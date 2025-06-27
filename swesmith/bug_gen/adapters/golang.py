import re

from swesmith.constants import TODO_REWRITE, CodeEntity
from tree_sitter import Language, Parser, Query
import tree_sitter_go as tsgo
import warnings

GO_LANGUAGE = Language(tsgo.language())


class GoEntity(CodeEntity):
    @property
    def name(self) -> str:
        func_query = Query(
            GO_LANGUAGE, "(function_declaration name: (identifier) @name)"
        )
        func_name = self._extract_text_from_first_match(func_query, self.node, "name")
        if func_name:
            return func_name

        name_query = Query(
            GO_LANGUAGE, "(method_declaration name: (field_identifier) @name)"
        )
        receiver_query = Query(
            GO_LANGUAGE,
            """
            (method_declaration
              receiver: (parameter_list
                (parameter_declaration
                  type: [
                    (type_identifier) @receiver_type
                    (pointer_type (type_identifier) @receiver_type)
                  ])))
            """.strip(),
        )

        func_name = self._extract_text_from_first_match(name_query, self.node, "name")
        receiver_type = self._extract_text_from_first_match(
            receiver_query, self.node, "receiver_type"
        )

        return (
            f"{receiver_type}.{func_name}" if receiver_type and func_name else func_name
        )

    @property
    def signature(self) -> str:
        body_query = Query(
            GO_LANGUAGE,
            """
            [
              (function_declaration body: (block) @body)
              (method_declaration body: (block) @body)
            ]
            """.strip(),
        )
        matches = body_query.matches(self.node)
        if matches:
            body_node = matches[0][1]["body"][0]
            body_start_byte = body_node.start_byte - self.node.start_byte
            return self.src_code[:body_start_byte].strip()
        return ""

    @property
    def stub(self) -> str:
        return f"{self.signature} {{\n\t// {TODO_REWRITE}\n}}"

    @property
    def complexity(self) -> int:
        def walk(node):
            score = 0
            if node.type in [
                "!=",
                "&&",
                "<",
                "<-",
                "<=",
                "==",
                ">",
                ">=",
                "||",
                "case",
                "default",
                "defer",
                "else",
                "for",
                "go",
                "if",
            ]:
                score += 1

            for child in node.children:
                score += walk(child)

            return score

        return 1 + walk(self.node)

    @staticmethod
    def _extract_text_from_first_match(query, node, capture_name: str) -> str | None:
        """Extract text from tree-sitter query matches with None fallback."""
        matches = query.matches(node)
        return matches[0][1][capture_name][0].text.decode("utf-8") if matches else None


def get_entities_from_file_go(
    entities: list[GoEntity],
    file_path: str,
    max_entities: int = -1,
) -> list[GoEntity]:
    """
    Parse a .go file and return up to max_entities top-level funcs and types.
    If max_entities < 0, collects them all.
    """
    parser = Parser(GO_LANGUAGE)

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

        if node.type in [
            "function_declaration",
            "method_declaration",
        ]:
            entities.append(_build_entity(node, lines, file_path))
            if 0 <= max_entities == len(entities):
                return

        for child in node.children:
            walk(child)

    walk(root)


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

    return GoEntity(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_start=start_row + 1,
        line_end=end_row + 1,
        node=node,
        src_code="\n".join(dedented),
    )
