import pytest

from swesmith.bug_gen.adapters.ruby import get_entities_from_file_rb
from swesmith.bug_gen.procedural.ruby.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
    GuardClauseInvertModifier,
)


def test_control_if_else_invert(tmp_path):
    src = """\
def check(x, y)
  z = x + y
  if x > 0
    if y > 0
      "both positive"
    else
      "mixed"
    end
  else
    "non-positive"
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Split on outer condition then first "else" to get then/else bodies
    parts = modified.rewrite.split("if x > 0", 1)
    then_else = parts[1].split("else", 1)
    then_body = then_else[0]
    else_body = then_else[1]
    # "non-positive" swapped into then-branch, inner if swapped into else-branch
    assert '"non-positive"' in then_body
    assert "if y > 0" in else_body


def test_control_unless_else_invert(tmp_path):
    src = """\
def check(x)
  y = x + 1
  z = y * 2
  unless x > 0
    "non-positive"
  else
    "positive"
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    parts = modified.rewrite.split("unless x > 0", 1)
    then_else = parts[1].split("else", 1)
    then_body = then_else[0]
    else_body = then_else[1]
    assert '"positive"' in then_body
    assert '"non-positive"' in else_body


def test_control_if_else_invert_no_else(tmp_path):
    src = """\
def check(x)
  y = x + 1
  z = y * 2
  if x > 0
    "positive"
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    assert not pm.can_change(entities[0])


def test_control_shuffle_lines(tmp_path):
    src = """\
def setup
  @name = "test"
  @count = 0
  @ready = true
  while @count < 10
    @count += 1
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = ControlShuffleLinesModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Statements reordered — don't check specific order (seed-dependent)
    assert modified.rewrite != src
    # All original statements still present
    assert "@name" in modified.rewrite
    assert "@count = 0" in modified.rewrite
    assert "@ready" in modified.rewrite


def test_control_shuffle_lines_singleton_method(tmp_path):
    """ControlShuffleLinesModifier also shuffles singleton (self.) methods."""
    src = """\
def self.configure
  @host = "localhost"
  @port = 8080
  @debug = false
  @timeout = 30
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = ControlShuffleLinesModifier(likelihood=1.0, seed=42)
    modified = pm.modify(entities[0])
    assert modified is not None
    assert modified.rewrite != src
    assert "@host" in modified.rewrite
    assert "@port" in modified.rewrite
    assert "@debug" in modified.rewrite
    assert "@timeout" in modified.rewrite


@pytest.mark.parametrize(
    "src,expected_keyword",
    [
        (
            """\
def process(x)
  return if x.nil?
  y = x + 1
  z = y * 2
  z
end
""",
            "return unless x.nil?",
        ),
        (
            """\
def process(x)
  raise unless x.valid?
  y = x + 1
  z = y * 2
  x.perform(z)
end
""",
            "raise if x.valid?",
        ),
    ],
)
def test_guard_clause_invert(tmp_path, src, expected_keyword):
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = GuardClauseInvertModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert expected_keyword in modified.rewrite


def test_control_if_else_invert_flip_failure(tmp_path):
    """ControlIfElseInvertModifier returns None when likelihood=0.0."""
    src = """\
def check(x, y)
  z = x + y
  if x > 0
    "positive"
  else
    "non-positive"
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = ControlIfElseInvertModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_guard_clause_invert_flip_failure(tmp_path):
    """GuardClauseInvertModifier returns None when likelihood=0.0."""
    src = """\
def process(x)
  return if x.nil?
  y = x + 1
  z = y * 2
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = GuardClauseInvertModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_guard_clause_invert_no_modifiers(tmp_path):
    """GuardClauseInvertModifier returns None when only block-form if/unless."""
    src = """\
def process(x)
  if x > 0
    y = x + 1
    z = y * 2
    z
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = GuardClauseInvertModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_control_shuffle_lines_flip_failure(tmp_path):
    """ControlShuffleLinesModifier returns None when likelihood=0.0."""
    src = """\
def setup
  @name = "test"
  @count = 0
  @ready = true
  while @count < 10
    @count += 1
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = ControlShuffleLinesModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None
