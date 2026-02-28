import pytest
from swesmith.bug_gen.adapters.cpp import get_entities_from_file_cpp
from swesmith.bug_gen.procedural.cpp.replace_strings import ReplaceStringTypoModifier


@pytest.mark.parametrize(
    "src",
    [
        """void foo() {
    const char* msg = "Hello World";
}""",
        """void bar() {
    std::string s = "error message";
}""",
        """void baz() {
    printf("testing output");
}""",
    ],
)
def test_replace_string_typo_modifier(tmp_path, src):
    """Test that ReplaceStringTypoModifier introduces typos in string literals."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"
    # The string literal should be modified
    assert '"' in result.rewrite, "Expected quotes to still be present"


def test_replace_string_typo_modifier_single_character_change(tmp_path):
    """Test that ReplaceStringTypoModifier changes a single character."""
    src = """void foo() {
    const char* msg = "abcdef";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert len(result.rewrite) == len(src), "Expected typo mutation to preserve length"

    changed_positions = [
        index
        for index, (original_char, rewritten_char) in enumerate(
            zip(src, result.rewrite)
        )
        if original_char != rewritten_char
    ]
    assert 1 <= len(changed_positions) <= 2, (
        "Expected one changed character (or two for adjacent swap)"
    )

    literal_body_start = src.index('"abcdef"') + 1
    literal_body_end = literal_body_start + len("abcdef")
    assert all(
        literal_body_start <= index < literal_body_end for index in changed_positions
    ), "Expected typo mutation to affect only characters inside the string literal"


def test_replace_string_typo_modifier_wide_string(tmp_path):
    """Test that ReplaceStringTypoModifier handles wide string literals."""
    src = """void foo() {
    const wchar_t* msg = L"Wide string";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"
    assert 'L"' in result.rewrite, "Expected wide string prefix to be preserved"


def test_replace_string_typo_modifier_raw_string(tmp_path):
    """Test that ReplaceStringTypoModifier handles raw string literals."""
    src = """void foo() {
    const char* msg = R"(Raw string text)";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected raw string content to be modified"
    assert 'R"(' in result.rewrite, "Expected raw string prefix to be preserved"
    assert ')"' in result.rewrite, "Expected raw string suffix to be preserved"


def test_replace_string_typo_modifier_raw_string_custom_delimiter(tmp_path):
    """Test that ReplaceStringTypoModifier preserves custom raw string delimiters."""
    src = """void foo() {
    const char* msg = R"custom(Delimited raw string)custom";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, (
        "Expected custom-delimited raw string content to be modified"
    )
    assert 'R"custom(' in result.rewrite, (
        "Expected custom raw string prefix to be preserved"
    )
    assert ')custom"' in result.rewrite, (
        "Expected custom raw string suffix to be preserved"
    )


def test_replace_string_typo_modifier_empty_string(tmp_path):
    """Test that ReplaceStringTypoModifier handles empty strings gracefully."""
    src = """void foo() {
    const char* msg = "";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    # Empty strings should return None (nothing to modify)
    assert result is None, "Expected None for empty string"


def test_replace_string_typo_modifier_no_strings(tmp_path):
    """Test that ReplaceStringTypoModifier returns None when no strings are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when no strings are present"


def test_replace_string_typo_modifier_multiple_strings(tmp_path):
    """Test that ReplaceStringTypoModifier handles functions with multiple strings."""
    src = """void foo() {
    printf("first string");
    printf("second string");
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"


def test_replace_string_typo_modifier_preserves_structure(tmp_path):
    """Test that ReplaceStringTypoModifier preserves code structure."""
    src = """void foo() {
    const char* msg = "test";
    printf(msg);
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    # Function structure should be preserved
    assert "void foo()" in result.rewrite
    assert "printf(msg);" in result.rewrite


def test_replace_string_typo_explanation(tmp_path):
    """Test that ReplaceStringTypoModifier provides correct explanation."""
    src = """void foo() {
    const char* msg = "Hello";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "typo" in result.explanation.lower(), (
        f"Expected explanation to mention typo: {result.explanation}"
    )


def test_replace_string_typo_strategy_name(tmp_path):
    """Test that ReplaceStringTypoModifier provides correct strategy name."""
    src = """void foo() {
    const char* msg = "Hello";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.strategy == "func_pm_string_typo", (
        f"Expected strategy 'func_pm_string_typo', got {result.strategy}"
    )
