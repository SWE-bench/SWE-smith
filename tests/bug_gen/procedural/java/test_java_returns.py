from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.returns import ReturnNullModifier


def test_return_null_modifier_reference_return_type(tmp_path):
    """Test that reference-typed returns can be rewritten to null."""
    src = """public String foo(String s) {
    return s.trim();
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReturnNullModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "return null;" in result.rewrite
    assert "return s.trim();" not in result.rewrite


def test_return_null_modifier_primitive_return_type_is_skipped(tmp_path):
    """Test that primitive-typed methods are skipped."""
    src = """public int foo() {
    return 1;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReturnNullModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


def test_return_null_modifier_void_return_is_skipped(tmp_path):
    """Test that void returns are not candidates."""
    src = """public void foo() {
    return;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReturnNullModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None


def test_return_null_modifier_already_null_is_skipped(tmp_path):
    """Test that an existing null return is not rewritten."""
    src = """public String foo() {
    return null;
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReturnNullModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None
