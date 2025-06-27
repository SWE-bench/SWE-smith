import re

from swesmith.constants import TODO_REWRITE, CodeEntity
from tree_sitter import Language, Parser
import tree_sitter_php as tsphp

PHP_LANGUAGE = Language(tsphp.language_php())


class PhpEntity(CodeEntity):
    @property
    def name(self) -> str:
        if self.node.type == "function_definition":
            for child in self.node.children:
                if child.type == "name":
                    return child.text.decode("utf-8")
        elif self.node.type == "method_declaration":
            for child in self.node.children:
                if child.type == "name":
                    func_name = child.text.decode("utf-8")
                    # Find the class this method belongs to
                    class_node = self._find_parent_class()
                    if class_node:
                        class_name = self._get_class_name(class_node)
                        return f"{class_name}::{func_name}" if class_name else func_name
                    return func_name
        elif self.node.type == "class_declaration":
            for child in self.node.children:
                if child.type == "name":
                    return child.text.decode("utf-8")
        return "unknown"

    def _find_parent_class(self):
        """Find the parent class node for a method."""
        current = self.node.parent
        while current:
            if current.type == "class_declaration":
                return current
            current = current.parent
        return None

    def _get_class_name(self, class_node):
        """Extract class name from a class node."""
        for child in class_node.children:
            if child.type == "name":
                return child.text.decode("utf-8")
        return None

    @property
    def signature(self) -> str:
        # Find the opening brace '{' and remove everything after it
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


def get_entities_from_file_php(
    entities: list[PhpEntity],
    file_path: str,
    max_entities: int = -1,
) -> list[PhpEntity]:
    """
    Parse a .php file and return up to max_entities top-level functions, methods, and classes.
    If max_entities < 0, collects them all.
    """
    parser = Parser(PHP_LANGUAGE)

    try:
        file_content = open(file_path, "r", encoding="utf8").read()
        tree = parser.parse(bytes(file_content, "utf8"))
        root = tree.root_node
        lines = file_content.splitlines()

        def walk(node):
            # stop if we've hit the limit
            if 0 <= max_entities == len(entities):
                return

            if node.type in [
                "function_definition",
                "method_declaration",
                "class_declaration",
            ]:
                entities.append(_build_entity(node, lines, file_path))
                if 0 <= max_entities == len(entities):
                    return

            for child in node.children:
                walk(child)

        walk(root)
        return entities
    except Exception:
        return entities


def _build_entity(node, lines, file_path: str) -> PhpEntity:
    """
    Turn a Tree-sitter node into PhpEntity.
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

    return PhpEntity(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_start=start_row + 1,
        line_end=end_row + 1,
        node=node,
        src_code="\n".join(dedented),
    )
