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
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find all string literals
        string_literals = []
        self._find_string_literals(tree.root_node, string_literals)

        if not string_literals:
            return None

        # Try to find a string that matches our swap pairs
        candidates = []
        for lit in string_literals:
            lit_text = code_entity.src_code[lit.start_byte : lit.end_byte]
            # Remove quotes
            if lit_text.startswith('"') and lit_text.endswith('"'):
                content = lit_text[1:-1]
                for pair in self.SWAP_PAIRS:
                    if content in pair:
                        candidates.append((lit, content, pair))
                        break

        if not candidates:
            # No matching pairs, just pick a random string and modify it slightly
            target = self.rand.choice(string_literals)
            lit_text = code_entity.src_code[target.start_byte : target.end_byte]

            if lit_text.startswith('"') and lit_text.endswith('"'):
                content = lit_text[1:-1]

                # Try different modifications
                if len(content) > 0:
                    # Add/remove a character
                    if len(content) > 1:
                        modified_content = content[:-1]  # Remove last char
                    else:
                        modified_content = content + content  # Double it

                    replacement = f'"{modified_content}"'
                else:
                    # Empty string becomes space
                    replacement = '" "'

                modified_code = (
                    code_entity.src_code[: target.start_byte]
                    + replacement
                    + code_entity.src_code[target.end_byte :]
                )
            else:
                return None
        else:
            # Use a swap pair
            target, content, pair = self.rand.choice(candidates)

            # Find the replacement
            if content == pair[0]:
                new_content = pair[1]
            else:
                new_content = pair[0]

            replacement = f'"{new_content}"'

            modified_code = (
                code_entity.src_code[: target.start_byte]
                + replacement
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

    def _find_string_literals(self, node, results):
        """Find all string literals."""
        if node.type == "string_literal":
            results.append(node)
        for child in node.children:
            self._find_string_literals(child, results)


class ClassRemoveInterfaceModifier(JavaProceduralModifier):
    """Removes interface implementations from classes."""

    name = "func_pm_class_remove_interface"
    explanation = "Class may be missing interface implementations."
    conditions = [CodeProperty.IS_CLASS, CodeProperty.HAS_PARENT]

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find class declaration
        class_decl = None
        self._find_class_declaration(tree.root_node, class_decl_list := [])

        if not class_decl_list:
            return None

        class_decl = class_decl_list[0]

        # Find 'implements' clause
        implements_node = None
        for child in class_decl.children:
            if child.type == "super_interfaces":
                implements_node = child
                break

        if not implements_node:
            return None

        # Remove the entire implements clause
        modified_code = (
            code_entity.src_code[: implements_node.start_byte]
            + code_entity.src_code[implements_node.end_byte :]
        )

        # Clean up extra whitespace
        modified_code = modified_code.replace("  ", " ")

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )

    def _find_class_declaration(self, node, results):
        """Find class declaration."""
        if node.type == "class_declaration":
            results.append(node)
            return  # Only get the first one
        for child in node.children:
            self._find_class_declaration(child, results)
