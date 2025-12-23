"""
Base classes and utilities for procedural bug generation across different languages.

This module provides the foundational infrastructure for language-specific procedural
modification techniques. Language-specific implementations should be placed in their
respective subdirectories (e.g., python/, javascript/, java/).
"""

# For backward compatibility, expose Python-specific classes
from swesmith.bug_gen.procedural.golang import MODIFIERS_GOLANG
from swesmith.bug_gen.procedural.python import MODIFIERS_PYTHON
from swesmith.bug_gen.procedural.rust import MODIFIERS_RUST

MAP_EXT_TO_MODIFIERS = {
    ".go": MODIFIERS_GOLANG,
    ".py": MODIFIERS_PYTHON,
    ".rs": MODIFIERS_RUST,
}
