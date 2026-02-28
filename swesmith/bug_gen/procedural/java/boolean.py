"""
Boolean-related procedural modifications for Java code.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

JAVA_LANGUAGE = Language(tsjava.language())


class BooleanNegateModifier(JavaProceduralModifier):
    """Negate boolean expressions and literals."""

    explanation: str = "Negated a boolean expression"
    name: str = "func_pm_bool_negate"
    conditions: list = []

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._negate_booleans(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _negate_booleans(self, code: str, node) -> str:
        """Negate boolean literals and expressions."""
        candidates = []
        self._find_booleans(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)
        original_text = code[target.start_byte : target.end_byte]

        # Negate the boolean
        if original_text == "true":
            replacement = "false"
        elif original_text == "false":
            replacement = "true"
        elif target.type == "unary_expression" and original_text.startswith("!"):
            # Remove negation: !x -> x
            # Find the operand
            for child in target.children:
                if child.type != "!":
                    replacement = code[child.start_byte : child.end_byte]
                    break
            else:
                return code
        else:
            # Add negation: x -> !x (wrap in parens if needed)
            if target.type in ["identifier", "field_access", "method_invocation"]:
                replacement = f"!{original_text}"
            else:
                replacement = f"!({original_text})"

        return code[: target.start_byte] + replacement + code[target.end_byte :]

    def _find_booleans(self, node, candidates):
        """Find boolean literals and simple boolean expressions."""
        # Boolean literals
        if node.type == "true" or node.type == "false":
            candidates.append(node)
        # Already negated expressions (to potentially un-negate)
        elif node.type == "unary_expression":
            for child in node.children:
                if child.type == "!":
                    candidates.append(node)
                    break
        # Boolean variables/method calls in condition expressions.
        # In if/while/do, parenthesized_expression wraps the condition.
        # In for-loops, the condition can be directly under for_statement.
        elif (
            node.type in ["identifier", "field_access", "method_invocation"]
            and node.parent
            and node.parent.type in ["parenthesized_expression", "for_statement"]
        ):
            candidates.append(node)

        for child in node.children:
            self._find_booleans(child, candidates)
