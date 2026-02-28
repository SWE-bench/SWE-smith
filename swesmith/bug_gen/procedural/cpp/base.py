"""
Base class for cpp procedural modifications.
"""

from abc import ABC
from swesmith.bug_gen.procedural.base import ProceduralModifier


class CppProceduralModifier(ProceduralModifier, ABC):
    """Base class for C++ procedural modifications."""

    pass
