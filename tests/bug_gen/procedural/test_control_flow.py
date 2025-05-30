import libcst
import pytest
from swesmith.bug_gen.procedural.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        # Simple if-else inversion
        (
            """
def foo(x):
    if x > 0:
        return 1
    else:
        return -1
""",
            """def foo(x):
    if x > 0:
        return -1
    else:
        return 1
""",
        ),
        # No else branch, should not change
        (
            """
def bar(x):
    if x == 0:
        return 0
""",
            """def bar(x):
    if x == 0:
        return 0
""",
        ),
    ],
)
def test_control_if_else_invert(src, expected):
    module = libcst.parse_module(src)
    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert modified.code.strip() == expected.strip()


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Function with two statements to shuffle
        (
            """
def foo():
    a = 1
    b = 2
""",
            [
                "def foo():\n    a = 1\n    b = 2\n",
                "def foo():\n    b = 2\n    a = 1\n",
            ],
        ),
        # Function with only one statement, should not change
        (
            """
def bar():
    x = 42
""",
            [
                "def bar():\n    x = 42\n",
            ],
        ),
    ],
)
def test_control_shuffle_lines(src, expected_variants):
    module = libcst.parse_module(src)
    modifier = ControlShuffleLinesModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert any(
        modified.code.strip() == variant.strip() for variant in expected_variants
    )
