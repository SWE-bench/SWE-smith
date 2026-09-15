"""
Base class for error handling corruption modifiers.

This module provides the foundation for removing exception handling mechanisms
(try/except, assert, raise) from Python code using libcst transformations.
"""

import libcst

from abc import ABC
from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity


class ErrorHandlingModifier(ProceduralModifier, ABC):
    """
    Base class for error handling corruption using LibCST.

    This class extends ProceduralModifier to provide common functionality
    for removing exception handling constructs from Python code.
    """

    class Transformer(libcst.CSTTransformer):
        """
        Nested LibCST transformer for error handling modifications.

        This transformer walks the CST and probabilistically removes
        error handling nodes (try/except, assert, raise).
        """

        def __init__(self, parent_modifier):
            """
            Initialize transformer with reference to parent modifier.

            Args:
                parent_modifier: The ErrorHandlingModifier instance that created this transformer
            """
            self.parent = parent_modifier
            super().__init__()

        def flip(self) -> bool:
            """
            Probabilistically decide whether to apply a modification.

            Returns:
                True with probability equal to parent's likelihood, False otherwise
            """
            return self.parent.flip()

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        """
        Apply error handling corruption to a code entity.

        This method:
        1. Parses the code entity's source into a CST
        2. Applies the transformer to remove error handling
        3. Returns a BugRewrite with the modified code

        Args:
            code_entity: The code entity to modify

        Returns:
            BugRewrite if modification was successful, None otherwise
        """
        try:
            module = libcst.parse_module(code_entity.src_code)
        except libcst.ParserSyntaxError:
            # Failed to parse code - skip this entity
            return None

        changed = False
        transformer = self.Transformer(self)

        try:
            # Attempt modification up to max_attempts times
            for _ in range(self.max_attempts):
                modified = module.visit(transformer)
                if module.code != modified.code:
                    changed = True
                    break
        except (AttributeError, TypeError, ValueError):
            # Transformation failed - return None
            return None

        if not changed:
            # No modifications made - return None
            return None

        return BugRewrite(
            rewrite=modified.code,
            explanation=self.explanation,
            cost=0.0,
            strategy="error_handling",
        )
