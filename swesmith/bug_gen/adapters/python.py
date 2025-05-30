import ast

from swesmith.utils import CodeEntity


def py_get_entities_from_file(
    entities: list[CodeEntity],
    file_content: str,
    file_path: str,
    max_entities: int = -1,
):
    try:
        tree = ast.parse(file_content, filename=file_path)
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if not any([isinstance(node, x) for x in (ast.ClassDef, ast.FunctionDef)]):
            continue
        entities.append(py_get_entity_from_node(node, file_content, file_path))
        if max_entities != -1 and len(entities) >= max_entities:
            return


def py_get_entity_from_node(
    node: ast.AST, file_content: str, file_path: str
) -> CodeEntity:
    """Turns an AST node into a CodeEntity object."""
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

    source_code = ast.get_source_segment(file_content, node)

    # Get the line content for the source definition
    source_line = file_content.splitlines()[start_line - 1]
    leading_whitespace = len(source_line) - len(source_line.lstrip())

    # Determine the number of spaces per tab
    indent_size = 4  # Default fallback
    if "\t" in file_content:
        indent_size = source_line.expandtabs().index(source_line.lstrip())

    # Calculate indentation level
    indentation_level = (
        leading_whitespace // indent_size if leading_whitespace > 0 else 0
    )

    # Remove indentation from source source code
    assert source_code is not None
    lines = source_code.splitlines()
    dedented_source_code = [lines[0]]
    for line in lines[1:]:
        # Strip leading spaces equal to indentation_level * indent_size
        dedented_source_code.append(line[indentation_level * indent_size :])
    source_code = "\n".join(dedented_source_code)

    return CodeEntity(
        file_path=file_path,
        indent_level=indentation_level,
        indent_size=indent_size,
        line_end=end_line,
        line_start=start_line,
        src_code=source_code,
        src_node=node,
    )
