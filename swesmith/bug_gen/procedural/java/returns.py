"""
Return-related procedural modifications for Java code.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

JAVA_LANGUAGE = Language(tsjava.language())
PRIMITIVE_RETURN_TYPES = {
    "integral_type",
    "floating_point_type",
    "boolean_type",
    "void_type",
}


class ReturnNullModifier(JavaProceduralModifier):
    """Change return statements to return null."""

    explanation: str = "Changed return value to null"
    name: str = "func_pm_return_null"
    conditions: list = []

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_return_to_null(
            code_entity.src_code, tree.root_node
        )

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_return_to_null(self, code: str, node) -> str:
        """Change return statements to return null."""
        candidates = []
        self._find_returns(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)
        return_expr = None
        for child in target.children:
            if child.type not in {"return", ";"}:
                return_expr = child
                break

        if return_expr is None:
            return code

        return_expr_text = code[return_expr.start_byte : return_expr.end_byte]
        if return_expr_text.strip() == "null":
            # Already returning null, skip
            return code

        # Replace with null
        return code[: return_expr.start_byte] + "null" + code[return_expr.end_byte :]

    def _find_returns(self, node, candidates):
        """Find return statements with non-null values."""
        if node.type == "return_statement":
            # Check if it's not void return
            has_expression = any(
                child.type not in ["return", ";"] for child in node.children
            )
            if has_expression and self._method_can_return_null(node):
                candidates.append(node)
        for child in node.children:
            self._find_returns(child, candidates)

    def _method_can_return_null(self, node) -> bool:
        """Return True only for methods with reference return types."""
        current = node
        while current and current.type != "method_declaration":
            current = current.parent
        if not current:
            return False

        return_type_node = None
        for child in current.children:
            if child.type in {"modifiers", "type_parameters"}:
                continue
            if child.type == "identifier":
                break
            return_type_node = child
            break

        if return_type_node is None:
            return False

        return return_type_node.type not in PRIMITIVE_RETURN_TYPES
