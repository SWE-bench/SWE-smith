"""
Base class for Java-specific procedural modifications.
"""

from abc import ABC

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import ProceduralModifier


JAVA_LANGUAGE = Language(tsjava.language())


class JavaProceduralModifier(ProceduralModifier, ABC):
    """Base class for Java-specific procedural modifications."""

    @staticmethod
    def has_syntax_errors(code: str) -> bool:
        """
        Check if Java code has syntax errors using tree-sitter.

        Args:
            code: Java source code to validate

        Returns:
            True if the code has syntax errors, False otherwise
        """
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code, "utf8"))

        def check_for_errors(node) -> bool:
            """Recursively check for ERROR or MISSING nodes"""
            if node.type in ["ERROR", "MISSING"]:
                return True
            for child in node.children:
                if check_for_errors(child):
                    return True
            return False

        return check_for_errors(tree.root_node)

    @staticmethod
    def validate_syntax(original_code: str, modified_code: str) -> bool | None:
        """
        Validate that modified code doesn't introduce syntax errors.

        Args:
            original_code: Original source code
            modified_code: Modified source code

        Returns:
            True if modified code is syntactically valid,
            False if it has syntax errors,
            None if the code is unchanged
        """
        # Return None so callers can reject no-op rewrites explicitly.
        if original_code == modified_code:
            return None

        # Check if modified code has syntax errors
        return not JavaProceduralModifier.has_syntax_errors(modified_code)
