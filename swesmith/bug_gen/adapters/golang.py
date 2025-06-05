import re

from swesmith.constants import TODO_REWRITE
from swesmith.utils import CodeEntity
from tree_sitter import Parser
from tree_sitter_languages import get_language

GO_LANGUAGE = get_language("go")


class GoEntity(CodeEntity):
    @property
    def name(self) -> str:
        if self.node.type == "function_declaration":
            for child in self.node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8")
        elif self.node.type == "method_declaration":
            func_name, receiver_type = None, None
            for child in self.node.children:
                if child.type == "field_identifier":
                    func_name = child.text.decode("utf-8")
                elif child.type == "parameter_list":
                    # Assume first parameter is the receiver
                    receiver = [
                        c for c in self.node.children if c.type == "parameter_list"
                    ]
                    receiver = [
                        c
                        for c in receiver[0].children
                        if c.type == "parameter_declaration"
                    ][0]
                    type_node = [c for c in receiver.named_children if "type" in c.type]
                    receiver_type = type_node[0].text.decode("utf-8").lstrip("*")
            return f"{receiver_type}.{func_name}" if receiver_type else func_name

    @property
    def signature(self) -> str:
        return self.src_code.split("{", 1)[0].strip()

    @property
    def stub(self) -> str:
        # Find the opening brace '{' and remove everything after it
        match = re.search(r"\{", self.src_code)
        if match:
            body_start = match.start()
            return (
                self.src_code[:body_start].rstrip() + " {\n\t// " + TODO_REWRITE + "\n}"
            )
        else:
            # If no body found, return the original code
            return self.src_code


def get_entities_from_file_go(
    entities: list[GoEntity],
    file_path: str,
    max_entities: int = -1,
) -> list[GoEntity]:
    """
    Parse a .go file and return up to max_entities top-level funcs and types.
    If max_entities < 0, collects them all.
    """
    parser = Parser()
    parser.set_language(GO_LANGUAGE)

    file_content = open(file_path, "r", encoding="utf8").read()
    tree = parser.parse(bytes(file_content, "utf8"))
    root = tree.root_node
    lines = file_content.splitlines()

    def walk(node):
        # stop if we've hit the limit
        if 0 <= max_entities == len(entities):
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
