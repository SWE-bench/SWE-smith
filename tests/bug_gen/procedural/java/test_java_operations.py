import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.operations import (
    OperationBreakChainsModifier,
    OperationChangeModifier,
    OperationChangeConstantsModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)


@pytest.mark.parametrize(
    "src,possible_results",
    [
        (
            """public int add() {
    return 1 + 2;
}""",
            [
                "return 1 - 2;",
                "return 1 * 2;",
                "return 1 / 2;",
                "return 1 % 2;",
            ],
        ),
        (
            """public boolean compare(int x, int y) {
    return x < y;
}""",
            [
                "return x > y;",
                "return x <= y;",
                "return x >= y;",
                "return x == y;",
                "return x != y;",
            ],
        ),
    ],
)
def test_operation_change_modifier(tmp_path, src, possible_results):
    """Test that OperationChangeModifier changes operations."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(expected in result.rewrite for expected in possible_results), (
        f"Expected one of {possible_results} in {result.rewrite}"
    )


def test_operation_change_modifier_bitwise_operator(tmp_path):
    """Test that OperationChangeModifier can change bitwise operators."""
    src = """public int mask(int a, int b) {
    return a ^ b;
}"""
    possible_results = [
        "return a & b;",
        "return a | b;",
        "return a << b;",
        "return a >> b;",
        "return a >>> b;",
    ]
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(expected in result.rewrite for expected in possible_results), (
        f"Expected one of {possible_results} in {result.rewrite}"
    )


def test_operation_change_modifier_no_string_literal_concat(tmp_path):
    """Test that string-literal concatenation expressions are not selected."""
    src = """public String foo(String a) {
    String s = a + "suffix";
    int n = 1 + 2;
    return s + n;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert 'String s = a + "suffix";' in result.rewrite


@pytest.mark.parametrize(
    "src,expected_mapping",
    [
        (
            """public boolean foo(int x) {
    return x < 10;
}""",
            {"<": ">="},
        ),
        (
            """public boolean bar(int x) {
    return x == 0;
}""",
            {"==": "!="},
        ),
        (
            """public boolean baz(boolean a, boolean b) {
    return a && b;
}""",
            {"&&": "||"},
        ),
    ],
)
def test_operation_flip_operator_modifier(tmp_path, src, expected_mapping):
    """Test that OperationFlipOperatorModifier flips operators correctly."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    for original, flipped in expected_mapping.items():
        if original in src:
            assert flipped in result.rewrite, (
                f"Expected {flipped} in result after flipping {original}"
            )


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """public int foo(int a, int b) {
    return a + b;
}""",
            "return b + a;",
        ),
        (
            """public boolean bar(int x, int y) {
    return x < y;
}""",
            "return y < x;",
        ),
    ],
)
def test_operation_swap_operands_modifier(tmp_path, src, expected):
    """Test that OperationSwapOperandsModifier swaps operands."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationSwapOperandsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert expected in result.rewrite, f"Expected swapped expression {expected}"


@pytest.mark.parametrize(
    "src",
    [
        """public int foo() {
    return 42;
}""",
        """public double bar() {
    return 3.14;
}""",
        """public int baz(int x) {
    return x + 10;
}""",
    ],
)
def test_operation_change_constants_modifier(tmp_path, src):
    """Test that OperationChangeConstantsModifier changes numeric constants."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected constant to be changed"


def test_operation_change_constants_modifier_handles_long_suffix(tmp_path):
    """Test that long literal suffixes remain valid after mutation."""
    src = """public long foo() {
    return 1234L;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "1234L" not in result.rewrite
    assert "L;" in result.rewrite


def test_operation_change_constants_modifier_handles_hex_float(tmp_path):
    """Test that hex floating-point literals are mutated without parse failures."""
    src = """public double foo() {
    return 0x1.0p3;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "0x1.0p3" not in result.rewrite


def test_operation_break_chains_modifier(tmp_path):
    """Test that OperationBreakChainsModifier breaks chained method calls."""
    src = """public String foo(String s) {
    return s.trim().toLowerCase();
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "s.trim().toLowerCase()" not in result.rewrite
    assert "s.trim()" in result.rewrite


def test_operation_break_chains_modifier_no_chain(tmp_path):
    """Test that OperationBreakChainsModifier returns None when no chains exist."""
    src = """public int foo() {
    return 42;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None
