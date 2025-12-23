import pytest
from swesmith.bug_gen.adapters.rust import get_entities_from_file_rs
from swesmith.bug_gen.procedural.rust.operations import (
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    FLIPPED_OPERATORS,
)


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo(a: i32, b: i32) -> i32 {
    a + b
}""",
            [
                "fn foo(a: i32, b: i32) -> i32 {\n    a - b\n}",
                "fn foo(a: i32, b: i32) -> i32 {\n    a * b\n}",
                "fn foo(a: i32, b: i32) -> i32 {\n    a / b\n}",
                "fn foo(a: i32, b: i32) -> i32 {\n    a % b\n}",
            ],
        ),
        (
            """fn bar(x: i32, y: i32) -> bool {
    x == y
}""",
            [
                "fn bar(x: i32, y: i32) -> bool {\n    x != y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x < y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x <= y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x > y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x >= y\n}",
            ],
        ),
        (
            """fn baz(a: u32, b: u32) -> u32 {
    a & b
}""",
            [
                "fn baz(a: u32, b: u32) -> u32 {\n    a | b\n}",
                "fn baz(a: u32, b: u32) -> u32 {\n    a ^ b\n}",
            ],
        ),
    ],
)
def test_operation_change_modifier(tmp_path, src, expected_variants):
    """Test that OperationChangeModifier changes operators within the same category."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)

    found_variant = False
    for _ in range(20):
        result = modifier.modify(entities[0])
        if (
            result
            and result.rewrite != src
            and any(
                result.rewrite.strip() == variant.strip()
                for variant in expected_variants
            )
        ):
            found_variant = True
            break

    assert found_variant, (
        f"Expected one of {expected_variants}, but got {result.rewrite if result else 'None'}"
    )


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(a: i32, b: i32) -> i32 {
    a + b
}""",
            """fn foo(a: i32, b: i32) -> i32 {
    a - b
}""",
        ),
        (
            """fn bar(x: i32, y: i32) -> bool {
    x == y
}""",
            """fn bar(x: i32, y: i32) -> bool {
    x != y
}""",
        ),
        (
            """fn baz(a: i32, b: i32) -> bool {
    a < b
}""",
            """fn baz(a: i32, b: i32) -> bool {
    a > b
}""",
        ),
        (
            """fn qux(x: bool, y: bool) -> bool {
    x && y
}""",
            """fn qux(x: bool, y: bool) -> bool {
    x || y
}""",
        ),
    ],
)
def test_operation_flip_operator_modifier(tmp_path, src, expected):
    """Test that OperationFlipOperatorModifier flips operators to their opposites."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(a: i32, b: i32) -> i32 {
    a + b
}""",
            """fn foo(a: i32, b: i32) -> i32 {
    b + a
}""",
        ),
        (
            """fn bar(x: i32, y: i32) -> bool {
    x < y
}""",
            """fn bar(x: i32, y: i32) -> bool {
    y < x
}""",
        ),
        (
            """fn baz(a: i32, b: i32) -> i32 {
    a - b
}""",
            """fn baz(a: i32, b: i32) -> i32 {
    b - a
}""",
        ),
    ],
)
def test_operation_swap_operands_modifier(tmp_path, src, expected):
    """Test that OperationSwapOperandsModifier swaps operands in binary expressions."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationSwapOperandsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo(a: i32, b: i32, c: i32) -> i32 {
    a + b + c
}""",
            [
                "fn foo(a: i32, b: i32, c: i32) -> i32 {\n    a\n}",
                "fn foo(a: i32, b: i32, c: i32) -> i32 {\n    c\n}",
            ],
        ),
    ],
)
def test_operation_break_chains_modifier(tmp_path, src, expected_variants):
    """Test that OperationBreakChainsModifier breaks operation chains."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(
        result.rewrite.strip() == variant.strip() for variant in expected_variants
    ), f"Expected one of {expected_variants}, got {result.rewrite}"


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo() -> i32 {
    2 + x
}""",
            [
                "fn foo() -> i32 {\n    1 + x\n}",
                "fn foo() -> i32 {\n    3 + x\n}",
            ],
        ),
        (
            """fn bar() -> i32 {
    y - 5
}""",
            [
                "fn bar() -> i32 {\n    y - 4\n}",
                "fn bar() -> i32 {\n    y - 6\n}",
            ],
        ),
        (
            """fn baz() -> i32 {
    10 * 20
}""",
            [
                "fn baz() -> i32 {\n    9 * 20\n}",
                "fn baz() -> i32 {\n    11 * 20\n}",
                "fn baz() -> i32 {\n    10 * 19\n}",
                "fn baz() -> i32 {\n    10 * 21\n}",
                "fn baz() -> i32 {\n    9 * 19\n}",
                "fn baz() -> i32 {\n    9 * 21\n}",
                "fn baz() -> i32 {\n    11 * 19\n}",
                "fn baz() -> i32 {\n    11 * 21\n}",
            ],
        ),
    ],
)
def test_operation_change_constants_modifier(tmp_path, src, expected_variants):
    """Test that OperationChangeConstantsModifier changes integer constants."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(
        result.rewrite.strip() == variant.strip() for variant in expected_variants
    ), f"Expected one of {expected_variants}, got {result.rewrite}"


def test_operation_flip_operator_mappings():
    """Test that OperationFlipOperatorModifier uses correct operator mappings."""
    assert FLIPPED_OPERATORS["+"] == "-"
    assert FLIPPED_OPERATORS["-"] == "+"
    assert FLIPPED_OPERATORS["*"] == "/"
    assert FLIPPED_OPERATORS["/"] == "*"
    assert FLIPPED_OPERATORS["=="] == "!="
    assert FLIPPED_OPERATORS["!="] == "=="
    assert FLIPPED_OPERATORS["<"] == ">"
    assert FLIPPED_OPERATORS[">"] == "<"
    assert FLIPPED_OPERATORS["<="] == ">="
    assert FLIPPED_OPERATORS[">="] == "<="
    assert FLIPPED_OPERATORS["&&"] == "||"
    assert FLIPPED_OPERATORS["||"] == "&&"
    assert FLIPPED_OPERATORS["&"] == "|"
    assert FLIPPED_OPERATORS["|"] == "&"
    assert FLIPPED_OPERATORS["<<"] == ">>"
    assert FLIPPED_OPERATORS[">>"] == "<<"
