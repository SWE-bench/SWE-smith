import pytest
from swesmith.bug_gen.adapters.rust import get_entities_from_file_rs
from swesmith.bug_gen.procedural.rust.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(x: i32) -> i32 {
    if x > 0 {
        return 1;
    } else {
        return -1;
    }
}""",
            """fn foo(x: i32) -> i32 {
    if x > 0 {
        return -1;
    } else {
        return 1;
    }
}""",
        ),
        (
            """fn bar(condition: bool) -> &str {
    if condition {
        "true"
    } else {
        "false"
    }
}""",
            """fn bar(condition: bool) -> &str {
    if condition {
        "false"
    } else {
        "true"
    }
}""",
        ),
        (
            """fn baz(x: i32) -> i32 {
    if x == 0 {
        let y = 1;
        y + 2
    } else {
        let z = 3;
        z + 4
    }
}""",
            """fn baz(x: i32) -> i32 {
    if x == 0 {
        let z = 3;
        z + 4
    } else {
        let y = 1;
        y + 2
    }
}""",
        ),
    ],
)
def test_control_if_else_invert_modifier(tmp_path, src, expected):
    """Test that ControlIfElseInvertModifier inverts if-else branches."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo() {
    let a = 1;
    let b = 2;
}""",
            [
                "fn foo() {\n    let a = 1;\n    let b = 2;\n}",
                "fn foo() {\n    let b = 2;\n    let a = 1;\n}",
            ],
        ),
        (
            """fn bar() {
    let x = 1;
    let y = 2;
    let z = 3;
}""",
            [
                "fn bar() {\n    let x = 1;\n    let y = 2;\n    let z = 3;\n}",
                "fn bar() {\n    let x = 1;\n    let z = 3;\n    let y = 2;\n}",
                "fn bar() {\n    let y = 2;\n    let x = 1;\n    let z = 3;\n}",
                "fn bar() {\n    let y = 2;\n    let z = 3;\n    let x = 1;\n}",
                "fn bar() {\n    let z = 3;\n    let x = 1;\n    let y = 2;\n}",
                "fn bar() {\n    let z = 3;\n    let y = 2;\n    let x = 1;\n}",
            ],
        ),
    ],
)
def test_control_shuffle_lines_modifier(tmp_path, src, expected_variants):
    """Test that ControlShuffleLinesModifier shuffles independent lines."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlShuffleLinesModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(
        result.rewrite.strip() == variant.strip() for variant in expected_variants
    ), f"Expected one of {expected_variants}, got {result.rewrite}"
