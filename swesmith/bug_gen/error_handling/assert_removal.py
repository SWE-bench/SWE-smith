"""
Assert removal modifier.

This module removes assert statements from code, allowing invalid states to propagate.
"""

import libcst

from swesmith.bug_gen.error_handling.base import ErrorHandlingModifier
from swesmith.constants import CodeProperty


class AssertRemover(ErrorHandlingModifier):
    """
    Removes assert statements from code.

    This removes input validation and precondition checks, allowing
    invalid states to propagate through the code.
    """

    name = "error_handling_assert"
    explanation = "Input validation assertion has been removed"
    conditions = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_ASSERT]

    class Transformer(ErrorHandlingModifier.Transformer):
        """Transformer that removes assert statements."""

        def leave_Assert(self, original_node, updated_node):
            """
            Remove assert statement from the code.

            When flip() returns True, this removes the entire assert statement.

            Args:
                original_node: Original Assert node
                updated_node: Updated Assert node

            Returns:
                RemoveFromParent() if removing, otherwise original node
            """
            if self.flip():
                return libcst.RemoveFromParent()

            return updated_node
