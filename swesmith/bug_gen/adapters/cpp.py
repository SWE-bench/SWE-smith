import re
import tree_sitter_cpp as tscpp

from swesmith.constants import TODO_REWRITE, CodeEntity
from tree_sitter import Language, Parser, Query, QueryCursor

CPP_LANGUAGE = Language(tscpp.language())


class CPlusPlusEntity(CodeEntity):
    @property
    def name(self) -> str:
        func_query = Query(
            CPP_LANGUAGE,
            """
            [
                (function_definition (function_declarator declarator: (identifier) @name))
                (function_definition (function_declarator declarator: (destructor_name (identifier) @name)))
            ]
            """,
        )
        matches = QueryCursor(func_query).matches(self.node)
        if matches:
            name_node = matches[0][1]["name"][0]
            func_name = name_node.text.decode("utf-8")
            if name_node.parent.type == "destructor_name":
                return f"{func_name} Destructor"
            return func_name
        return ""

    @property
    def signature(self) -> str:
        body_query = Query(
            CPP_LANGUAGE, "(function_definition body: (compound_statement) @body)"
        )
        matches = QueryCursor(body_query).matches(self.node)
        if matches:
            body_node = matches[0][1]["body"][0]
            body_start_byte = body_node.start_byte - self.node.start_byte
            signature = self.node.text[:body_start_byte].strip().decode("utf-8")
            signature = re.sub(r"\(\s+", "(", signature).strip()
            signature = re.sub(r"\s+\)", ")", signature).strip()
            signature = re.sub(r"\s+", " ", signature).strip()
            return signature
        return ""

    @property
    def stub(self) -> str:
        return f"{self.signature} {{\n\t// {TODO_REWRITE}\n}}"


def get_entities_from_file_cpp(
    entities: list[CPlusPlusEntity],
    file_path: str,
    max_entities: int = -1,
) -> None:
    """
    Parse a .cpp file and return up to max_entities top-level funcs.
    If max_entities < 0, collects them all.
    """
    parser = Parser(CPP_LANGUAGE)

    file_content = open(file_path, "r", encoding="utf8").read()
    tree = parser.parse(bytes(file_content, "utf8"))
    root = tree.root_node
    lines = file_content.splitlines()

    def walk(node) -> None:
        # stop if we've hit the limit
        if 0 <= max_entities == len(entities):
            return

        # not checking for error nodes here because tree-sitter-cpp frequently
        # generates them parsing valid pre-processor directives

        if node.type == "function_definition":
            entities.append(_build_entity(node, lines, file_path))
            if 0 <= max_entities == len(entities):
                return

        for child in node.children:
            walk(child)

    walk(root)


def _build_entity(node, lines, file_path: str) -> CPlusPlusEntity:
    """
    Turns a Tree-sitter node into a CPlusPlusEntity object.
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

    return CPlusPlusEntity(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_start=start_row + 1,
        line_end=end_row + 1,
        node=node,
        src_code="\n".join(dedented),
    )
