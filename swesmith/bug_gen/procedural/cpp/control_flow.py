"""
Control flow-related procedural modifications for C++ code.
"""

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.cpp.base import CppProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

CPP_LANGUAGE = Language(tscpp.language())


class ControlIfElseInvertModifier(CppProceduralModifier):
    """Invert if-else branches."""

    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = 1  # Reduced from 5 to allow simpler code

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._invert_if_else_statements(
            code_entity.src_code, tree.root_node
        )

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _invert_if_else_statements(self, code: str, node) -> str:
        """Invert if-else statements (including else-if chains and bare if statements)."""
        candidates = []
        self._find_all_if_statements(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)

        # Extract components
        condition = None
        if_body = None
        else_body = None

        for i, child in enumerate(target.children):
            # Handle condition_clause (contains the condition expression)
            if child.type == "condition_clause":
                condition = code[child.start_byte : child.end_byte]
            elif child.type == "compound_statement" and if_body is None:
                if_body = code[child.start_byte : child.end_byte]
            elif child.type == "else_clause":
                # else_clause contains the else body
                for subchild in child.children:
                    if subchild.type == "compound_statement":
                        else_body = code[subchild.start_byte : subchild.end_byte]
                        break
                    elif subchild.type == "if_statement":
                        # Handle else-if: extract the if body as else body
                        for subsubchild in subchild.children:
                            if subsubchild.type == "compound_statement":
                                else_body = code[
                                    subsubchild.start_byte : subsubchild.end_byte
                                ]
                                break

        if condition and if_body:
            if else_body:
                # Swap bodies WITHOUT negating condition (creates actual bug)
                inverted = f"if {condition} {else_body} else {if_body}"
            else:
                # If no else, create one with empty body (inverts the logic)
                inverted = f"if {condition} {{}} else {if_body}"
            return code[: target.start_byte] + inverted + code[target.end_byte :]

        return code

    def _find_all_if_statements(self, node, candidates):
        """Find all if statements (with or without else clauses)."""
        if node.type == "if_statement":
            candidates.append(node)

        for child in node.children:
            self._find_all_if_statements(child, candidates)


class ControlShuffleLinesModifier(CppProceduralModifier):
    """Shuffle independent lines within a block."""

    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._shuffle_lines(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
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

        target = self.rand.choice(candidates)
        statements = [
            child
            for child in target.children
            if child.type
            in [
                "expression_statement",
                "declaration",
                "return_statement",
            ]
        ]

        if len(statements) < 2:
            return code

        # Extract statement texts
        stmt_texts = [code[stmt.start_byte : stmt.end_byte] for stmt in statements]

        # Shuffle
        original_order = stmt_texts.copy()
        self.rand.shuffle(stmt_texts)

        # If shuffle produced the same order, return original unchanged
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

        # Build new block content with original indentation
        new_block = "\n".join(indent + stmt for stmt in stmt_texts)

        # Replace statements region, preserving the rest of the code
        # (including newline and closing brace after last statement)
        return code[:indent_start] + new_block + code[last_stmt.end_byte :]

    def _find_blocks(self, node, candidates):
        """Find blocks with multiple statements."""
        if node.type == "compound_statement":
            statements = [
                child
                for child in node.children
                if child.type
                in [
                    "expression_statement",
                    "declaration",
                    "return_statement",
                ]
            ]
            if len(statements) >= 2:
                candidates.append(node)
        for child in node.children:
            self._find_blocks(child, candidates)
