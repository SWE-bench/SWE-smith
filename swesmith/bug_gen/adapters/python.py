import ast
import astor

from dataclasses import dataclass
from swesmith.constants import TODO_REWRITE, CodeEntity, CodeProperty


@dataclass
class PythonEntity(CodeEntity):
    def _analyze_properties(self):
        node = self.node

        # Core entity types
        if isinstance(node, ast.FunctionDef):
            self._tags.add(CodeProperty.IS_FUNCTION)
        elif isinstance(node, ast.ClassDef):
            self._tags.add(CodeProperty.IS_CLASS)

        # Control flow
        if any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_LOOP)
        if any(isinstance(n, ast.If) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_IF)
            if any(n.orelse for n in ast.walk(node) if isinstance(n, ast.If)):
                self._tags.add(CodeProperty.HAS_IF_ELSE)
        if any(isinstance(n, ast.Try) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_EXCEPTION)

        # Operations
        if any(isinstance(n, ast.Subscript) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_LIST_INDEXING)
        if any(isinstance(n, ast.Call) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_FUNCTION_CALL)
        if any(isinstance(n, ast.Return) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_RETURN)
        if any(isinstance(n, ast.ListComp) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_LIST_COMPREHENSION)
        if any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_IMPORT)
        if any(isinstance(n, ast.Assign) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_ASSIGNMENT)
        if any(isinstance(n, ast.Lambda) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_LAMBDA)
        if any(isinstance(n, (ast.BinOp, ast.UnaryOp)) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_ARITHMETIC)
        if any(
            isinstance(n, ast.FunctionDef) and n.decorator_list for n in ast.walk(node)
        ):
            self._tags.add(CodeProperty.HAS_DECORATOR)
        if any(isinstance(n, (ast.Try, ast.With)) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_WRAPPER)
        if any(isinstance(n, ast.ClassDef) and n.bases for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_PARENT)

        # Operations by type
        if any(isinstance(n, ast.BinOp) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_BINARY_OP)
        if any(isinstance(n, ast.BoolOp) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_BOOL_OP)
        if any(isinstance(n, ast.UnaryOp) for n in ast.walk(node)):
            self._tags.add(CodeProperty.HAS_UNARY_OP)

        # Special cases
        if any(
            isinstance(n, ast.Compare)
            and len(n.ops) == 1
            and n.ops[0].__class__.__name__ in ["Lt", "Gt", "LtE", "GtE"]
            for n in ast.walk(node)
        ):
            self._tags.add(CodeProperty.HAS_OFF_BY_ONE)

    @property
    def complexity(self) -> int:
        """
        Simple way of calculating the complexity of a function.
        Complexity starts at 1 and increases for each decision point:
        - if/elif/else statements
        - for/while loops
        - and/or operators
        - except clauses
        - boolean operators
        """
        complexity = 1  # Base complexity

        for n in ast.walk(self.node):
            # Decision points
            if isinstance(n, (ast.If, ast.While, ast.For)):
                complexity += 1
            # Boolean operators
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values) - 1
            # Exception handling
            elif isinstance(n, ast.Try):
                complexity += len(n.handlers)
            # Comparison operators
            elif isinstance(n, ast.Compare):
                complexity += len(n.ops)

        return complexity

    @property
    def name(self):
        return self.node.name

    @property
    def signature(self):
        if isinstance(self.node, ast.ClassDef):
            return f"class {self.node.name}:"
        elif isinstance(self.node, ast.FunctionDef):
            args = [ast.unparse(arg) for arg in self.node.args.args]
            args_str = ", ".join(args)
            return f"def {self.node.name}({args_str})"

    @property
    def stub(self):
        src_code = self.src_code
        tree = ast.parse(src_code)

        class FunctionBodyStripper(ast.NodeTransformer):
            def visit_FunctionDef(self, node):
                # Keep the original arguments and decorator list
                new_node = ast.FunctionDef(
                    name=node.name,
                    args=node.args,
                    body=[],  # Empty body initially
                    decorator_list=node.decorator_list,
                    returns=node.returns,
                    type_params=getattr(node, "type_params", None),  # For Python 3.12+
                )

                # Add docstring if it exists
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                ):
                    new_node.body.append(node.body[0])

                # Add a comment indicating to implement this function
                new_node.body.append(ast.Expr(ast.Constant(TODO_REWRITE)))

                # Add a 'pass' statement after the docstring
                new_node.body.append(ast.Pass())

                return new_node

        stripped_tree = FunctionBodyStripper().visit(tree)
        ast.fix_missing_locations(stripped_tree)
        return astor.to_source(stripped_tree).strip()


def get_entities_from_file_py(
    entities: list[PythonEntity],
    file_path: str,
    max_entities: int = -1,
):
    try:
        file_content = open(file_path, "r", encoding="utf8").read()
        tree = ast.parse(file_content, filename=file_path)
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if not any([isinstance(node, x) for x in (ast.ClassDef, ast.FunctionDef)]):
            continue
        entities.append(_build_entity(node, file_content, file_path))
        if max_entities != -1 and len(entities) >= max_entities:
            return


def _build_entity(node: ast.AST, file_content: str, file_path: str) -> PythonEntity:
    """Turns an AST node into a PythonEntity object."""
    start_line = node.lineno  # type: ignore[attr-defined]
    end_line = (
        node.end_lineno if hasattr(node, "end_lineno") else None  # type: ignore[attr-defined]
    )

    if end_line is None:
        # Calculate end line manually if not available (older Python versions)
        end_line = (
            start_line
            + len(
                ast.get_source_segment(file_content, node).splitlines()  # type: ignore[attr-defined]
            )
            - 1
        )

    src_code = ast.get_source_segment(file_content, node)

    # Get the line content for the source definition
    source_line = file_content.splitlines()[start_line - 1]
    leading_whitespace = len(source_line) - len(source_line.lstrip())

    # Determine the number of spaces per tab
    indent_size = 4  # Default fallback
    if "\t" in file_content:
        indent_size = source_line.expandtabs().index(source_line.lstrip())

    # Calculate indentation level
    indent_level = leading_whitespace // indent_size if leading_whitespace > 0 else 0

    # Remove indentation from source source code
    assert src_code is not None
    lines = src_code.splitlines()
    dedented_src_code = [lines[0]]
    for line in lines[1:]:
        # Strip leading spaces equal to indent_level * indent_size
        dedented_src_code.append(line[indent_level * indent_size :])
    src_code = "\n".join(dedented_src_code)

    return PythonEntity(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_end=end_line,
        line_start=start_line,
        node=node,
        src_code=src_code,
    )
