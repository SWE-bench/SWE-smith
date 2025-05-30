import libcst
import pytest
from swesmith.bug_gen.procedural.remove import (
    RemoveLoopModifier,
    RemoveConditionalModifier,
    RemoveAssignModifier,
    RemoveWrapperModifier,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        # Remove for loop
        (
            """
def foo():
    for i in range(3):
        print(i)
    return 1
""",
            """def foo():
    return 1
""",
        ),
        # Remove while loop
        (
            """
def bar():
    while True:
        break
    return 2
""",
            """def bar():
    return 2
""",
        ),
    ],
)
def test_remove_loop(src, expected):
    module = libcst.parse_module(src)
    modifier = RemoveLoopModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert modified.code.strip() == expected.strip()


@pytest.mark.parametrize(
    "src,expected",
    [
        # Remove if statement
        (
            """
def foo(x):
    if x > 0:
        return x
    return 0
""",
            """def foo(x):
    return 0
""",
        ),
        # If with else, remove whole if
        (
            """
def bar(x):
    if x < 0:
        return -1
    else:
        return 1
""",
            """def bar(x):
    pass
""",
        ),
    ],
)
def test_remove_conditional(src, expected):
    module = libcst.parse_module(src)
    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert modified.code.strip() == expected.strip()


@pytest.mark.parametrize(
    "src,expected",
    [
        # Remove assignment
        (
            """
def foo():
    x = 1
    return x
""",
            """def foo():
    return x
""",
        ),
        # Remove augmented assignment
        (
            """
def bar():
    y = 2
    y += 3
    return y
""",
            """def bar():
    return y
""",
        ),
    ],
)
def test_remove_assign(src, expected):
    module = libcst.parse_module(src)
    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert modified.code.strip() == expected.strip()


@pytest.mark.parametrize(
    "src,expected",
    [
        # Remove with block
        (
            """
def foo():
    with open('f') as f:
        data = f.read()
    return 1
""",
            """def foo():
    return 1
""",
        ),
        # Remove try block
        (
            """
def bar():
    try:
        x = 1
    except Exception:
        x = 2
    return x
""",
            """def bar():
    return x
""",
        ),
    ],
)
def test_remove_wrapper(src, expected):
    module = libcst.parse_module(src)
    modifier = RemoveWrapperModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert modified.code.strip() == expected.strip()
