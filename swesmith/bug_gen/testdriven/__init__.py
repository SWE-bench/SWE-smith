"""
Test-Driven Bug Injection

Generate bugs by mutating tests and using LLMs to reconcile code,
creating spec-overfitting bugs where code satisfies one modified test
but breaks other previously passing tests.
"""

from .discover import TestCandidate, discover_tests
from .mutators import MUTATION_REGISTRY, TestMutation
from .reconcile import reconcile_code_with_test

__all__ = [
    "TestCandidate",
    "discover_tests",
    "MUTATION_REGISTRY",
    "TestMutation",
    "reconcile_code_with_test",
]
