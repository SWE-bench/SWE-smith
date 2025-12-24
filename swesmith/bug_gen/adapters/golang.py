from swesmith.constants import TODO_REWRITE, CodeEntity, CodeProperty
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_go as tsgo
import warnings
from swesmith.bug_gen.adapters.utils import build_entity

GO_LANGUAGE = Language(tsgo.language())


class GoEntity(CodeEntity):
    def _analyze_properties(self):
        """Analyze Go code properties."""
        node = self.node

        # Core entity types
        if node.type in ["function_declaration", "method_declaration"]:
            self._tags.add(CodeProperty.IS_FUNCTION)

        # Control flow and operations analysis
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
        if n.type == "for_statement":
            self._tags.add(CodeProperty.HAS_LOOP)
        if n.type == "if_statement":
            self._tags.add(CodeProperty.HAS_IF)
            # Check if this if statement has an else clause
            for child in n.children:
                if child.type == "else":
                    self._tags.add(CodeProperty.HAS_IF_ELSE)
                    break
        # Handle switch statements as control flow
        if n.type in ["expression_switch_statement", "type_switch_statement"]:
            self._tags.add(CodeProperty.HAS_SWITCH)

    def _check_operations(self, n):
        """Check for various operations."""
        if n.type == "index_expression":
            self._tags.add(CodeProperty.HAS_LIST_INDEXING)
        if n.type == "call_expression":
            self._tags.add(CodeProperty.HAS_FUNCTION_CALL)
        if n.type == "return_statement":
            self._tags.add(CodeProperty.HAS_RETURN)
        if n.type == "import_declaration":
            self._tags.add(CodeProperty.HAS_IMPORT)
        if n.type in [
            "assignment_expression",
            "assignment_statement",
            "short_var_declaration",
            "var_declaration",
        ]:
            self._tags.add(CodeProperty.HAS_ASSIGNMENT)
        if n.type == "func_literal":  # Anonymous functions in Go
            self._tags.add(CodeProperty.HAS_LAMBDA)

    def _check_expressions(self, n):
        """Check expression patterns."""
        if n.type == "binary_expression":
            self._tags.add(CodeProperty.HAS_BINARY_OP)
            # Check for boolean operators
            for child in n.children:
                if hasattr(child, "text"):
                    text = child.text.decode("utf-8")
                    if text in ["&&", "||"]:
                        self._tags.add(CodeProperty.HAS_BOOL_OP)
                    # Check for comparison operators (off by one potential)
                    elif text in ["<", ">", "<=", ">="]:
                        self._tags.add(CodeProperty.HAS_OFF_BY_ONE)
        if n.type == "unary_expression":
            self._tags.add(CodeProperty.HAS_UNARY_OP)

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

        if receiver_type and func_name:
            return f"{receiver_type}.{func_name}"
        elif func_name:
            return func_name
        else:
            return ""

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
        matches = QueryCursor(body_query).matches(self.node)
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
        matches = QueryCursor(query).matches(node)
        return matches[0][1][capture_name][0].text.decode("utf-8") if matches else None


def get_entities_from_file_go(
    entities: list[GoEntity],
    file_path: str,
    max_entities: int = -1,
) -> None:
    """
    Parse a .go file and return up to max_entities top-level funcs and types.
    If max_entities < 0, collects them all.
    """
    parser = Parser(GO_LANGUAGE)

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
            "function_declaration",
            "method_declaration",
        ]:
            entities.append(build_entity(node, lines, file_path, GoEntity))
            if 0 <= max_entities == len(entities):
                return

        for child in node.children:
            walk(child)

    walk(root)
