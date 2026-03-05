from swesmith.bug_gen.adapters.ruby import get_entities_from_file_rb
from swesmith.bug_gen.procedural.ruby.base import RubyProceduralModifier
from swesmith.bug_gen.procedural.ruby.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)


def test_operation_change(tmp_path):
    src = """\
def calc(a, b)
  x = a + b
  y = x * 2
  z = y - a
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # All three operators changed within their category
    assert "a * b" in modified.rewrite
    assert "x - 2" in modified.rewrite
    assert "y ** a" in modified.rewrite


def test_operation_flip_operator(tmp_path):
    src = """\
def check(x, y)
  a = x == y
  b = x > 0
  c = a && b
  c
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Operators flipped to opposites
    assert "x != y" in modified.rewrite
    assert "x < 0" in modified.rewrite
    assert "a || b" in modified.rewrite


def test_operation_swap_operands(tmp_path):
    src = """\
def compare(a, b)
  x = a > b
  y = a + b
  z = x && y
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationSwapOperandsModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Operands swapped: left and right sides exchanged
    assert "b > a" in modified.rewrite
    assert "b + a" in modified.rewrite
    assert "y && x" in modified.rewrite


def test_operation_break_chains(tmp_path):
    src = """\
def calc(a, b, c)
  x = a + b + c
  y = x * a - b
  z = y + b
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationBreakChainsModifier(likelihood=1.0, seed=0)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Chains collapsed: "a + b + c" -> "a", "x * a - b" -> "x"
    assert "x = a\n" in modified.rewrite
    assert "y = x\n" in modified.rewrite


def test_operation_change_constants(tmp_path):
    src = """\
def offset(x)
  y = x + 1
  z = y * 2
  w = z - 3
  w
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Off-by-one changes: 1->2, 2->1, 3->2
    assert "x + 2" in modified.rewrite
    assert "y * 1" in modified.rewrite
    assert "z - 2" in modified.rewrite


def test_operation_no_binary_ops(tmp_path):
    src = """\
def simple
  puts "hello"
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeModifier(likelihood=1.0, seed=42)
    assert not pm.can_change(entities[0])


def test_operation_change_flip_failure(tmp_path):
    """OperationChangeModifier returns None when likelihood=0.0 (flip fails)."""
    src = """\
def calc(a, b)
  x = a + b
  y = x * 2
  z = y - a
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = OperationChangeModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_operation_flip_operator_flip_failure(tmp_path):
    """OperationFlipOperatorModifier returns None when likelihood=0.0."""
    src = """\
def check(x, y)
  a = x == y
  b = x > 0
  c = a && b
  c
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = OperationFlipOperatorModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_operation_swap_operands_flip_failure(tmp_path):
    """OperationSwapOperandsModifier returns None when likelihood=0.0."""
    src = """\
def compare(a, b)
  x = a > b
  y = a + b
  z = x && y
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = OperationSwapOperandsModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_operation_break_chains_flip_failure(tmp_path):
    """OperationBreakChainsModifier returns None when likelihood=0.0."""
    src = """\
def calc(a, b, c)
  x = a + b + c
  y = x * a - b
  z = y + b
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = OperationBreakChainsModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_operation_change_constants_flip_failure(tmp_path):
    """OperationChangeConstantsModifier returns None when likelihood=0.0."""
    src = """\
def offset(x)
  y = x + 1
  z = y * 2
  w = z - 3
  w
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = OperationChangeConstantsModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_operation_change_bitwise(tmp_path):
    """OperationChangeModifier exercises the BITWISE_OPS branch."""
    src = """\
def bitops(a, b)
  x = a & b
  y = x | 3
  z = y ^ a
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeModifier(likelihood=1.0, seed=42)
    modified = pm.modify(entities[0])
    assert modified is not None
    # Original bitwise operators should be changed to alternatives
    assert modified.rewrite != src


def test_operation_change_comparison(tmp_path):
    """OperationChangeModifier exercises the COMPARISON_OPS branch."""
    src = """\
def compare(a, b)
  x = a == b
  y = a < b
  z = x != y
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeModifier(likelihood=1.0, seed=42)
    modified = pm.modify(entities[0])
    assert modified is not None
    assert modified.rewrite != src


def test_operation_change_logical(tmp_path):
    """OperationChangeModifier exercises the LOGICAL_OPS branch."""
    src = """\
def check(a, b)
  x = a && b
  y = x || a
  z = y && b
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeModifier(likelihood=1.0, seed=42)
    modified = pm.modify(entities[0])
    assert modified is not None
    assert modified.rewrite != src


def test_operation_change_keyword_logical(tmp_path):
    """OperationChangeModifier exercises the KEYWORD_LOGICAL_OPS branch."""
    src = """\
def check(a, b)
  x = a and b
  y = x or a
  z = y and b
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeModifier(likelihood=1.0, seed=42)
    modified = pm.modify(entities[0])
    assert modified is not None
    assert modified.rewrite != src


def test_operation_flip_no_flippable_ops(tmp_path):
    """OperationFlipOperatorModifier returns None when only bitwise ops present."""
    src = """\
def bitops(a, b)
  x = a & b
  y = x | 3
  z = y ^ a
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    # Bitwise ops aren't in FLIPPED_OPERATORS, so no modifications possible
    result = pm.modify(entities[0])
    assert result is None


def test_operation_change_constants_float(tmp_path):
    """OperationChangeConstantsModifier exercises the float branch."""
    src = """\
def calc(x)
  y = x + 1.5
  z = y * 2.0
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    modified = pm.modify(entities[0])
    assert modified is not None
    # Float constants should be perturbed
    assert "1.5" not in modified.rewrite or "2.0" not in modified.rewrite


def test_operation_break_chains_no_chains(tmp_path):
    """OperationBreakChainsModifier returns None when no chained expressions."""
    src = """\
def simple(a, b)
  x = a + b
  y = x * a
  y
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationBreakChainsModifier(likelihood=1.0, seed=0)
    # Simple binary ops (not nested) can't be broken
    result = pm.modify(entities[0])
    assert result is None


def test_operation_break_chains_right_nested(tmp_path):
    """OperationBreakChainsModifier exercises the right-nested branch via precedence."""
    # a + b * c parses as a + (b * c) — right child is binary
    src = """\
def calc(a, b, c)
  x = a + b * c
  y = x - 1
  y
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OperationBreakChainsModifier(likelihood=1.0, seed=0)
    modified = pm.modify(entities[0])
    assert modified is not None
    # Right-nested chain collapsed: a + (b * c) -> c (innermost right operand)
    assert modified.rewrite != src


def test_validate_syntax_unchanged():
    """validate_syntax returns None when original and modified are identical."""
    code = "def foo\n  42\nend\n"
    result = RubyProceduralModifier.validate_syntax(code, code)
    assert result is None


def test_validate_syntax_invalid():
    """validate_syntax returns False for code with syntax errors."""
    valid = "def foo\n  42\nend\n"
    invalid = "def foo(\nend"
    result = RubyProceduralModifier.validate_syntax(valid, invalid)
    assert result is False
