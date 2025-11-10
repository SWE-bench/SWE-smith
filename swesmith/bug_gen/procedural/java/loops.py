"""
Loop-related procedural modifications for Java.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty

JAVA_LANGUAGE = Language(tsjava.language())


class LoopBreakContinueSwapModifier(JavaProceduralModifier):
    """Swaps break and continue statements in loops."""

    name = "func_pm_loop_break_continue_swap"
    explanation = "Break and continue statements in loops may be swapped."
    conditions = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_LOOP]

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find all break and continue statements
        breaks = []
        continues = []
        self._find_break_continue(tree.root_node, breaks, continues)

        if not breaks and not continues:
            return None

        # Swap them
        modified_code = code_entity.src_code

        # Process in reverse order to maintain string positions
        all_statements = [(b, "break") for b in breaks] + [
            (c, "continue") for c in continues
        ]
        all_statements.sort(key=lambda x: x[0].start_byte, reverse=True)

        for node, stmt_type in all_statements:
            start = node.start_byte
            end = node.end_byte

            # Get the full statement text (e.g., "break;", "break label;", "continue;")
            original_text = code_entity.src_code[start:end]

            # Replace just the keyword, preserving labels and semicolon
            if stmt_type == "break":
                replacement = original_text.replace("break", "continue", 1)
            else:
                replacement = original_text.replace("continue", "break", 1)

            modified_code = modified_code[:start] + replacement + modified_code[end:]

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )

    def _find_break_continue(self, node, breaks, continues):
        """Recursively find break and continue statements."""
        if node.type == "break_statement":
            breaks.append(node)
        elif node.type == "continue_statement":
            continues.append(node)

        for child in node.children:
            self._find_break_continue(child, breaks, continues)


class LoopOffByOneModifier(JavaProceduralModifier):
    """Creates off-by-one errors in loop conditions."""

    name = "func_pm_loop_off_by_one"
    explanation = "Loop boundaries may be off by one."
    conditions = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_LOOP]

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find loop conditions with < or <= operators
        candidates = []
        self._find_loop_conditions(tree.root_node, candidates)

        if not candidates:
            return None

        # Pick a random candidate
        target = self.rand.choice(candidates)

        modified_code = code_entity.src_code
        start = target.start_byte
        end = target.end_byte
        operator = code_entity.src_code[start:end]

        # Swap < with <= and vice versa
        if operator == "<":
            replacement = "<="
        elif operator == "<=":
            replacement = "<"
        elif operator == ">":
            replacement = ">="
        elif operator == ">=":
            replacement = ">"
        else:
            return None

        modified_code = modified_code[:start] + replacement + modified_code[end:]

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )

    def _find_loop_conditions(self, node, candidates):
        """Find comparison operators in loop conditions."""
        # Look for for loops and while loops
        if node.type == "for_statement":
            # Find the condition part
            for child in node.children:
                if child.type == "binary_expression":
                    self._extract_comparison_operators(child, candidates)
        elif node.type == "while_statement" or node.type == "do_statement":
            # Find condition
            for child in node.children:
                if child.type == "parenthesized_expression":
                    for subchild in child.children:
                        if subchild.type == "binary_expression":
                            self._extract_comparison_operators(subchild, candidates)

        for child in node.children:
            self._find_loop_conditions(child, candidates)

    def _extract_comparison_operators(self, node, candidates):
        """Extract comparison operators from binary expressions."""
        for child in node.children:
            if child.type in ["<", "<=", ">", ">="]:
                candidates.append(child)
