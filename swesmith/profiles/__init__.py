"""
Profiles module for SWE-smith.

This module contains repository profiles for different programming languages
and provides a global registry for accessing all profiles.
"""

from .base import RepoProfile, global_registry

__all__ = ["RepoProfile", "global_registry"]
