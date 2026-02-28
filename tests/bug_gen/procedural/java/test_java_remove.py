import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.remove import (
    RemoveConditionalModifier,
    RemoveAssignModifier,
)


@pytest.mark.parametrize(
    "src",
    [
        """public int foo(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}""",
        """public void bar(int x) {
    if (x < 0) {
        System.out.println("negative");
    }
}""",
    ],
)
def test_remove_conditional_modifier(tmp_path, src):
    """Test that RemoveConditionalModifier removes if statements."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.count("if (") < src.count("if ("), (
        "Expected at least one if statement to be removed"
    )


def test_remove_conditional_modifier_no_block_if(tmp_path):
    """Test conditional removal when the if statement body has no braces."""
    src = """public int foo(int x) {
    if (x > 0)
        return 1;
    return 0;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "if (" not in result.rewrite


def test_remove_conditional_no_if(tmp_path):
    """Test that modifier returns None when there's no if statement."""
    src = """public int foo(int x) {
    return x + 1;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


@pytest.mark.parametrize(
    "src,removed_assignment",
    [
        (
            """public void foo() {
    int x = 0;
    x = 5;
    System.out.println(x);
}""",
            "x = 5;",
        ),
        (
            """public void bar(int[] arr) {
    int i = 0;
    i = i + 1;
}""",
            "i = i + 1;",
        ),
    ],
)
def test_remove_assign_modifier(tmp_path, src, removed_assignment):
    """Test that RemoveAssignModifier removes reassignment statements."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert removed_assignment not in result.rewrite


def test_remove_assign_no_reassignment(tmp_path):
    """Test that modifier returns None when there's no reassignment."""
    src = """public int foo(int x) {
    int y = x + 1;
    return y;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    # Should return None because there's only declaration, no reassignment
    assert result is None
