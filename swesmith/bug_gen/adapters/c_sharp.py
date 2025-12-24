import re
import warnings

from swesmith.constants import CodeEntity, TODO_REWRITE
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_c_sharp as tscs
from swesmith.bug_gen.adapters.utils import build_entity

C_SHARP_LANGUAGE = Language(tscs.language())


class CSharpEntity(CodeEntity):
    @property
    def name(self) -> str:
        name_query = Query(
            C_SHARP_LANGUAGE,
            """
                (constructor_declaration name: (identifier) @name)
                (destructor_declaration name: (identifier) @name)
                (method_declaration name: (identifier) @name)
            """,
        )
        name = self._extract_text_from_first_match(name_query, self.node, "name")
        if self.node.type == "destructor_declaration":
            name = f"{name} Finalizer"
        return name or ""

    @property
    def signature(self) -> str:
        body_query = Query(
            C_SHARP_LANGUAGE,
            """
            [
              (constructor_declaration body: (block) @body)
              (destructor_declaration body: (block) @body)
              (method_declaration body: (block) @body)
            ]
            """.strip(),
        )
        matches = QueryCursor(body_query).matches(self.node)
        if matches:
            body_node = matches[0][1]["body"][0]
            signature = (
                self.node.text[: body_node.start_byte - self.node.start_byte]
                .rstrip()
                .decode("utf-8")
            )
            signature = re.sub(r"\(\s+", "(", signature).strip()
            signature = re.sub(r"\s+\)", ")", signature).strip()
            signature = re.sub(r"\s+", " ", signature).strip()
            return signature
        return ""

    @property
    def stub(self) -> str:
        return f"{self.signature}\n{{\n\t// {TODO_REWRITE}\n}}"

    @staticmethod
    def _extract_text_from_first_match(query, node, capture_name: str) -> str | None:
        """Extract text from tree-sitter query matches with None fallback."""
        matches = QueryCursor(query).matches(node)
        return matches[0][1][capture_name][0].text.decode("utf-8") if matches else None


def get_entities_from_file_c_sharp(
    entities: list[CSharpEntity],
    file_path: str,
    max_entities: int = -1,
) -> None:
    """
    Parse a .cs file and return up to max_entities methods.
    If max_entities < 0, collects them all.
    """
    parser = Parser(C_SHARP_LANGUAGE)

    try:
        file_content = open(file_path, "r", encoding="utf8").read()
    except UnicodeDecodeError:
        warnings.warn(f"Ignoring file {file_path} as it has an unsupported encoding")
        return

    tree = parser.parse(bytes(file_content, "utf8"))
    root = tree.root_node
    lines = file_content.splitlines()

    def walk(node) -> None:
        # stop if we've hit the limit
        if 0 <= max_entities == len(entities):
            return

        if node.type == "ERROR":
            warnings.warn(f"Error encountered parsing {file_path}")
            return

        if node.type in [
            "constructor_declaration",
            "destructor_declaration",
            "method_declaration",
        ]:
            if node.type == "method_declaration" and not _has_body(node):
                pass
            else:
                entities.append(build_entity(node, lines, file_path, CSharpEntity))
                if 0 <= max_entities == len(entities):
                    return

        for child in node.children:
            walk(child)

    walk(root)


def _has_body(node) -> bool:
    """
    Check if a method declaration has a body.
    """
    for child in node.children:
        if child.type == "block":
            return True
    return False
