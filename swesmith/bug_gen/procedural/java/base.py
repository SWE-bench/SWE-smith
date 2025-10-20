"""
Base class for Java-specific procedural modifications.
"""

from abc import ABC

from swesmith.bug_gen.procedural.base import ProceduralModifier


class JavaProceduralModifier(ProceduralModifier, ABC):
    """Base class for Java-specific procedural modifications."""

    pass

