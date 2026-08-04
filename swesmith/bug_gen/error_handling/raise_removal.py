"""
Raise removal modifier.

This module removes raise statements from code, causing silent failures.
"""

import libcst

from swesmith.bug_gen.error_handling.base import ErrorHandlingModifier
from swesmith.constants import CodeProperty


class RaiseRemover(ErrorHandlingModifier):
    """
    Removes raise statements from code.

    This prevents errors from being raised, leading to silent failures
    where invalid conditions are not properly signaled.
    """

    name = "error_handling_raise"
    explanation = "Error raising statement has been removed, causing silent failures"
    conditions = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_RAISE]

    class Transformer(ErrorHandlingModifier.Transformer):
        """Transformer that removes raise statements."""

        def leave_Raise(self, original_node, updated_node):
            """
            Remove raise statement, replacing with Pass if necessary.

            When flip() returns True, this replaces the raise statement with
            a Pass statement to avoid creating an empty block (which would be
            a syntax error in Python).

            Args:
                original_node: Original Raise node
                updated_node: Updated Raise node

            Returns:
                Pass() if removing, otherwise original node
            """
            if self.flip():
                # Replace raise with pass to avoid syntax errors from empty blocks
                # This is safer than trying to determine if the block would be empty
                return libcst.Pass()

            return updated_node
