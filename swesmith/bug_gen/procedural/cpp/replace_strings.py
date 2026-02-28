"""
String-related procedural modifications for C++ code.
"""

import string

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.cpp.base import CppProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty

CPP_LANGUAGE = Language(tscpp.language())


class ReplaceStringTypoModifier(CppProceduralModifier):
    """Introduce typos into string literals."""

    explanation: str = "A typo has been introduced in a string constant."
    name: str = "func_pm_string_typo"
    conditions: list = [CodeProperty.IS_FUNCTION]

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._introduce_string_typos(
            code_entity.src_code, tree.root_node
        )

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _introduce_string_typos(self, code: str, node) -> str:
        """Introduce typos into string literals."""
        candidates = []
        self._find_string_literals(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)
        original_string = code[target.start_byte : target.end_byte]

        # Extract the string content (remove quotes)
        if original_string.startswith('"') and original_string.endswith('"'):
            # Regular string literal
            content = original_string[1:-1]
            if not content:  # Empty string
                return code
            modified_content = self._introduce_typo(content)
            modified_string = f'"{modified_content}"'
        elif original_string.startswith('L"') and original_string.endswith('"'):
            # Wide string literal
            content = original_string[2:-1]
            if not content:
                return code
            modified_content = self._introduce_typo(content)
            modified_string = f'L"{modified_content}"'
        elif original_string.startswith('R"') and '"' in original_string[2:]:
            # Raw string literal (e.g., R"delim(...)delim")
            # Find the delimiter and content
            delimiter_end = original_string.find("(", 2)
            if delimiter_end == -1:
                return code
            prefix = original_string[: delimiter_end + 1]
            suffix_start = original_string.rfind(")")
            if suffix_start == -1:
                return code
            suffix = original_string[suffix_start:]
            content = original_string[delimiter_end + 1 : suffix_start]
            if not content:
                return code
            modified_content = self._introduce_typo(content)
            modified_string = f"{prefix}{modified_content}{suffix}"
        else:
            # Unknown string format, skip
            return code

        return code[: target.start_byte] + modified_string + code[target.end_byte :]

    def _introduce_typo(self, content: str) -> str:
        """Introduce a single character typo in the string content."""
        if not content:
            return content

        # Choose a random position
        pos = self.rand.randint(0, len(content) - 1)
        char = content[pos]

        # Introduce typo: change one character
        # Options: swap adjacent, change to similar character, or random change
        typo_choice = self.rand.choice(["adjacent", "similar", "random"])

        if typo_choice == "adjacent" and len(content) > 1:
            # Swap with adjacent character (common typo)
            if pos > 0:
                new_char = content[pos - 1]
                return content[: pos - 1] + char + new_char + content[pos + 1 :]
            elif pos < len(content) - 1:
                new_char = content[pos + 1]
                return content[:pos] + new_char + char + content[pos + 2 :]
            return content

        elif typo_choice == "similar" and char.isalnum():
            # Change to a visually similar or adjacent keyboard character
            if char.isalpha():
                # Change to adjacent letter in alphabet or common typo
                if char.lower() in "qwertyuiopasdfghjklzxcvbnm":
                    # Use QWERTY keyboard layout adjacent keys
                    adjacent_chars = self._get_qwerty_adjacent(char.lower())
                    if adjacent_chars:
                        new_char = self.rand.choice(adjacent_chars)
                        if char.isupper():
                            new_char = new_char.upper()
                        return content[:pos] + new_char + content[pos + 1 :]
            elif char.isdigit():
                # Change to adjacent digit
                digit = int(char)
                if digit > 0:
                    new_char = str(digit - 1)
                else:
                    new_char = str(digit + 1)
                return content[:pos] + new_char + content[pos + 1 :]

        # Random change (fallback or explicit choice)
        while True:
            # Choose a random printable ASCII character
            new_char = self.rand.choice(string.printable)
            if new_char != char and new_char not in "\n\r\t":
                break
        return content[:pos] + new_char + content[pos + 1 :]

    def _get_qwerty_adjacent(self, char: str) -> list:
        """Get adjacent characters on QWERTY keyboard."""
        qwerty_map = {
            "q": ["w", "a"],
            "w": ["q", "e", "s", "a"],
            "e": ["w", "r", "d", "s"],
            "r": ["e", "t", "f", "d"],
            "t": ["r", "y", "g", "f"],
            "y": ["t", "u", "h", "g"],
            "u": ["y", "i", "j", "h"],
            "i": ["u", "o", "k", "j"],
            "o": ["i", "p", "l", "k"],
            "p": ["o", "l"],
            "a": ["q", "s", "z"],
            "s": ["a", "w", "d", "x", "z"],
            "d": ["s", "e", "f", "c", "x"],
            "f": ["d", "r", "g", "v", "c"],
            "g": ["f", "t", "h", "b", "v"],
            "h": ["g", "y", "j", "n", "b"],
            "j": ["h", "u", "k", "m", "n"],
            "k": ["j", "i", "l", "m"],
            "l": ["k", "o", "p"],
            "z": ["a", "x"],
            "x": ["z", "s", "c"],
            "c": ["x", "d", "v"],
            "v": ["c", "f", "b"],
            "b": ["v", "g", "n"],
            "n": ["b", "h", "m"],
            "m": ["n", "j"],
        }
        return qwerty_map.get(char.lower(), [])

    def _find_string_literals(self, node, candidates):
        """Find string literal nodes in the AST."""
        # C++ tree-sitter node types for strings
        if node.type == "string_literal":
            # Regular string literal "..." or L"..."
            candidates.append(node)
        elif node.type == "raw_string_literal":
            # Raw string literal R"delim(...)delim"
            candidates.append(node)
        # Note: We skip char_literal since they're usually single characters
        # and introducing typos in them is less meaningful

        for child in node.children:
            self._find_string_literals(child, candidates)
