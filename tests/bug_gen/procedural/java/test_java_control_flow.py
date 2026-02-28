import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.control_flow import (
    ControlIfElseInvertModifier,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """public int foo(int x) {
    if (x > 0) {
        return 1;
    } else {
        return -1;
    }
}""",
            """public int foo(int x) {
    if (x > 0) {
        return -1;
    } else {
        return 1;
    }
}""",
        ),
        (
            """public String bar(boolean condition) {
    if (condition) {
        return "true";
    } else {
        return "false";
    }
}""",
            """public String bar(boolean condition) {
    if (condition) {
        return "false";
    } else {
        return "true";
    }
}""",
        ),
        (
            """public int baz(int x) {
    if (x == 0) {
        int y = 1;
        return y + 2;
    } else {
        int z = 3;
        return z + 4;
    }
}""",
            """public int baz(int x) {
    if (x == 0) {
        int z = 3;
        return z + 4;
    } else {
        int y = 1;
        return y + 2;
    }
}""",
        ),
    ],
)
def test_control_if_else_invert_modifier(tmp_path, src, expected):
    """Test that ControlIfElseInvertModifier inverts if-else branches."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected:\n{expected}\n\nGot:\n{result.rewrite}"
    )


def test_control_if_else_invert_no_else(tmp_path):
    """Test that modifier returns None when there's no else branch."""
    src = """public int foo(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


def test_control_if_else_invert_terminal_else_if_branch(tmp_path):
    """Test that terminal else-if branches are eligible for inversion."""
    src = """public int foo(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    } else {
        return 0;
    }
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    # Outer if remains intact while the terminal else-if branch gets inverted.
    assert "if (x > 0)" in result.rewrite
    assert "else if (x < 0)" in result.rewrite
    else_if_start = result.rewrite.index("else if (x < 0)")
    assert result.rewrite.index("return 1;") < else_if_start
    assert result.rewrite.index("return 0;", else_if_start) < result.rewrite.index(
        "return -1;", else_if_start
    )


def test_control_if_else_invert_without_braces(tmp_path):
    """Test that modifier handles if/else statements without braces."""
    src = """public int foo(int x) {
    if (x > 0)
        return 1;
    else
        return -1;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "if (x > 0) return -1; else return 1;" in result.rewrite
