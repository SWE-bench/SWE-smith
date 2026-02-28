"""
Control flow-related procedural modifications for Java code.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

JAVA_LANGUAGE = Language(tsjava.language())


class ControlIfElseInvertModifier(JavaProceduralModifier):
    """Invert if-else branches."""

    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = 5

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._invert_if_else_statements(
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

    def _invert_if_else_statements(self, code: str, node) -> str:
        """Invert if-else statements."""
        candidates = []
        self._find_if_else_statements(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)

        # Extract components
        condition = None
        if_body = None
        else_body = None
        then_statement = None

        for i, child in enumerate(target.children):
            if child.type == "parenthesized_expression":
                condition = code[child.start_byte : child.end_byte]
                # The immediate sibling after the condition is the "then" statement,
                # which may be a block or a single statement.
                if i + 1 < len(target.children):
                    then_statement = target.children[i + 1]
                    if_body = code[then_statement.start_byte : then_statement.end_byte]
            elif child.type == "else":
                # Next sibling should be the else body
                if i + 1 < len(target.children):
                    else_node = target.children[i + 1]
                    else_body = code[else_node.start_byte : else_node.end_byte]

        if condition and if_body and else_body:
            # Swap bodies WITHOUT negating condition (creates actual bug)
            # This matches Python and Go implementations
            inverted = f"if {condition} {else_body} else {if_body}"
            return code[: target.start_byte] + inverted + code[target.end_byte :]

        return code

    def _find_if_else_statements(self, node, candidates):
        """Find invertible if/else statements.

        We skip if-statements whose else branch points to another if-statement
        (chain head/middle), but allow terminal else-if nodes that end in an
        actual else branch.
        """
        if node.type == "if_statement":
            # Check if it has an else branch
            has_else = False
            has_else_if = False

            for i, child in enumerate(node.children):
                if child.type == "else":
                    has_else = True
                    # Check if the next node is another if_statement (else-if chain)
                    if i + 1 < len(node.children):
                        next_node = node.children[i + 1]
                        if next_node.type == "if_statement":
                            has_else_if = True
                    break

            # Only accept simple if-else, not else-if chains
            if has_else and not has_else_if:
                candidates.append(node)

        for child in node.children:
            self._find_if_else_statements(child, candidates)
