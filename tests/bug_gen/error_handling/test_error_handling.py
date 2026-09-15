import libcst
import pytest
from swesmith.bug_gen.error_handling.try_except import TryExceptRemover
from swesmith.bug_gen.error_handling.assert_removal import AssertRemover
from swesmith.bug_gen.error_handling.raise_removal import RaiseRemover


@pytest.mark.parametrize(
    "src,expected",
    [
        # Remove try/except, keep try body
        (
            """
def foo():
    try:
        x = risky_call()
    except Exception:
        x = None
    return x
""",
            """def foo():
    x = risky_call()
    return x
""",
        ),
        # Try with multiple statements in body
        (
            """
def bar():
    try:
        a = 1
        b = 2
    except ValueError:
        a = 0
        b = 0
    return a + b
""",
            """def bar():
    a = 1
    b = 2
    return a + b
""",
        ),
    ],
)
def test_try_except_remover(src, expected):
    module = libcst.parse_module(src)
    modifier = TryExceptRemover(likelihood=1.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    assert modified.code.strip() == expected.strip()


@pytest.mark.parametrize(
    "src,expected",
    [
        # Remove single assert
        (
            """
def foo(x):
    assert x > 0
    return x * 2
""",
            """def foo(x):
    return x * 2
""",
        ),
        # Remove assert with message
        (
            """
def bar(data):
    assert data is not None, "data cannot be None"
    return len(data)
""",
            """def bar(data):
    return len(data)
""",
        ),
        # Multiple asserts
        (
            """
def validate(x, y):
    assert x > 0
    assert y > 0
    return x + y
""",
            """def validate(x, y):
    return x + y
""",
        ),
    ],
)
def test_assert_remover(src, expected):
    module = libcst.parse_module(src)
    modifier = AssertRemover(likelihood=1.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    assert modified.code.strip() == expected.strip()


@pytest.mark.parametrize(
    "src,expected",
    [
        # Replace raise with pass
        (
            """
def foo(x):
    if x < 0:
        raise ValueError("negative")
    return x
""",
            """def foo(x):
    if x < 0:
        pass
    return x
""",
        ),
        # Raise without argument
        (
            """
def bar():
    try:
        do_something()
    except Exception:
        raise
""",
            """def bar():
    try:
        do_something()
    except Exception:
        pass
""",
        ),
    ],
)
def test_raise_remover(src, expected):
    module = libcst.parse_module(src)
    modifier = RaiseRemover(likelihood=1.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    assert modified.code.strip() == expected.strip()


def test_try_except_no_modification_when_likelihood_zero():
    """Test that no changes occur when likelihood is 0."""
    src = """
def foo():
    try:
        x = 1
    except Exception:
        x = 0
    return x
"""
    module = libcst.parse_module(src)
    modifier = TryExceptRemover(likelihood=0.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    assert modified.code == module.code


def test_assert_no_modification_when_likelihood_zero():
    """Test that no changes occur when likelihood is 0."""
    src = """
def foo(x):
    assert x > 0
    return x
"""
    module = libcst.parse_module(src)
    modifier = AssertRemover(likelihood=0.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    assert modified.code == module.code


def test_raise_no_modification_when_likelihood_zero():
    """Test that no changes occur when likelihood is 0."""
    src = """
def foo(x):
    if x < 0:
        raise ValueError()
    return x
"""
    module = libcst.parse_module(src)
    modifier = RaiseRemover(likelihood=0.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    assert modified.code == module.code
