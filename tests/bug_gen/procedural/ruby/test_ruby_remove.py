from swesmith.bug_gen.adapters.ruby import get_entities_from_file_rb
from swesmith.bug_gen.procedural.ruby.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
    RemoveRescueEnsureModifier,
)


def test_remove_loop(tmp_path):
    src = """\
def count_down(n)
  x = n + 1
  y = x * 2
  while n > 0
    puts n
    n -= 1
  end
  y
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = RemoveLoopModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "while" not in modified.rewrite


def test_remove_until_loop(tmp_path):
    src = """\
def count_up(n)
  x = n + 1
  y = x * 2
  i = 0
  until i >= n
    puts i
    i += 1
  end
  y
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = RemoveLoopModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "until" not in modified.rewrite


def test_remove_for_loop(tmp_path):
    src = """\
def iterate(items)
  x = items.length + 1
  y = x * 2
  for item in items
    puts item
  end
  y
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = RemoveLoopModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "for item" not in modified.rewrite


def test_remove_conditional(tmp_path):
    src = """\
def check(x)
  y = x + 1
  z = y * 2
  if x > 0
    puts "positive"
  end
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = RemoveConditionalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "if x > 0" not in modified.rewrite


def test_remove_unless(tmp_path):
    src = """\
def check(x)
  y = x + 1
  z = y * 2
  unless x.nil?
    puts x
  end
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = RemoveConditionalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "unless" not in modified.rewrite


def test_remove_rescue(tmp_path):
    src = """\
def safe_parse(input)
  x = input + ""
  y = x.length > 0
  begin
    JSON.parse(input)
  rescue JSON::ParserError
    nil
  ensure
    Logger.flush
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = RemoveRescueEnsureModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "rescue" not in modified.rewrite
    assert "ensure" not in modified.rewrite


def test_remove_rescue_keyword_not_matched(tmp_path):
    """Ensure the rescue keyword token isn't matched as a removable node."""
    src = """\
def safe_parse(input)
  x = input + ""
  y = x.length > 0
  begin
    JSON.parse(input)
  rescue JSON::ParserError
    nil
  ensure
    Logger.flush
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    # likelihood=0.5, seed=3 previously deleted just the rescue keyword,
    # leaving JSON::ParserError orphaned without its keyword
    pm = RemoveRescueEnsureModifier(likelihood=0.5, seed=3)
    modified = pm.modify(entities[0])
    assert modified is not None
    # ensure block removed, rescue block kept intact
    assert "rescue" in modified.rewrite
    assert "JSON::ParserError" in modified.rewrite
    assert "ensure" not in modified.rewrite


def test_remove_assign(tmp_path):
    src = """\
def setup
  @name = "test"
  @count = 0
  @ready = true || false
  @extra = @count + 1
  @name
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = RemoveAssignModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # All four assignments removed, only bare @name return remains
    assert '@name = "test"' not in modified.rewrite
    assert "@count = 0" not in modified.rewrite


def test_remove_loop_no_loops(tmp_path):
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

    pm = RemoveLoopModifier(likelihood=1.0, seed=42)
    assert not pm.can_change(entities[0])
