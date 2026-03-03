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
    # Outer if/else swapped: "non-positive" now in then-branch
    assert '"non-positive"' in modified.rewrite.split("if x > 0")[1].split("else")[0]


def test_control_if_else_invert_no_else(tmp_path):
    src = """\
def check(x)
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
    # Statements reordered: @ready appears before @count
    lines = modified.rewrite.strip().split("\n")
    ready_idx = next(i for i, line in enumerate(lines) if "@ready" in line)
    count_idx = next(i for i, line in enumerate(lines) if "@count = 0" in line)
    assert ready_idx < count_idx


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
