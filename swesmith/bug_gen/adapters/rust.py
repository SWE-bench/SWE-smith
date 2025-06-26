import re
import tree_sitter_rust as tsrs
import warnings

from swesmith.constants import TODO_REWRITE, CodeEntity
from tree_sitter import Language, Parser, Query

RUST_LANGUAGE = Language(tsrs.language())


class RustEntity(CodeEntity):
    @property
    def name(self) -> str:
        func_query = Query(RUST_LANGUAGE, "(function_item name: (identifier) @name)")
        func_name = self._extract_text_from_first_match(func_query, self.node, "name")
        if func_name:
            return func_name
        return ""

    @property
    def signature(self) -> str:
        body_query = Query(RUST_LANGUAGE, "(function_item body: (block) @body)")
        matches = body_query.matches(self.node)
        if matches:
            body_node = matches[0][1]["body"][0]
            body_start_byte = body_node.start_byte - self.node.start_byte
            signature = self.node.text[:body_start_byte].strip().decode("utf-8")
            signature = re.sub(r"\(\s+", "(", signature).strip()
            signature = re.sub(r",\s+\)", ")", signature).strip()
            signature = re.sub(r"\s+", " ", signature).strip()
            return signature
        return ""

    @property
    def stub(self) -> str:
        return f"{self.signature} {{\n    // {TODO_REWRITE}\n}}"

    @staticmethod
    def _extract_text_from_first_match(query, node, capture_name: str) -> str | None:
        """Extract text from tree-sitter query matches with None fallback."""
        matches = query.matches(node)
        return matches[0][1][capture_name][0].text.decode("utf-8") if matches else None


def get_entities_from_file_rs(
    entities: list[RustEntity],
    file_path: str,
    max_entities: int = -1,
) -> list[RustEntity]:
    """
    Parse a .rs file and return up to max_entities top-level funcs and types.
    If max_entities < 0, collects them all.
    """
    parser = Parser(RUST_LANGUAGE)

    file_content = open(file_path, "r", encoding="utf8").read()
    tree = parser.parse(bytes(file_content, "utf8"))
    root = tree.root_node
    lines = file_content.splitlines()

    def walk(node):
        # stop if we've hit the limit
        if 0 <= max_entities == len(entities):
            return

        if node.type == "ERROR":
            warnings.warn(f"Error encountered parsing {file_path}")
            return

        if node.type == "function_item":
            if _has_test_attribute(node):
                return

            entities.append(_build_entity(node, lines, file_path))
            if 0 <= max_entities == len(entities):
                return

        for child in node.children:
            walk(child)

    walk(root)


def _has_test_attribute(node) -> bool:
    possible_att = node.prev_named_sibling
    while possible_att and possible_att.type == "attribute_item":
        if possible_att.text == b"#[test]":
            return True
        possible_att = possible_att.prev_named_sibling
    return False


def _build_entity(node, lines, file_path: str) -> CodeEntity:
    """
    Turn a Tree-sitter node into CodeEntity.
    """
    # start_point/end_point are (row, col) zero-based
    start_row, _ = node.start_point
    end_row, _ = node.end_point

    # slice out the raw lines
    snippet = lines[start_row : end_row + 1]

    # detect indent on first line
    first = snippet[0]
    m = re.match(r"^(?P<indent>[\t ]*)", first)
    indent_str = m.group("indent")
    # tabs count as size=1, else use count of spaces, fallback to 4
    indent_size = 1 if "\t" in indent_str else (len(indent_str) or 4)
    indent_level = len(indent_str) // indent_size

    # dedent each line
    dedented = []
    for line in snippet:
        if len(line) >= indent_level * indent_size:
            dedented.append(line[indent_level * indent_size :])
        else:
            dedented.append(line.lstrip("\t "))

    return RustEntity(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_start=start_row + 1,
        line_end=end_row + 1,
        node=node,
        src_code="\n".join(dedented),
    )
