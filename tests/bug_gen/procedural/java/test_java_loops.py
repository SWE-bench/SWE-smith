import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.loops import (
    LoopBreakContinueSwapModifier,
    LoopOffByOneModifier,
)


@pytest.mark.parametrize(
    "src,expected_swap",
    [
        (
            """public void foo() {
    for (int i = 0; i < 10; i++) {
        if (i == 5) {
            break;
        }
    }
}""",
            ("break", "continue"),
        ),
        (
            """public void bar() {
    for (int i = 0; i < 10; i++) {
        if (i % 2 == 0) {
            continue;
        }
        System.out.println(i);
    }
}""",
            ("continue", "break"),
        ),
    ],
)
def test_loop_break_continue_swap_modifier(tmp_path, src, expected_swap):
    """Test that LoopBreakContinueSwapModifier swaps break and continue."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = LoopBreakContinueSwapModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    original, swapped = expected_swap
    assert swapped in result.rewrite, f"Expected {original} to be swapped to {swapped}"


def test_loop_break_continue_swap_no_break_continue(tmp_path):
    """Test that modifier returns None when there's no break/continue."""
    src = """public void foo() {
    for (int i = 0; i < 10; i++) {
        System.out.println(i);
    }
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = LoopBreakContinueSwapModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


def test_loop_break_continue_swap_ignores_switch_break(tmp_path):
    """Test that switch-only break statements are not swapped."""
    src = """public int foo(int x) {
    switch (x) {
        case 0:
            break;
        default:
            return x;
    }
    return 0;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = LoopBreakContinueSwapModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


@pytest.mark.parametrize(
    "src,original_op,expected_ops",
    [
        (
            """public void foo() {
    for (int i = 0; i < 10; i++) {
        System.out.println(i);
    }
}""",
            "<",
            ["<="],
        ),
        (
            """public void bar() {
    for (int i = 10; i >= 0; i--) {
        System.out.println(i);
    }
}""",
            ">=",
            [">"],
        ),
        (
            """public void baz(int[] arr) {
    for (int i = 0; i <= arr.length - 1; i++) {
        System.out.println(arr[i]);
    }
}""",
            "<=",
            ["<"],
        ),
        (
            """public void whileLoop() {
    int i = 0;
    while (i < 10) {
        i++;
    }
}""",
            "<",
            ["<="],
        ),
        (
            """public void doLoop() {
    int i = 0;
    do {
        i++;
    } while (i < 10);
}""",
            "<",
            ["<="],
        ),
    ],
)
def test_loop_off_by_one_modifier(tmp_path, src, original_op, expected_ops):
    """Test that LoopOffByOneModifier introduces off-by-one errors."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = LoopOffByOneModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(op in result.rewrite for op in expected_ops), (
        f"Expected one of {expected_ops} in result"
    )


def test_loop_off_by_one_no_loop(tmp_path):
    """Test that modifier returns None when there's no loop."""
    src = """public int foo(int x) {
    return x + 1;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = LoopOffByOneModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None
