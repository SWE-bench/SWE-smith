import pytest
from swesmith.bug_gen.adapters.cpp import get_entities_from_file_cpp
from swesmith.bug_gen.procedural.cpp.operations import (
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
            """int foo(int a, int b) {
    return a + b;
}""",
            [
                "int foo(int a, int b) {\n    return a - b;\n}",
                "int foo(int a, int b) {\n    return a * b;\n}",
                "int foo(int a, int b) {\n    return a / b;\n}",
            ],
        ),
        (
            """bool bar(int x, int y) {
    return x == y;
}""",
            [
                "bool bar(int x, int y) {\n    return x != y;\n}",
                "bool bar(int x, int y) {\n    return x < y;\n}",
                "bool bar(int x, int y) {\n    return x <= y;\n}",
                "bool bar(int x, int y) {\n    return x > y;\n}",
                "bool bar(int x, int y) {\n    return x >= y;\n}",
            ],
        ),
        (
            """int baz(int a, int b) {
    return a * b;
}""",
            [
                "int baz(int a, int b) {\n    return a / b;\n}",
                "int baz(int a, int b) {\n    return a - b;\n}",
                "int baz(int a, int b) {\n    return a + b;\n}",
            ],
        ),
        (
            """int bit(int a, int b) {
    return a & b;
}""",
            [
                "int bit(int a, int b) {\n    return a | b;\n}",
            ],
        ),
    ],
)
def test_operation_change_modifier(tmp_path, src, expected_variants):
    """Test that OperationChangeModifier changes operators within the same category."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)

    found_variant = False
    result = None
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
            """bool bar(int x, int y) {
    return x == y;
}""",
            """bool bar(int x, int y) {
    return x != y;
}""",
        ),
        (
            """bool baz(int a, int b) {
    return a < b;
}""",
            """bool baz(int a, int b) {
    return a >= b;
}""",
        ),
        (
            """bool qux(bool x, bool y) {
    return x && y;
}""",
            """bool qux(bool x, bool y) {
    return x || y;
}""",
        ),
        (
            """bool check(int a, int b) {
    return a > b;
}""",
            """bool check(int a, int b) {
    return a <= b;
}""",
        ),
        (
            """int shift(int a) {
    return a << 1;
}""",
            """int shift(int a) {
    return a >> 1;
}""",
        ),
    ],
)
def test_operation_flip_operator_modifier(tmp_path, src, expected):
    """Test that OperationFlipOperatorModifier flips operators to their opposites."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )


def test_operation_change_modifier_bitwise_xor(tmp_path):
    """Test that OperationChangeModifier mutates XOR with another bitwise operator."""
    src = """int bit_xor(int a, int b) {
    return a ^ b;
}"""
    expected_variants = [
        "int bit_xor(int a, int b) {\n    return a & b;\n}",
        "int bit_xor(int a, int b) {\n    return a | b;\n}",
        "int bit_xor(int a, int b) {\n    return a << b;\n}",
        "int bit_xor(int a, int b) {\n    return a >> b;\n}",
    ]
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(
        result.rewrite.strip() == variant.strip() for variant in expected_variants
    ), f"Expected one of {expected_variants}, got {result.rewrite}"


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """int foo(int a, int b) {
    return a + b;
}""",
            """int foo(int a, int b) {
    return b + a;
}""",
        ),
        (
            """bool bar(int x, int y) {
    return x < y;
}""",
            """bool bar(int x, int y) {
    return y < x;
}""",
        ),
        (
            """int baz(int a, int b) {
    return a - b;
}""",
            """int baz(int a, int b) {
    return b - a;
}""",
        ),
    ],
)
def test_operation_swap_operands_modifier(tmp_path, src, expected):
    """Test that OperationSwapOperandsModifier swaps operands in binary expressions."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationSwapOperandsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )


def test_operation_break_chains_modifier(tmp_path):
    """Test that OperationBreakChainsModifier breaks function call chains."""
    src = """int foo() {
    return getValue();
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    # The modifier should remove the function call, leaving just the callee
    assert result is not None
    assert result.rewrite != src
    assert "getValue" in result.rewrite


def test_operation_break_chains_modifier_chained_calls(tmp_path):
    """Test that OperationBreakChainsModifier breaks chained method calls."""
    src = """int foo() {
    return obj.method1().method2();
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None, "Expected modifier to produce a result for chained calls"
    # The modifier removes one level of function call, so either:
    # - obj.method1().method2() -> obj.method1().method2 (removes outer call)
    # - obj.method1().method2() -> obj.method1.method2() (removes inner call)
    valid_rewrites = [
        "int foo() {\n    return obj.method1().method2;\n}",
        "int foo() {\n    return obj.method1.method2();\n}",
    ]
    assert any(result.rewrite.strip() == v.strip() for v in valid_rewrites), (
        f"Expected one of {valid_rewrites}, got {result.rewrite}"
    )


def test_operation_break_chains_modifier_no_calls(tmp_path):
    """Test that OperationBreakChainsModifier returns None when no function calls are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when no function calls are present"


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """int foo() {
    return 2 + x;
}""",
            [
                "int foo() {\n    return 1 + x;\n}",
                "int foo() {\n    return 3 + x;\n}",
                "int foo() {\n    return 0 + x;\n}",
                "int foo() {\n    return 20 + x;\n}",
                "int foo() {\n    return 200 + x;\n}",
                "int foo() {\n    return -2 + x;\n}",
                "int foo() {\n    return 102 + x;\n}",
                "int foo() {\n    return -98 + x;\n}",
                "int foo() {\n    return -1 + x;\n}",
            ],
        ),
        (
            """int bar() {
    return y - 5;
}""",
            [
                "int bar() {\n    return y - 4;\n}",
                "int bar() {\n    return y - 6;\n}",
                "int bar() {\n    return y - 0;\n}",
                "int bar() {\n    return y - 50;\n}",
                "int bar() {\n    return y - 500;\n}",
                "int bar() {\n    return y - 1;\n}",
                "int bar() {\n    return y - -1;\n}",
                "int bar() {\n    return y - 105;\n}",
                "int bar() {\n    return y - -95;\n}",
                "int bar() {\n    return y - -5;\n}",
            ],
        ),
    ],
)
def test_operation_change_constants_modifier(tmp_path, src, expected_variants):
    """Test that OperationChangeConstantsModifier changes integer constants."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(
        result.rewrite.strip() == variant.strip() for variant in expected_variants
    ), f"Expected one of {expected_variants}, got {result.rewrite}"


def test_operation_flip_operator_mappings():
    """Test that OperationFlipOperatorModifier uses correct operator mappings."""
    assert FLIPPED_OPERATORS["=="] == "!="
    assert FLIPPED_OPERATORS["!="] == "=="
    assert FLIPPED_OPERATORS["<"] == ">="
    assert FLIPPED_OPERATORS["<="] == ">"
    assert FLIPPED_OPERATORS[">"] == "<="
    assert FLIPPED_OPERATORS[">="] == "<"
    assert FLIPPED_OPERATORS["&&"] == "||"
    assert FLIPPED_OPERATORS["||"] == "&&"
    assert FLIPPED_OPERATORS["&"] == "|"
    assert FLIPPED_OPERATORS["|"] == "&"
    assert FLIPPED_OPERATORS["<<"] == ">>"
    assert FLIPPED_OPERATORS[">>"] == "<<"


def test_operation_change_modifier_no_operators(tmp_path):
    """Test that OperationChangeModifier returns None when no operators are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


def test_operation_flip_modifier_no_flippable_operators(tmp_path):
    """Test that OperationFlipOperatorModifier returns None when no flippable operators are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


def test_operation_change_constants_modifier_float(tmp_path):
    """Test that OperationChangeConstantsModifier handles floating-point constants."""
    src = """double foo() {
    return 3.14 + x;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected float constant to be modified"
    # The float constant should be transformed (the exact value depends on the random seed)
    # We just verify the code was modified - the modifier applies transformations like *10, +100, etc.
    assert "return" in result.rewrite, f"Expected return statement: {result.rewrite}"
