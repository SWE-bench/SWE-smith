import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.literals import StringLiteralModifier


@pytest.mark.parametrize(
    "src,expected_changes",
    [
        (
            """public String foo() {
    return "true";
}""",
            ['return "false";'],
        ),
        (
            """public String bar() {
    return "";
}""",
            ['return " ";'],
        ),
    ],
)
def test_string_literal_modifier_swap_pairs(tmp_path, src, expected_changes):
    """Test that StringLiteralModifier swaps known literal pairs."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = StringLiteralModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(change in result.rewrite for change in expected_changes), (
        f"Expected one of {expected_changes} in:\n{result.rewrite}"
    )


def test_string_literal_modifier_fallback_mutation(tmp_path):
    """Test fallback mutation when no swap pair matches."""
    src = """public String foo() {
    return "alpha";
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = StringLiteralModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert 'return "alph";' in result.rewrite


def test_string_literal_modifier_fallback_single_character(tmp_path):
    """Test fallback mutation for single-character literals."""
    src = """public String foo() {
    return "x";
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = StringLiteralModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert 'return "xx";' in result.rewrite


def test_string_literal_modifier_text_block_returns_none(tmp_path):
    """Test that Java text blocks are ignored."""
    src = """public String foo() {
    return \"\"\"
line one
line two
\"\"\";
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = StringLiteralModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


def test_string_literal_modifier_no_strings(tmp_path):
    """Test that modifier returns None when no string literals are present."""
    src = """public int foo(int x) {
    return x + 1;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = StringLiteralModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None
