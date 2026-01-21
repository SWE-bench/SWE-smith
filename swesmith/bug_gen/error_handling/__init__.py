"""
Error handling corruption module.

This module provides bug generation through removal of exception handling
mechanisms (try/except, assert, raise statements).
"""

from swesmith.bug_gen.error_handling.assert_removal import AssertRemover
from swesmith.bug_gen.error_handling.raise_removal import RaiseRemover
from swesmith.bug_gen.error_handling.try_except import TryExceptRemover

MODIFIERS_ERROR_HANDLING = [
    TryExceptRemover,
    AssertRemover,
    RaiseRemover,
]

__all__ = [
    "MODIFIERS_ERROR_HANDLING",
    "TryExceptRemover",
    "AssertRemover",
    "RaiseRemover",
]