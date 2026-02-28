import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.wrappers import (
    RemoveTryCatchModifier,
    RemoveNullCheckModifier,
)


@pytest.mark.parametrize(
    "src",
    [
        """public void foo() {
    try {
        doSomething();
    } catch (Exception e) {
        handleError(e);
    }
}""",
        """public int bar() {
    try {
        return Integer.parseInt("42");
    } catch (NumberFormatException e) {
        return 0;
    }
}""",
        """public void baz() {
    try (java.io.InputStream in = getStream()) {
        in.read();
    } catch (Exception e) {
        handle(e);
    }
}""",
    ],
)
def test_remove_try_catch_modifier(tmp_path, src):
    """Test that RemoveTryCatchModifier removes try-catch blocks."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveTryCatchModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.count("try") < src.count("try"), (
        "Expected try block to be removed"
    )
    assert result.rewrite.count("catch") < src.count("catch"), (
        "Expected catch block to be removed"
    )


def test_remove_try_catch_no_try(tmp_path):
    """Test that modifier returns None when there's no try-catch."""
    src = """public int foo(int x) {
    return x + 1;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveTryCatchModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


@pytest.mark.parametrize(
    "src",
    [
        """public void foo(String s) {
    if (s != null) {
        System.out.println(s.length());
    }
}""",
        """public int bar(Integer x) {
    if (x == null) {
        return 0;
    }
    return x;
}""",
    ],
)
def test_remove_null_check_modifier(tmp_path, src):
    """Test that RemoveNullCheckModifier removes null checks."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveNullCheckModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.count("null") < src.count("null"), (
        "Expected null check to be removed"
    )


def test_remove_null_check_no_null(tmp_path):
    """Test that modifier returns None when there's no null check."""
    src = """public int foo(int x) {
    if (x > 0) {
        return x;
    }
    return 0;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveNullCheckModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


@pytest.mark.parametrize(
    "src,expected_condition",
    [
        (
            """public void foo(String s) {
    if (s == null || s.isEmpty()) {
        return;
    }
}""",
            "if (s.isEmpty())",
        ),
        (
            """public void foo(String s) {
    if (s != null && s.length() > 0) {
        System.out.println(s);
    }
}""",
            "if (s.length() > 0)",
        ),
        (
            """public void foo(String s) {
    if (s.length() > 0 && s != null) {
        System.out.println(s);
    }
}""",
            "if (s.length() > 0)",
        ),
    ],
)
def test_remove_null_check_simplifies_compound_conditions(
    tmp_path, src, expected_condition
):
    """Test that compound null-check conditions are simplified."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveNullCheckModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert expected_condition in result.rewrite
