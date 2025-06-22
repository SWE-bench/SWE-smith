import libcst

from swesmith.bug_gen.procedural import PythonProceduralModifier
from swesmith.constants import CodeProperty


class ClassRemoveBasesModifier(PythonProceduralModifier):
    explanation: str = "The base class has been removed from the class definition."
    name: str = "func_pm_class_rm_base"
    conditions: list = [CodeProperty.IS_CLASS, CodeProperty.HAS_PARENT]
    min_complexity: int = 10

    def leave_ClassDef(self, original_node, updated_node):
        bases = list(updated_node.bases)
        if len(bases) > 0 and self.flip():
            if len(bases) == 1:
                bases = []
            else:
                to_remove = self.rand.randint(0, len(bases) - 1)
                bases.pop(to_remove)

        return updated_node.with_changes(bases=tuple(bases))


class ClassShuffleMethodsModifier(PythonProceduralModifier):
    explanation: str = "The methods in a class have been shuffled."
    name: str = "func_pm_class_shuffle_funcs"
    conditions: list = [CodeProperty.IS_CLASS]
    min_complexity: int = 10

    def leave_ClassDef(self, original_node, updated_node):
        methods = [
            n for n in updated_node.body.body if isinstance(n, libcst.FunctionDef)
        ]
        non_methods = [
            n for n in updated_node.body.body if not isinstance(n, libcst.FunctionDef)
        ]
        self.rand.shuffle(methods)
        new_body = non_methods + methods
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=tuple(new_body))
        )


class ClassRemoveFuncsModifier(PythonProceduralModifier):
    explanation: str = (
        "Method(s) and their reference(s) have been removed from the class."
    )
    name: str = "func_pm_class_rm_funcs"
    conditions: list = [CodeProperty.IS_CLASS]
    min_complexity: int = 10

    def leave_ClassDef(
        self, original_node: libcst.ClassDef, updated_node: libcst.ClassDef
    ) -> libcst.ClassDef:
        # Access the statements inside the indented block
        body_statements = list(updated_node.body.body)

        # Track which function names we're removing
        removed_functions = set()

        # First pass: identify functions to remove
        new_body_statements = []
        for stmt in body_statements:
            if isinstance(stmt, libcst.FunctionDef) and self.flip():
                # Track this function name for removal
                removed_functions.add(stmt.name.value)
                # Skip this function (remove it)
                continue
            new_body_statements.append(stmt)

        # Only proceed if we actually removed something
        if not removed_functions:
            return updated_node

        # Create a reference remover to clean up references to removed functions
        reference_remover = FunctionReferenceRemover(removed_functions)

        # Second pass: process the remaining statements to remove references
        clean_statements = []
        for stmt in new_body_statements:
            # The correct way to apply a transformer to a node
            clean_stmt = stmt.visit(reference_remover)
            clean_statements.append(clean_stmt)

        # Create a new indented block with the cleaned statements
        new_body = updated_node.body.with_changes(body=tuple(clean_statements))

        # Return the updated class with the new body
        return updated_node.with_changes(body=new_body)


class FunctionReferenceRemover(libcst.CSTTransformer):
    """Helper transformer to remove references to deleted functions."""

    def __init__(self, removed_functions):
        super().__init__()
        self.removed_functions = removed_functions
        self.in_self_attr = False

    def visit_Attribute(self, node: libcst.Attribute) -> bool:
        # Check if this is a self.method_name pattern
        if (
            isinstance(node.value, libcst.Name)
            and node.value.value == "self"
            and node.attr.value in self.removed_functions
        ):
            self.in_self_attr = True
        return True

    def leave_Attribute(
        self, original_node: libcst.Attribute, updated_node: libcst.Attribute
    ) -> libcst.BaseExpression:
        if (
            isinstance(updated_node.value, libcst.Name)
            and updated_node.value.value == "self"
            and updated_node.attr.value in self.removed_functions
        ):
            # Reset state
            self.in_self_attr = False
        return updated_node

    def leave_Call(
        self, original_node: libcst.Call, updated_node: libcst.Call
    ) -> libcst.BaseExpression:
        # Check if we're calling a removed function through self
        if self.in_self_attr:
            # Reset state
            self.in_self_attr = False
            # Replace with a placeholder that won't cause errors
            return libcst.Name(value="None")
        return updated_node
