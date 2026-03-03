from swesmith.bug_gen.adapters.ruby import get_entities_from_file_rb
from swesmith.bug_gen.procedural.ruby.ruby_specific import (
    BlockMutationModifier,
    SymbolStringSwapModifier,
)


def test_symbol_string_swap_symbol_to_string(tmp_path):
    src = """\
def render_page(opts)
  x = opts[:size] + 1
  y = x * 2
  render action: :index
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = SymbolStringSwapModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # :size symbol swapped to "size" string
    assert '"size"' in modified.rewrite
    assert "opts[:size]" not in modified.rewrite


def test_symbol_string_swap_string_to_symbol(tmp_path):
    src = """\
def get_type(config)
  x = config["format"]
  y = x + "suffix"
  z = y.length > 0
  x
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = SymbolStringSwapModifier(likelihood=1.0, seed=42)

    modified = pm.modify(entities[0])
    assert modified is not None
    # "format" string swapped to :format symbol
    assert "config[:format]" in modified.rewrite


def test_block_mutation_remove_params(tmp_path):
    src = """\
def process(items)
  x = items.length + 1
  y = x * 2
  items.each { |item| puts item }
  y
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = BlockMutationModifier(likelihood=1.0, seed=42)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # Block parameters |item| removed
    assert "|item|" not in modified.rewrite
    assert "puts item" in modified.rewrite


def test_block_mutation_strip_yield(tmp_path):
    src = """\
def with_logging(name, value)
  x = name + value
  y = x.length * 2
  puts "start"
  yield name, value
  puts "end"
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = BlockMutationModifier(likelihood=1.0, seed=0)
    assert pm.can_change(entities[0])

    modified = pm.modify(entities[0])
    assert modified is not None
    # yield(name, value) stripped to bare yield
    assert "yield\n" in modified.rewrite
    assert "yield name" not in modified.rewrite


def test_block_mutation_no_blocks(tmp_path):
    src = """\
def simple(x)
  y = x + 1
  z = y * 2
  z - x
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)
    assert len(entities) == 1

    pm = BlockMutationModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None


def test_symbol_string_swap_flip_failure(tmp_path):
    """SymbolStringSwapModifier returns None when likelihood=0.0."""
    src = """\
def render_page(opts)
  x = opts[:size] + 1
  y = x * 2
  render action: :index
end
"""
    f = tmp_path / "test.rb"
    f.write_text(src)
    entities = []
    get_entities_from_file_rb(entities, f)

    pm = SymbolStringSwapModifier(likelihood=0.0, seed=42)
    assert pm.modify(entities[0]) is None


def test_symbol_string_swap_no_candidates(tmp_path):
    """SymbolStringSwapModifier returns None with only dynamic/interpolated strings."""
    src = """\
def render_page(opts)
  x = opts[:"dynamic_#{key}"]
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

    pm = SymbolStringSwapModifier(likelihood=1.0, seed=42)
    result = pm.modify(entities[0])
    assert result is None
