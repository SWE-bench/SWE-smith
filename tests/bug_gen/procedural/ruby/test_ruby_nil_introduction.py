import pytest

from swesmith.bug_gen.adapters.ruby import get_entities_from_file_rb
from swesmith.bug_gen.procedural.ruby.nil_introduction import (
    BangMethodStripModifier,
    NilGuardRemovalModifier,
    OrDefaultRemovalModifier,
    OrEqualsRemovalModifier,
    PresenceStripModifier,
    SafeNavigationRemovalModifier,
)


def test_safe_navigation_removal(tmp_path):
    src = """\
def get_name(user)
  x = user&.name
  y = x&.length
  z = y || 0
  w = z + 1
  r = w * 2
  r
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = SafeNavigationRemovalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # First &. replaced with ., second kept
    assert "user.name" in modified.rewrite
    assert "x&.length" in modified.rewrite


def test_safe_navigation_no_safe_nav(tmp_path):
    src = """\
def get_name(user)
  x = user.name
  y = x.length + 1
  z = y * 2
  w = z - 1
  w
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = SafeNavigationRemovalModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_or_default_removal(tmp_path):
    src = """\
def get_name(params)
  name = params[:name] || "anonymous"
  x = name.length + 1
  y = x * 2
  name
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrDefaultRemovalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Fallback removed, left operand kept
    assert "name = params[:name]\n" in modified.rewrite
    assert "anonymous" not in modified.rewrite


def test_or_default_removal_or_keyword(tmp_path):
    """OrDefaultRemovalModifier handles Ruby's `or` keyword (not just `||`)."""
    src = """\
def get_name(params)
  name = params[:name] or "anonymous"
  x = name.length + 1
  y = x * 2
  name
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrDefaultRemovalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "name = params[:name]\n" in modified.rewrite
    assert "anonymous" not in modified.rewrite


def test_presence_strip(tmp_path):
    src = """\
def get_value(params)
  x = params[:name].presence
  y = x.to_s + "suffix"
  z = y.length * 2
  x
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = PresenceStripModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # .presence removed, receiver kept
    assert "x = params[:name]\n" in modified.rewrite
    assert ".presence" not in modified.rewrite


def test_bang_method_strip(tmp_path):
    src = """\
def find_user(id)
  x = id + 1
  y = x * 2
  User.take!(id)
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = BangMethodStripModifier(likelihood=1.0, seed=0)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "User.take(id)" in modified.rewrite
    assert "take!" not in modified.rewrite


def test_bang_method_strip_not_mutation_bang(tmp_path):
    """sort! and map! should NOT be stripped — not in the allowlist."""
    src = """\
def sort_items(items)
  x = items.length + 1
  y = x * 2
  items.sort!
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = BangMethodStripModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_or_equals_removal(tmp_path):
    src = """\
def cached_user
  @user ||= find_user
  x = @user.name + "suffix"
  y = x.length * 2
  @user
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrEqualsRemovalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "@user = find_user" in modified.rewrite
    assert "||=" not in modified.rewrite


def test_nil_guard_removal(tmp_path):
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
    assert len(entities) == 1

    pm = NilGuardRemovalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert "return if x.nil?" not in modified.rewrite
    # Guard removed but rest of method preserved
    assert "y = x + 1" in modified.rewrite


@pytest.mark.parametrize(
    "guard_line",
    [
        "return unless x.present?",
        "raise if x.nil?",
        "raise unless x.valid?",
    ],
)
def test_nil_guard_removal_variants(tmp_path, guard_line):
    """NilGuardRemovalModifier handles unless and other guard keywords."""
    src = f"""\
def process(x)
  {guard_line}
  y = x + 1
  z = y * 2
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = NilGuardRemovalModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    assert guard_line not in modified.rewrite
    assert "y = x + 1" in modified.rewrite


def test_safe_navigation_removal_flip_failure(tmp_path):
    """SafeNavigationRemovalModifier returns None when likelihood=0.0."""
    src = """\
def get_name(user)
  x = user&.name
  y = x&.length
  z = y || 0
  w = z + 1
  r = w * 2
  r
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = SafeNavigationRemovalModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_or_default_removal_skips_conditionals(tmp_path):
    """OrDefaultRemovalModifier skips || inside conditionals."""
    src = """\
def check_date(date, from_date, to_date)
  x = date.to_i + 1
  y = x * 2
  if date > to_date || date < from_date
    raise "out of range"
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrDefaultRemovalModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_or_default_removal_skips_nested_conditional(tmp_path):
    """OrDefaultRemovalModifier skips || nested in parens inside conditionals."""
    src = """\
def check_date(date, from_date, to_date)
  x = date.to_i + 1
  y = x * 2
  if date.valid? && (date > to_date || date < from_date)
    raise "out of range"
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrDefaultRemovalModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_or_default_removal_inside_conditional_body(tmp_path):
    """OrDefaultRemovalModifier modifies || defaults inside conditional bodies."""
    src = """\
def get_name(params, flag)
  x = flag.to_s + "check"
  y = x.length * 2
  if flag == true
    name = params[:name] || "anonymous"
  end
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrDefaultRemovalModifier(likelihood=1.0, seed=42)
    modified = pm.modify(entities[0])
    assert modified is not None
    assert "name = params[:name]\n" in modified.rewrite
    assert '"anonymous"' not in modified.rewrite


def test_or_default_removal_no_or(tmp_path):
    """OrDefaultRemovalModifier returns None when no || operators present."""
    src = """\
def check(a, b)
  x = a && b
  y = x + 1
  z = y * 2
  x
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrDefaultRemovalModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_presence_strip_no_presence(tmp_path):
    """PresenceStripModifier returns None when no .presence calls present."""
    src = """\
def get_value(params)
  x = params[:name].to_s
  y = x + "suffix"
  z = y.length * 2
  x
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = PresenceStripModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_or_equals_removal_no_or_equals(tmp_path):
    """OrEqualsRemovalModifier returns None when no ||= operators present."""
    src = """\
def update(x)
  x += 1
  y = x * 2
  z = y - 1
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = OrEqualsRemovalModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_nil_guard_removal_no_guards(tmp_path):
    """NilGuardRemovalModifier returns None when modifier-ifs aren't guard clauses."""
    src = """\
def process(x, verbose)
  puts "hi" if verbose
  y = x + 1
  z = y * 2
  z
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = NilGuardRemovalModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_nil_guard_removal_flip_failure(tmp_path):
    """NilGuardRemovalModifier returns None when likelihood=0.0."""
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

    pm = NilGuardRemovalModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None
