"""
Base classes and utilities for procedural bug generation across different languages.

This module provides the foundational infrastructure for language-specific procedural
modification techniques. Language-specific implementations should be placed in their
respective subdirectories (e.g., python/, javascript/, java/).
"""

# For backward compatibility, expose Python-specific classes
from swesmith.bug_gen.procedural.golang import MODIFIERS_GOLANG
from swesmith.bug_gen.procedural.java import MODIFIERS_JAVA, NEW_MODIFIERS_JAVA
from swesmith.bug_gen.procedural.python import MODIFIERS_PYTHON

MAP_EXT_TO_MODIFIERS = {
    ".go": MODIFIERS_GOLANG,
    ".java": MODIFIERS_JAVA,
    ".py": MODIFIERS_PYTHON,
}

MAP_EXT_TO_NEW_MODIFIERS = {
    ".java": NEW_MODIFIERS_JAVA,
}
