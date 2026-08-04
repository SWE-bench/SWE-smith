"""
Try/Except removal modifier.

This module removes try/except blocks from code, exposing unhandled exceptions.
"""

import libcst

from swesmith.bug_gen.error_handling.base import ErrorHandlingModifier
from swesmith.constants import CodeProperty


class TryExceptRemover(ErrorHandlingModifier):
    """
    Removes try/except blocks, keeping only the try body.

    This exposes the code to unhandled exceptions that were previously caught.
    """

    name = "error_handling_try_except"
    explanation = "Exception handler has been removed, causing unhandled exceptions"
    conditions = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_TRY_EXCEPT]

    class Transformer(ErrorHandlingModifier.Transformer):
        """Transformer that removes try/except wrappers."""

        def leave_Try(self, original_node, updated_node):
            """
            Remove try/except block, keeping only the try body.

            When flip() returns True, this extracts the statements from inside
            the try block and returns them directly, effectively unwrapping
            the exception handling.

            Args:
                original_node: Original Try node
                updated_node: Updated Try node

            Returns:
                List of statements from try body if removing, otherwise original node
            """
            if self.flip():
                # Extract the try body statements
                # updated_node.body.body gives us the list of statements inside try
                try_body = updated_node.body.body

                # If try body is empty, keep the original
                if not try_body:
                    return updated_node

                # Use FlattenSentinel to replace single Try node with multiple statements
                return libcst.FlattenSentinel(try_body)

            return updated_node
