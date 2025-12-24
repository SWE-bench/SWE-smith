import re
import tree_sitter_rust as tsrs
import warnings

from swesmith.constants import TODO_REWRITE, CodeEntity, CodeProperty
from tree_sitter import Language, Parser, Query, QueryCursor
from swesmith.bug_gen.adapters.utils import build_entity

RUST_LANGUAGE = Language(tsrs.language())


class RustEntity(CodeEntity):
    def _analyze_properties(self):
        """Analyze Rust code properties."""
        node = self.node

        if node.type == "function_item":
            self._tags.add(CodeProperty.IS_FUNCTION)

        self._walk_for_properties(node)

    def _walk_for_properties(self, n):
        """Walk the AST and analyze properties."""
        self._check_control_flow(n)
        self._check_operations(n)
        self._check_expressions(n)

        for child in n.children:
            self._walk_for_properties(child)

    def _check_control_flow(self, n):
        """Check for control flow patterns."""
        if n.type in ["for_expression", "while_expression", "loop_expression"]:
            self._tags.add(CodeProperty.HAS_LOOP)
        if n.type == "if_expression":
            self._tags.add(CodeProperty.HAS_IF)
            for child in n.children:
                if child.type == "else_clause":
                    self._tags.add(CodeProperty.HAS_IF_ELSE)
                    break
        if n.type == "match_expression":
            self._tags.add(CodeProperty.HAS_SWITCH)

    def _check_operations(self, n):
        """Check for various operations."""
        if n.type == "index_expression":
            self._tags.add(CodeProperty.HAS_LIST_INDEXING)
        if n.type == "call_expression":
            self._tags.add(CodeProperty.HAS_FUNCTION_CALL)
        if n.type == "return_expression":
            self._tags.add(CodeProperty.HAS_RETURN)
        if n.type in ["let_declaration", "const_item", "static_item"]:
            self._tags.add(CodeProperty.HAS_ASSIGNMENT)

    def _check_expressions(self, n):
        """Check for expression patterns."""
        if n.type == "binary_expression":
            self._tags.add(CodeProperty.HAS_BINARY_OP)
        if n.type == "unary_expression":
            self._tags.add(CodeProperty.HAS_UNARY_OP)
        if n.type == "closure_expression":
            self._tags.add(CodeProperty.HAS_LAMBDA)

    @property
    def complexity(self) -> int:
        """Calculate cyclomatic complexity for Rust code."""

        def walk(node):
            score = 0
            if node.type in [
                "!=",
                "&&",
                "<",
                "<=",
                "==",
                ">",
                ">=",
                "||",
                "match_arm",
                "else_clause",
                "for_expression",
                "while_expression",
                "loop_expression",
                "if_expression",
            ]:
                score += 1

            for child in node.children:
                score += walk(child)

            return score

        return 1 + walk(self.node)

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
        matches = QueryCursor(body_query).matches(self.node)
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
        matches = QueryCursor(query).matches(node)
        return matches[0][1][capture_name][0].text.decode("utf-8") if matches else None


def get_entities_from_file_rs(
    entities: list[RustEntity],
    file_path: str,
    max_entities: int = -1,
) -> None:
    """
    Parse a .rs file and return up to max_entities top-level funcs and types.
    If max_entities < 0, collects them all.
    """
    parser = Parser(RUST_LANGUAGE)

    file_content = open(file_path, "r", encoding="utf8").read()
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

        if node.type == "function_item":
            if _has_test_attribute(node):
                return

            entities.append(build_entity(node, lines, file_path, RustEntity))
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
