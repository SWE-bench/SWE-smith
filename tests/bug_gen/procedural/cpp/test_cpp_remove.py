import pytest
from swesmith.bug_gen.adapters.cpp import get_entities_from_file_cpp
from swesmith.bug_gen.procedural.cpp.remove import (
    RemoveLoopModifier,
    RemoveConditionalModifier,
    RemoveAssignModifier,
)


@pytest.mark.parametrize(
    "src",
    [
        """void foo() {
    for (int i = 0; i < 10; i++) {
        doSomething();
    }
}""",
        """void bar() {
    while (condition) {
        process();
    }
}""",
        """void baz() {
    do {
        work();
    } while (running);
}""",
        """void qux() {
    for (auto x : container) {
        process(x);
    }
}""",
    ],
)
def test_remove_loop_modifier(tmp_path, src):
    """Test that RemoveLoopModifier removes or extracts loop structures."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveLoopModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"
    # The loop structure should be removed (loop body extracted)
    # Check for actual loop syntax patterns, not just keywords (e.g., "do" appears in "doSomething")
    import re

    has_for_loop = re.search(r"\bfor\s*\(", result.rewrite) is not None
    has_while_loop = re.search(r"\bwhile\s*\(", result.rewrite) is not None
    has_do_loop = re.search(r"\bdo\s*\{", result.rewrite) is not None
    assert not (has_for_loop or has_while_loop or has_do_loop), (
        f"Expected loop structures to be removed: {result.rewrite}"
    )


def test_remove_loop_modifier_extracts_body(tmp_path):
    """Test that RemoveLoopModifier extracts loop body."""
    src = """void foo() {
    for (int i = 0; i < 10; i++) {
        int x = 5;
    }
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveLoopModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    # The body content should be extracted
    assert "int x = 5" in result.rewrite, (
        f"Expected loop body to be extracted: {result.rewrite}"
    )


def test_remove_loop_modifier_no_loops(tmp_path):
    """Test that RemoveLoopModifier returns None when no loops are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveLoopModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when no loops are present"


@pytest.mark.parametrize(
    "src",
    [
        """void foo(int x) {
    if (x > 0) {
        handlePositive();
    }
}""",
        """void bar(bool flag) {
    if (flag) {
        process();
    } else {
        skip();
    }
}""",
    ],
)
def test_remove_conditional_modifier(tmp_path, src):
    """Test that RemoveConditionalModifier removes or extracts conditional structures."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"


def test_remove_conditional_modifier_extracts_body(tmp_path):
    """Test that RemoveConditionalModifier extracts if body."""
    src = """void foo(int x) {
    if (x > 0) {
        doWork();
    }
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    # The body content should be extracted (if structure removed)
    assert "doWork()" in result.rewrite, (
        f"Expected if body to be extracted: {result.rewrite}"
    )


def test_remove_conditional_modifier_no_conditionals(tmp_path):
    """Test that RemoveConditionalModifier returns None when no conditionals are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when no conditionals are present"


@pytest.mark.parametrize(
    "src",
    [
        """void foo() {
    int x = 5;
}""",
        """void bar() {
    x = 10;
}""",
        """void baz() {
    int a = 1;
    int b = 2;
}""",
    ],
)
def test_remove_assign_modifier(tmp_path, src):
    """Test that RemoveAssignModifier removes assignment statements."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"


def test_remove_assign_modifier_removes_statement(tmp_path):
    """Test that RemoveAssignModifier removes entire assignment statement."""
    src = """void foo() {
    int x = 5;
    int y = 10;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    # One of the assignments should be removed
    lines_with_assignment = [line for line in result.rewrite.split("\n") if "=" in line]
    original_lines_with_assignment = [line for line in src.split("\n") if "=" in line]
    assert len(lines_with_assignment) < len(original_lines_with_assignment), (
        f"Expected fewer assignments: {result.rewrite}"
    )


def test_remove_assign_modifier_no_assignments(tmp_path):
    """Test that RemoveAssignModifier returns None when no assignments are present."""
    src = """void foo() {
    doSomething();
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when no assignments are present"
