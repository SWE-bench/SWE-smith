from swesmith.bug_gen.adapters.ruby import get_entities_from_file_rb
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
    assert "y % a" in modified.rewrite


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
