import libcst
import pytest
from swesmith.bug_gen.procedural.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
)


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Case 1: left is a BinaryOperation
        (
            """
def foo(a, b, c):
    return a + b + c
""",
            [
                "def foo(a, b, c):\n    return a + c\n",
                "def foo(a, b, c):\n    return a + b\n",
            ],
        ),
        # Case 2: right is a BinaryOperation
        (
            """
def bar(x, y, z):
    return x * (y * z)
""",
            [
                "def bar(x, y, z):\n    return x * z\n",
            ],
        ),
        # Case 3: no BinaryOperation, should not change
        (
            """
def baz(x):
    return x + 1
""",
            [
                "def baz(x):\n    return x + 1\n",
            ],
        ),
        # Case 4: multiple BinaryOperations, should break one chain
        (
            """
def qux(a, b, c, d):
    return a + b + c * d
""",
            [
                "def qux(a, b, c, d):\n    return a + (c * d)\n",
                "def qux(a, b, c, d):\n    return (a + b) + c\n",
                "def qux(a, b, c, d):\n    return a + c * d\n",
                "def qux(a, b, c, d):\n    return (a + b) + d\n",
            ],
        ),
    ],
)
def test_operation_break_chains(src, expected_variants):
    module = libcst.parse_module(src)
    modifier = OperationBreakChainsModifier(likelihood=0.5, seed=42)  # deterministic
    modified = module.visit(modifier)
    result = modified.code
    assert any(result.strip() == variant.strip() for variant in expected_variants), (
        f"Got: {result!r}, expected one of: {expected_variants!r}"
    )


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Case 1: left is an integer constant
        (
            """
def foo():
    return 2 + x
""",
            [
                "def foo():\n    return 1 + x\n",
                "def foo():\n    return 3 + x\n",
            ],
        ),
        # Case 2: right is an integer constant
        (
            """
def bar():
    return y - 5
""",
            [
                "def bar():\n    return y - 4\n",
                "def bar():\n    return y - 6\n",
            ],
        ),
        # Case 3: both sides are integer constants
        (
            """
def baz():
    return 10 * 20
""",
            [
                "def baz():\n    return 9 * 19\n",
                "def baz():\n    return 9 * 21\n",
                "def baz():\n    return 11 * 19\n",
                "def baz():\n    return 11 * 21\n",
            ],
        ),
        # Case 4: no integer constants, should not change
        (
            """
def qux(a, b):
    return a / b
""",
            [
                "def qux(a, b):\n    return a / b\n",
            ],
        ),
    ],
)
def test_operation_change_constants(src, expected_variants):
    module = libcst.parse_module(src)
    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)  # always flip
    modified = module.visit(modifier)
    result = modified.code
    assert any(result.strip() == variant.strip() for variant in expected_variants), (
        f"Got: {result!r}, expected one of: {expected_variants!r}"
    )
