"""
Literal value modifications for Java.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty

JAVA_LANGUAGE = Language(tsjava.language())


class StringLiteralModifier(JavaProceduralModifier):
    """Modifies string literals to introduce bugs."""

    name = "func_pm_string_literal_change"
    explanation = "String literals may have incorrect values."
    conditions = [CodeProperty.IS_FUNCTION]

    # Common string pairs that when swapped create bugs
    SWAP_PAIRS = [
        ("true", "false"),
        ("GET", "POST"),
        ("PUT", "POST"),
        ("DELETE", "GET"),
        ("yes", "no"),
        ("on", "off"),
        ("enabled", "disabled"),
        ("start", "stop"),
        ("open", "close"),
        ("read", "write"),
        ("", " "),  # Empty to space
        ("0", "1"),
        ("/", "\\"),
        (":", ";"),
        (",", "."),
    ]

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find all string literals
        string_literals = []
        self._find_string_literals(tree.root_node, string_literals)

        if not string_literals:
            return None

        candidates = self._find_pair_candidates(code_entity.src_code, string_literals)
        if candidates:
            modified_code = self._apply_swap_pair(code_entity.src_code, candidates)
        else:
            modified_code = self._apply_fallback_mutation(
                code_entity.src_code, string_literals
            )

        if modified_code is None:
            return None

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )

    def _find_pair_candidates(self, code: str, string_literals):
        """Return string literals that match configured swap pairs."""
        candidates = []
        for literal in string_literals:
            literal_text = code[literal.start_byte : literal.end_byte]
            content = self._extract_string_content(literal_text)
            if content is None:
                continue

            for pair in self.SWAP_PAIRS:
                if content in pair:
                    candidates.append((literal, content, pair))
                    break
        return candidates

    def _apply_swap_pair(self, code: str, candidates) -> str:
        """Swap a known string pair in one random literal."""
        target, content, pair = self.rand.choice(candidates)
        new_content = pair[1] if content == pair[0] else pair[0]
        replacement = f'"{new_content}"'
        return self._replace_node_text(code, target, replacement)

    def _apply_fallback_mutation(self, code: str, string_literals) -> str | None:
        """Fallback mutation when no swap pairs match."""
        fallback_candidates = []
        for literal in string_literals:
            literal_text = code[literal.start_byte : literal.end_byte]
            content = self._extract_string_content(literal_text)
            if content:
                fallback_candidates.append((literal, content))

        if not fallback_candidates:
            return None

        target, content = self.rand.choice(fallback_candidates)
        modified_content = content[:-1] if len(content) > 1 else content + content
        replacement = f'"{modified_content}"'
        return self._replace_node_text(code, target, replacement)

    @staticmethod
    def _extract_string_content(literal_text: str) -> str | None:
        """Extract content from simple quoted literals and skip text blocks."""
        if not (literal_text.startswith('"') and literal_text.endswith('"')):
            return None
        if literal_text.startswith('"""'):
            return None
        return literal_text[1:-1]

    @staticmethod
    def _replace_node_text(code: str, node, replacement: str) -> str:
        return code[: node.start_byte] + replacement + code[node.end_byte :]

    def _find_string_literals(self, node, results):
        """Find all string literals."""
        if node.type == "string_literal":
            results.append(node)
        for child in node.children:
            self._find_string_literals(child, results)
