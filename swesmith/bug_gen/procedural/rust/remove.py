import tree_sitter_rust as tsrs

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.rust.base import RustProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Language, Parser

RUST_LANGUAGE = Language(tsrs.language())


class RemoveLoopModifier(RustProceduralModifier):
    explanation: str = CommonPMs.REMOVE_LOOP.explanation
    name: str = CommonPMs.REMOVE_LOOP.name
    conditions: list = CommonPMs.REMOVE_LOOP.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove loop statements from the Rust code."""
        if not self.flip():
            return None

        parser = Parser(RUST_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._remove_loops(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_loops(self, source_code: str, node) -> str:
        """Recursively find and remove loop statements."""
        removals = []

        def collect_loops(n):
            if n.type in ["for_expression", "while_expression", "loop_expression"]:
                if self.flip():
                    removals.append(n)
            for child in n.children:
                collect_loops(child)

        collect_loops(node)

        if not removals:
            return source_code

        modified_source = source_code
        for loop_node in reversed(removals):
            start_byte = loop_node.start_byte
            end_byte = loop_node.end_byte

            modified_source = modified_source[:start_byte] + modified_source[end_byte:]

        return modified_source


class RemoveConditionalModifier(RustProceduralModifier):
    explanation: str = CommonPMs.REMOVE_CONDITIONAL.explanation
    name: str = CommonPMs.REMOVE_CONDITIONAL.name
    conditions: list = CommonPMs.REMOVE_CONDITIONAL.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove conditional statements from the Rust code."""
        if not self.flip():
            return None

        parser = Parser(RUST_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._remove_conditionals(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_conditionals(self, source_code: str, node) -> str:
        """Recursively find and remove conditional statements."""
        removals = []

        def collect_conditionals(n):
            if n.type == "if_expression":
                if self.flip():
                    removals.append(n)
            for child in n.children:
                collect_conditionals(child)

        collect_conditionals(node)

        if not removals:
            return source_code

        modified_source = source_code
        for if_node in reversed(removals):
            start_byte = if_node.start_byte
            end_byte = if_node.end_byte

            modified_source = modified_source[:start_byte] + modified_source[end_byte:]

        return modified_source


class RemoveAssignModifier(RustProceduralModifier):
    explanation: str = CommonPMs.REMOVE_ASSIGNMENT.explanation
    name: str = CommonPMs.REMOVE_ASSIGNMENT.name
    conditions: list = CommonPMs.REMOVE_ASSIGNMENT.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove assignment statements from the Rust code."""
        if not self.flip():
            return None

        parser = Parser(RUST_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._remove_assignments(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_assignments(self, source_code: str, node) -> str:
        """Recursively find and remove assignment statements."""
        removals = []

        def collect_assignments(n):
            if n.type in ["let_declaration", "assignment_expression"]:
                if self.flip():
                    removals.append(n)
            for child in n.children:
                collect_assignments(child)

        collect_assignments(node)

        if not removals:
            return source_code

        modified_source = source_code
        for assign_node in reversed(removals):
            start_byte = assign_node.start_byte
            end_byte = assign_node.end_byte

            modified_source = modified_source[:start_byte] + modified_source[end_byte:]

        return modified_source
