"""
Base classes and utilities for procedural bug generation across different languages.

This module provides the foundational infrastructure for language-specific procedural
modification techniques. Language-specific implementations should be placed in their
respective subdirectories (e.g., python/, javascript/, java/).
"""

# For backward compatibility, expose Python-specific classes
from swesmith.bug_gen.procedural.cpp import MODIFIERS_CPP
from swesmith.bug_gen.procedural.golang import MODIFIERS_GOLANG
from swesmith.bug_gen.procedural.java import MODIFIERS_JAVA
from swesmith.bug_gen.procedural.javascript import MODIFIERS_JAVASCRIPT
from swesmith.bug_gen.procedural.python import MODIFIERS_PYTHON
from swesmith.bug_gen.procedural.rust import MODIFIERS_RUST
from swesmith.bug_gen.procedural.typescript import MODIFIERS_TYPESCRIPT

MAP_EXT_TO_MODIFIERS = {
    ".cc": MODIFIERS_CPP,
    ".cpp": MODIFIERS_CPP,
    ".cxx": MODIFIERS_CPP,
    ".go": MODIFIERS_GOLANG,
    ".java": MODIFIERS_JAVA,
    ".h": MODIFIERS_CPP,
    ".hpp": MODIFIERS_CPP,
    ".js": MODIFIERS_JAVASCRIPT,
    ".py": MODIFIERS_PYTHON,
    ".rs": MODIFIERS_RUST,
    ".ts": MODIFIERS_TYPESCRIPT,
    ".tsx": MODIFIERS_TYPESCRIPT,
}
