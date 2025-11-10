"""
Boolean-related procedural modifications for Java code.
"""

import random

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMProp
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

        target = random.choice(candidates)
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
        # Boolean variables/fields in conditions
        elif node.type == "identifier" and node.parent and node.parent.type in [
            "if_statement",
            "while_statement",
            "do_statement",
            "parenthesized_expression",
        ]:
            candidates.append(node)
        # Boolean method calls
        elif node.type == "method_invocation" and node.parent and node.parent.type in [
            "if_statement",
            "while_statement",
            "do_statement",
            "parenthesized_expression",
        ]:
            candidates.append(node)

        for child in node.children:
            self._find_booleans(child, candidates)


class BooleanShortCircuitModifier(JavaProceduralModifier):
    """Change short-circuit operators (&&, ||) to non-short-circuit (&, |)."""

    explanation: str = "Changed short-circuit operators"
    name: str = "func_pm_bool_shortcircuit"
    conditions: list = []

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_shortcircuit(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_shortcircuit(self, code: str, node) -> str:
        """Change && to & and || to |."""
        candidates = []
        self._find_shortcircuit_ops(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        operator_text = code[target.start_byte : target.end_byte]

        # Change operator
        if operator_text == "&&":
            replacement = "&"
        elif operator_text == "||":
            replacement = "|"
        else:
            return code

        return code[: target.start_byte] + replacement + code[target.end_byte :]

    def _find_shortcircuit_ops(self, node, candidates):
        """Find && and || operators."""
        if node.type == "binary_expression":
            for child in node.children:
                if child.type in ["&&", "||"]:
                    candidates.append(child)
        for child in node.children:
            self._find_shortcircuit_ops(child, candidates)

