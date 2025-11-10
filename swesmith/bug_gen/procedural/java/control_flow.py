"""
Control flow-related procedural modifications for Java code.
"""

import random

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

        target = random.choice(candidates)

        # Extract components
        condition = None
        if_body = None
        else_body = None

        for i, child in enumerate(target.children):
            if child.type == "parenthesized_expression":
                condition = code[child.start_byte : child.end_byte]
            elif child.type == "block" and if_body is None:
                if_body = code[child.start_byte : child.end_byte]
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
        """Find simple if-else statements (not else-if chains)."""
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


class ControlShuffleLinesModifier(JavaProceduralModifier):
    """Shuffle independent lines within a block."""

    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._shuffle_lines(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _shuffle_lines(self, code: str, node) -> str:
        """Shuffle statements in blocks."""
        candidates = []
        self._find_blocks(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        statements = [
            child
            for child in target.children
            if child.type
            in [
                "expression_statement",
                "local_variable_declaration",
                "return_statement",
            ]
        ]

        if len(statements) < 2:
            return code

        # Extract statement texts
        stmt_texts = [code[stmt.start_byte : stmt.end_byte] for stmt in statements]

        # Shuffle
        original_order = stmt_texts.copy()
        random.shuffle(stmt_texts)

        # If nothing changed, try again or return original
        if stmt_texts == original_order:
            return code

        # Reconstruct the block
        first_stmt = statements[0]
        last_stmt = statements[-1]

        # Get the indentation from the first statement
        indent_start = first_stmt.start_byte
        while indent_start > 0 and code[indent_start - 1] in [" ", "\t"]:
            indent_start -= 1

        indent = code[indent_start : first_stmt.start_byte]

        # Build new block content
        new_block = "\n".join(indent + stmt for stmt in stmt_texts)

        # Properly concatenate the result
        return code[:indent_start] + new_block + "\n" + code[last_stmt.end_byte :]

    def _find_blocks(self, node, candidates):
        """Find blocks with multiple statements."""
        if node.type == "block":
            statements = [
                child
                for child in node.children
                if child.type
                in [
                    "expression_statement",
                    "local_variable_declaration",
                    "return_statement",
                ]
            ]
            if len(statements) >= 2:
                candidates.append(node)
        for child in node.children:
            self._find_blocks(child, candidates)
