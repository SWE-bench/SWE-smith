"""
Utility functions for language adapters.
"""

import re
from typing import TypeVar, Type
from swesmith.constants import CodeEntity

T = TypeVar("T", bound=CodeEntity)


def build_entity(
    node,
    lines: list[str],
    file_path: str,
    entity_class: Type[T],
    default_indent_size: int = 4,
) -> T:
    """
    Turns a Tree-sitter node into a CodeEntity object.
    """
    # start_point/end_point are (row, col) zero-based
    start_row, _ = node.start_point
    end_row, _ = node.end_point

    # slice out the raw lines
    snippet = lines[start_row : end_row + 1]

    # detect indent on first line
    first = snippet[0] if snippet else ""
    m = re.match(r"^(?P<indent>[\t ]*)", first)
    indent_str = m.group("indent") if m else ""
    # tabs count as size=1, else use count of spaces, fallback to default_indent_size
    indent_size = 1 if "\t" in indent_str else (len(indent_str) or default_indent_size)
    indent_level = len(indent_str) // indent_size

    # dedent each line
    dedented = []
    for line in snippet:
        if len(line) >= indent_level * indent_size:
            dedented.append(line[indent_level * indent_size :])
        else:
            dedented.append(line.lstrip("\t "))

    return entity_class(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_start=start_row + 1,
        line_end=end_row + 1,
        node=node,
        src_code="\n".join(dedented),
    )
