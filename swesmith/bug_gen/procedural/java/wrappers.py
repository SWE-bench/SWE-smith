"""
Wrapper and defensive code removal for Java.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty

JAVA_LANGUAGE = Language(tsjava.language())


class RemoveTryCatchModifier(JavaProceduralModifier):
    """Removes try-catch blocks, exposing exceptions."""

    name = "func_pm_remove_try_catch"
    explanation = "Try-catch blocks may be missing or incomplete."
    conditions = [CodeProperty.IS_FUNCTION]

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find try statements
        try_statements = []
        self._find_try_statements(tree.root_node, try_statements)

        if not try_statements:
            return None

        # Pick one randomly
        target = self.rand.choice(try_statements)

        # Find the try block body
        try_block = None
        for child in target.children:
            if child.type == "block" and child.start_byte > target.start_byte:
                try_block = child
                break

        if not try_block:
            return None

        # Extract the content of the try block (without the braces)
        try_body_content = self._extract_block_content(code_entity.src_code, try_block)

        if try_body_content is None:
            return None

        # Replace the entire try-catch with just the try body content
        modified_code = (
            code_entity.src_code[: target.start_byte]
            + try_body_content
            + code_entity.src_code[target.end_byte :]
        )

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )

    def _find_try_statements(self, node, results):
        """Find all try/catch constructs, including try-with-resources."""
        if node.type in {"try_statement", "try_with_resources_statement"}:
            results.append(node)
        for child in node.children:
            self._find_try_statements(child, results)

    def _extract_block_content(self, code: str, block_node):
        """Extract content inside block braces."""
        block_text = code[block_node.start_byte : block_node.end_byte]

        # Remove opening and closing braces
        if block_text.startswith("{") and block_text.endswith("}"):
            return block_text[1:-1]
        return None


class RemoveNullCheckModifier(JavaProceduralModifier):
    """Removes null checks, potentially causing NPEs."""

    name = "func_pm_remove_null_check"
    explanation = "Null checks may be missing in the code."
    conditions = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF]

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find if statements with removable null checks.
        null_check_candidates = []
        self._find_null_check_candidates(
            tree.root_node, code_entity.src_code, null_check_candidates
        )

        if not null_check_candidates:
            return None

        # Pick one randomly
        target, condition_node, simplified_condition = self.rand.choice(
            null_check_candidates
        )
        if simplified_condition is None:
            # Standalone null-check if-statements are replaced by their body.
            if_body = None
            for child in target.children:
                if child.type == "block" or child.type in [
                    "expression_statement",
                    "return_statement",
                    "throw_statement",
                ]:
                    if_body = child
                    break

            if not if_body:
                return None

            if if_body.type == "block":
                body_content = self._extract_block_content(
                    code_entity.src_code, if_body
                )
            else:
                body_content = code_entity.src_code[
                    if_body.start_byte : if_body.end_byte
                ]

            if body_content is None:
                return None

            modified_code = (
                code_entity.src_code[: target.start_byte]
                + body_content
                + code_entity.src_code[target.end_byte :]
            )
        else:
            # Compound checks keep the if-statement and drop only the null-check part.
            modified_code = (
                code_entity.src_code[: condition_node.start_byte]
                + simplified_condition
                + code_entity.src_code[condition_node.end_byte :]
            )

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )

    def _find_null_check_candidates(self, node, code: str, results):
        """Find if-statements where null checks can be removed or simplified."""
        if node.type == "if_statement":
            condition_node = None
            for child in node.children:
                if child.type == "parenthesized_expression":
                    condition_node = child
                    break

            if condition_node:
                condition_text = code[
                    condition_node.start_byte : condition_node.end_byte
                ]
                if self._is_simple_null_check(condition_text):
                    results.append((node, condition_node, None))
                else:
                    simplified = self._simplify_compound_null_check(condition_text)
                    if simplified is not None:
                        results.append((node, condition_node, simplified))

        for child in node.children:
            self._find_null_check_candidates(child, code, results)

    @staticmethod
    def _is_simple_null_check(condition_text: str) -> bool:
        """Return True only for standalone null checks like `(x == null)`."""
        text = condition_text.strip()
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()

        # Skip compound conditions to avoid removing unrelated expressions.
        if "&&" in text or "||" in text:
            return False

        if "==" in text:
            parts = text.split("==")
        elif "!=" in text:
            parts = text.split("!=")
        else:
            return False

        if len(parts) != 2:
            return False

        left, right = parts[0].strip(), parts[1].strip()
        return left == "null" or right == "null"

    def _simplify_compound_null_check(self, condition_text: str) -> str | None:
        """Drop one null-check term from top-level `&&`/`||` conditions."""
        text = condition_text.strip()
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()

        split = self._split_top_level_logical(text)
        if split is None:
            return None

        left, _, right = split
        left_is_null_check = self._is_simple_null_check(f"({left})")
        right_is_null_check = self._is_simple_null_check(f"({right})")

        if left_is_null_check == right_is_null_check:
            return None

        remaining = right if left_is_null_check else left
        remaining = remaining.strip()
        if not remaining:
            return None
        return f"({remaining})"

    @staticmethod
    def _split_top_level_logical(condition_text: str):
        """Split top-level binary logical expressions into (left, op, right)."""
        depth = 0
        i = 0
        while i < len(condition_text) - 1:
            char = condition_text[i]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0 and condition_text[i : i + 2] in {"&&", "||"}:
                left = condition_text[:i].strip()
                op = condition_text[i : i + 2]
                right = condition_text[i + 2 :].strip()
                if left and right:
                    return left, op, right
            i += 1
        return None

    def _extract_block_content(self, code: str, block_node):
        """Extract content inside block braces."""
        block_text = code[block_node.start_byte : block_node.end_byte]

        # Remove opening and closing braces
        if block_text.startswith("{") and block_text.endswith("}"):
            return block_text[1:-1]
        return None
