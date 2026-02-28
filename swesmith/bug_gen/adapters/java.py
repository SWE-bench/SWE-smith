import re
import warnings

from swesmith.constants import CodeEntity, CodeProperty, TODO_REWRITE
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava
from swesmith.bug_gen.adapters.utils import build_entity

JAVA_LANGUAGE = Language(tsjava.language())


class JavaEntity(CodeEntity):
    def _analyze_properties(self):
        """Analyze Java code properties for procedural modifiers."""
        node = self.node
        if node.type in ["method_declaration", "constructor_declaration"]:
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
        if n.type in [
            "for_statement",
            "enhanced_for_statement",
            "while_statement",
            "do_statement",
        ]:
            self._tags.add(CodeProperty.HAS_LOOP)
        if n.type == "if_statement":
            self._tags.add(CodeProperty.HAS_IF)
            for child in n.children:
                if child.type == "else":
                    self._tags.add(CodeProperty.HAS_IF_ELSE)
                    break
        if n.type == "switch_expression":
            self._tags.add(CodeProperty.HAS_SWITCH)
        if n.type in ["try_statement", "try_with_resources_statement"]:
            self._tags.add(CodeProperty.HAS_EXCEPTION)
            self._tags.add(CodeProperty.HAS_WRAPPER)

    def _check_operations(self, n):
        """Check for various operations."""
        if n.type == "array_access":
            self._tags.add(CodeProperty.HAS_LIST_INDEXING)
        if n.type == "method_invocation":
            self._tags.add(CodeProperty.HAS_FUNCTION_CALL)
        if n.type == "return_statement":
            self._tags.add(CodeProperty.HAS_RETURN)
        if n.type == "import_declaration":
            self._tags.add(CodeProperty.HAS_IMPORT)
        if n.type in ["assignment_expression", "local_variable_declaration"]:
            self._tags.add(CodeProperty.HAS_ASSIGNMENT)
        if n.type == "lambda_expression":
            self._tags.add(CodeProperty.HAS_LAMBDA)

    def _check_expressions(self, n):
        """Check expression patterns."""
        if n.type == "binary_expression":
            self._tags.add(CodeProperty.HAS_BINARY_OP)
            for child in n.children:
                if hasattr(child, "text"):
                    text = child.text.decode("utf-8")
                    if text in ["&&", "||"]:
                        self._tags.add(CodeProperty.HAS_BOOL_OP)
                    elif text in ["<", ">", "<=", ">="]:
                        self._tags.add(CodeProperty.HAS_OFF_BY_ONE)
        if n.type == "unary_expression":
            self._tags.add(CodeProperty.HAS_UNARY_OP)

    @property
    def complexity(self) -> int:
        """Calculate cyclomatic complexity for Java methods."""

        def walk(node):
            score = 0
            if node.type in [
                "if_statement",
                "for_statement",
                "enhanced_for_statement",
                "while_statement",
                "do_statement",
                "case",
                "catch_clause",
                "&&",
                "||",
                "?",
            ]:
                score += 1
            for child in node.children:
                score += walk(child)
            return score

        return 1 + walk(self.node)

    @property
    def name(self) -> str:
        method_query = Query(
            JAVA_LANGUAGE,
            """
                (constructor_declaration name: (identifier) @name)
                (method_declaration name: (identifier) @name)
            """,
        )
        method_name = self._extract_text_from_first_match(
            method_query, self.node, "name"
        )
        if method_name:
            return method_name
        return ""

    @property
    def signature(self) -> str:
        body_query = Query(
            JAVA_LANGUAGE,
            """
            [
              (constructor_declaration body: (constructor_body) @body)
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
        return f"{self.signature} {{\n\t// {TODO_REWRITE}\n}}"

    @staticmethod
    def _extract_text_from_first_match(query, node, capture_name: str) -> str | None:
        """Extract text from tree-sitter query matches with None fallback."""
        matches = QueryCursor(query).matches(node)
        return matches[0][1][capture_name][0].text.decode("utf-8") if matches else None


def get_entities_from_file_java(
    entities: list[JavaEntity],
    file_path: str,
    max_entities: int = -1,
) -> None:
    """
    Parse a .java file and return up to max_entities top-level funcs and types.
    If max_entities < 0, collects them all.
    """
    parser = Parser(JAVA_LANGUAGE)

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

        if node.type in [
            "constructor_declaration",
            "method_declaration",
        ]:
            if node.type == "method_declaration" and not _has_body(node):
                pass
            else:
                entities.append(build_entity(node, lines, file_path, JavaEntity))
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
