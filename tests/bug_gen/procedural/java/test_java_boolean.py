import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.boolean import (
    BooleanNegateModifier,
)


@pytest.mark.parametrize(
    "src,expected_changes",
    [
        (
            """public boolean foo() {
    return true;
}""",
            ["false"],
        ),
        (
            """public boolean bar(boolean x) {
    return !x;
}""",
            ["return x;"],
        ),
        (
            """public void baz(boolean flag) {
    if (flag) {
        doSomething();
    }
}""",
            ["!flag"],
        ),
        (
            """public boolean literalFalse() {
    return false;
}""",
            ["return true;"],
        ),
        (
            """public void whileLoop() {
    while (false) {
        doSomething();
    }
}""",
            ["while (true)"],
        ),
        (
            """public void doLoop(boolean ready) {
    do {
        doSomething();
    } while (ready);
}""",
            ["!ready"],
        ),
        (
            """public void forLoop(boolean flag) {
    for (; flag; ) {
        doSomething();
    }
}""",
            ["!flag"],
        ),
        (
            """public void methodInvocation() {
    if (isReady()) {
        doSomething();
    }
}""",
            ["!isReady()"],
        ),
    ],
)
def test_boolean_negate_modifier(tmp_path, src, expected_changes):
    """Test that BooleanNegateModifier negates boolean expressions."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = BooleanNegateModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(change in result.rewrite for change in expected_changes), (
        f"Expected one of {expected_changes} in:\n{result.rewrite}"
    )


def test_boolean_negate_no_boolean(tmp_path):
    """Test that modifier returns None when there's no boolean to negate."""
    src = """public int foo(int x) {
    return x + 1;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = BooleanNegateModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None
