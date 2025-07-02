"""
Profiles module for SWE-smith.

This module contains repository profiles for different programming languages
and provides a global registry for accessing all profiles.
"""

from .base import RepoProfile, global_registry

# Auto-import all profile modules to populate the registry
from . import c
from . import java
from . import javascript
from . import php
from . import python
from . import golang
from . import rust

__all__ = ["RepoProfile", "global_registry"]
