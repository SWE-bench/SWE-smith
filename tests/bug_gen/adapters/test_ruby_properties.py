import pytest
from swesmith.bug_gen.adapters.ruby import get_entities_from_file_rb


@pytest.fixture
def ruby_test_file_entities(test_file_ruby):
    entities = []
    get_entities_from_file_rb(entities, test_file_ruby)
    assert len(entities) == 12
    return entities


def test_parse_query_properties(ruby_test_file_entities):
    """Test that parse_query entity has expected property tags."""
    entity_map = {e.name: e for e in ruby_test_file_entities}
    entity = entity_map["parse_query"]

    assert entity.is_function is True
    assert entity.has_if is True
    assert entity.has_if_else is True
    assert entity.has_assignment is True
    assert entity.has_binary_op is True
    assert entity.has_function_call is True


def test_normalize_params_properties(ruby_test_file_entities):
    """Test that _normalize_params entity has expected property tags."""
    entity_map = {e.name: e for e in ruby_test_file_entities}
    entity = entity_map["_normalize_params"]

    assert entity.is_function is True
    assert entity.has_if is True
    assert entity.has_if_else is True
    assert entity.has_return is True
    assert entity.has_assignment is True
    assert entity.has_binary_op is True
    assert entity.has_function_call is True


def test_make_params_properties(ruby_test_file_entities):
    """Test that make_params entity (simple method) has minimal tags."""
    entity_map = {e.name: e for e in ruby_test_file_entities}
    entity = entity_map["make_params"]

    assert entity.is_function is True
    assert entity.has_if is False
    assert entity.has_loop is False
    assert entity.has_binary_op is False


def test_comprehensive_ruby_properties(tmp_path):
    """Test _analyze_properties with a comprehensive Ruby function."""
    comprehensive_ruby_code = """\
def comprehensive_method(arr, threshold)
  return nil if arr.nil?
  sum = 0
  arr.each do |item|
    if item > threshold && item < 1000
      sum += item
    elsif item <= threshold
      sum -= item
    end
  end
  result = sum > 0 ? sum * 2 : 0
  process = ->(x) { x + 1 }
  process.call(result)
end
"""

    test_file = tmp_path / "comprehensive.rb"
    test_file.write_text(comprehensive_ruby_code)

    entities = []
    get_entities_from_file_rb(entities, test_file)

    assert len(entities) == 1
    entity = entities[0]

    assert entity.is_function is True
    assert entity.has_if is True
    assert entity.has_if_else is True
    assert entity.has_return is True
    assert entity.has_assignment is True
    assert entity.has_binary_op is True
    assert entity.has_bool_op is True
    assert entity.has_off_by_one is True
    assert entity.has_function_call is True
    assert entity.has_lambda is True
    assert entity.has_ternary is True
