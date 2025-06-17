import pytest
import re
import warnings
from swesmith.bug_gen.adapters.ruby import (
    get_entities_from_file_rb,
)


@pytest.fixture
def ruby_test_file_entities(test_file_ruby):
    entities = []
    get_entities_from_file_rb(entities, test_file_ruby)
    assert len(entities) == 12
    return entities


def test_get_entities_from_file_rb_max(test_file_ruby):
    entities = []
    get_entities_from_file_rb(entities, test_file_ruby, 3)
    assert len(entities) == 3
    assert [e.name for e in entities] == ["make_default", "initialize", "parse_query"]


def test_get_entities_from_file_rb_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_rb([], "non-existent-file")


def test_get_entities_from_file_rb_no_functions(tmp_path):
    no_functions_file = tmp_path / "no_functions.rb"
    no_functions_file.write_text("# Matz Is Nice And So We Are Nice")
    entities = []
    get_entities_from_file_rb(entities, no_functions_file)
    assert len(entities) == 0


def test_get_entities_from_file_rb_empty_function(tmp_path):
    empty_function_file = tmp_path / "empty_function.rb"
    empty_function_file.write_text("def empty_function\nend")
    entities = []
    get_entities_from_file_rb(entities, empty_function_file)
    assert len(entities) == 0


def test_get_entities_from_file_rb_malformed(tmp_path):
    malformed_file = tmp_path / "malformed.rb"
    malformed_file.write_text("(malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_rb(entities, malformed_file)
        assert any(
            [
                re.search(r"Error encountered parsing .*malformed.rb", str(w.message))
                for w in ws
            ]
        )


def test_ruby_entity_names(ruby_test_file_entities):
    names = [e.name for e in ruby_test_file_entities]
    for name in [
        "make_default",
        "initialize",
        "parse_query",
        "parse_nested_query",
        "normalize_params",
        "_normalize_params",
        "make_params",
        "new_depth_limit",
        "params_hash_type?",
        "params_hash_has_key?",
        "check_query_string",
        "unescape",
    ]:
        assert name in names, f"Expected entity {name} not found in {names}"


def test_ruby_entity_file_positions(ruby_test_file_entities):
    start_end = [(e.line_start, e.line_end) for e in ruby_test_file_entities]
    for start, end in [
        (36, 38),
        (60, 65),
        (71, 92),
        (99, 113),
        (120, 122),
        (124, 190),
        (192, 194),
        (196, 198),
        (202, 204),
        (206, 216),
        (218, 232),
        (234, 236),
    ]:
        assert (start, end) in start_end, (
            f"Expected line range ({start}, {end}) not found in {start_end}"
        )


def test_ruby_entity_file_paths(test_file_ruby, ruby_test_file_entities):
    assert all([e.ext == "rb" for e in ruby_test_file_entities]), (
        "All ruby_test_file_entities should have the extension 'rb'"
    )
    assert all([e.file_path == str(test_file_ruby) for e in ruby_test_file_entities]), (
        "All ruby_test_file_entities should have the correct file path"
    )


FUNCTION_SIGNATURES = [
    "def self.make_default(param_depth_limit, **options)",
    "def initialize(params_class, param_depth_limit, bytesize_limit: BYTESIZE_LIMIT, params_limit: PARAMS_LIMIT)",
    "def parse_query(qs, separator = nil, &unescaper)",
    "def parse_nested_query(qs, separator = nil)",
    "def normalize_params(params, name, v, _depth=nil)",
    "private def _normalize_params(params, name, v, depth)",
    "def make_params",
    "def new_depth_limit(param_depth_limit)",
    "def params_hash_type?(obj)",
    "def params_hash_has_key?(hash, key)",
    "def check_query_string(qs, sep)",
    "def unescape(string, encoding = Encoding::UTF_8)",
]


def test_ruby_entity_signatures(ruby_test_file_entities):
    signatures = [e.signature for e in ruby_test_file_entities]
    assert signatures == FUNCTION_SIGNATURES


def test_ruby_entity_stubs(ruby_test_file_entities):
    stubs = [e.stub for e in ruby_test_file_entities]
    assert stubs == [
        f"{fs}\n\t# TODO: Implement this function\nend" for fs in FUNCTION_SIGNATURES
    ]


def test_ruby_entity_one_line_method(tmp_path):
    one_line_method_file = tmp_path / "one_line_method.rb"
    one_line_method_file.write_text("def one_line_method; :all_on_one_line; end")
    entities = []
    get_entities_from_file_rb(entities, one_line_method_file)
    assert len(entities) == 1
    assert entities[0].name == "one_line_method"
    assert entities[0].signature == "def one_line_method"


def test_ruby_entity_multi_line_signature(tmp_path):
    multi_line_sig_file = tmp_path / "multi_line_signature.rb"
    multi_line_sig_file.write_text(
        """
    def multi_line_signature(
      multiple,
      lines
    )
      :signature_across_lines
    end
    """
    )
    entities = []
    get_entities_from_file_rb(entities, multi_line_sig_file)
    assert len(entities) == 1
    assert entities[0].name == "multi_line_signature"
    assert entities[0].signature == "def multi_line_signature(\n  multiple,\n  lines\n)"


def test_get_entities_from_file_ruby_complexity(ruby_test_file_entities):
    complexity_scores = [(e.name, e.complexity) for e in ruby_test_file_entities]
    expected_scores = [
        ("make_default", 1),
        ("initialize", 1),
        ("parse_query", 14),
        ("parse_nested_query", 9),
        ("normalize_params", 1),
        ("_normalize_params", 50),
        ("make_params", 1),
        ("new_depth_limit", 1),
        ("params_hash_type?", 1),
        ("params_hash_has_key?", 7),
        ("check_query_string", 10),
        ("unescape", 1),
    ]
    assert complexity_scores == expected_scores


@pytest.mark.parametrize(
    "expr",
    [
        "true and true",
        "true or false",
        "foo rescue nil",
        "bar until true",
        "bar while false",
        "begin\n  some_action\nensure\n  cleanup\nend",
        "case\nwhen false\n  perform_some_action\nend",
    ],
)
def test_get_entities_from_file_ruby_complexity_other_expressions(tmp_path, expr):
    expr_file = tmp_path / "expr.rb"
    expr_file.write_text(f"def f\n  {expr}\nend")
    entities = []
    get_entities_from_file_rb(entities, expr_file)
    assert len(entities) == 1
    assert entities[0].complexity == 2
