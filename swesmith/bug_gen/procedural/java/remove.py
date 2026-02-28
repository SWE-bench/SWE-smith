"""
Removal-related procedural modifications for Java code.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

JAVA_LANGUAGE = Language(tsjava.language())


class RemoveConditionalModifier(JavaProceduralModifier):
    """Remove conditional statements."""

    explanation: str = CommonPMs.REMOVE_CONDITIONAL.explanation
    name: str = CommonPMs.REMOVE_CONDITIONAL.name
    conditions: list = CommonPMs.REMOVE_CONDITIONAL.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._remove_conditionals(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_conditionals(self, code: str, node) -> str:
        """Remove if statements."""
        candidates = []
        self._find_conditionals(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)

        # Find the if body
        body = None
        for child in target.children:
            if child.type == "block":
                body = child
                break

        if body:
            # Extract body content (without braces)
            body_content = code[body.start_byte + 1 : body.end_byte - 1]
            return code[: target.start_byte] + body_content + code[target.end_byte :]

        # If no block, just remove the entire conditional
        return code[: target.start_byte] + code[target.end_byte :]

    def _find_conditionals(self, node, candidates):
        """Find if statements."""
        if node.type == "if_statement":
            candidates.append(node)
        for child in node.children:
            self._find_conditionals(child, candidates)


class RemoveAssignModifier(JavaProceduralModifier):
    """Remove assignment statements."""

    explanation: str = CommonPMs.REMOVE_ASSIGNMENT.explanation
    name: str = CommonPMs.REMOVE_ASSIGNMENT.name
    conditions: list = CommonPMs.REMOVE_ASSIGNMENT.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._remove_assignments(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_assignments(self, code: str, node) -> str:
        """Remove assignment statements."""
        candidates = []
        self._find_assignments(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)

        # Find the statement containing this assignment
        stmt = target
        while stmt.parent and stmt.parent.type != "block":
            stmt = stmt.parent

        if stmt.type == "expression_statement":
            # Remove the entire statement including the semicolon
            # Also remove the newline if present
            end_byte = stmt.end_byte
            if end_byte < len(code) and code[end_byte] == "\n":
                end_byte += 1
            return code[: stmt.start_byte] + code[end_byte:]

        return code

    def _find_assignments(self, node, candidates):
        """Find assignment expressions used in reassignment statements."""
        if node.type == "assignment_expression":
            candidates.append(node)
        for child in node.children:
            self._find_assignments(child, candidates)
