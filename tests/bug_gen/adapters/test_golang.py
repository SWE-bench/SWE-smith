import pytest
import re
import warnings

from swesmith.bug_gen.adapters.golang import (
    get_entities_from_file_go,
)


@pytest.fixture
def entities(test_file_go):
    entities = []
    get_entities_from_file_go(entities, test_file_go)
    return entities


def test_get_entities_from_file_go_count(entities):
    assert len(entities) == 12


def test_get_entities_from_file_go_max(test_file_go):
    entities = []
    get_entities_from_file_go(entities, test_file_go, 3)
    assert len(entities) == 3


def test_get_entities_from_file_go_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_go([], "non-existent-file")


def test_get_entities_from_file_go_no_functions(tmp_path):
    no_functions_file = tmp_path / "no_functions.go"
    no_functions_file.write_text("// there are no functions here")
    entities = []
    get_entities_from_file_go(entities, no_functions_file)
    assert len(entities) == 0


def test_get_entities_from_file_go_malformed(tmp_path):
    malformed_file = tmp_path / "malformed.go"
    malformed_file.write_text("(malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_go(entities, malformed_file)
        assert any(
            [
                re.search(r"Error encountered parsing .*malformed.go", str(w.message))
                for w in ws
            ]
        )


def test_get_entities_from_file_go_names(entities):
    names = [e.name for e in entities]
    expected_names = [
        "LogFormatterParams.StatusCodeColor",
        "LogFormatterParams.MethodColor",
        "LogFormatterParams.ResetColor",
        "LogFormatterParams.IsOutputColor",
        "DisableConsoleColor",
        "ForceConsoleColor",
        "ErrorLogger",
        "ErrorLoggerT",
        "Logger",
        "LoggerWithFormatter",
        "LoggerWithWriter",
        "LoggerWithConfig",
    ]
    for name in expected_names:
        assert name in names, f"Expected entity {name} not found in {names}"


def test_get_entities_from_file_go_line_ranges(entities):
    start_end = [(e.line_start, e.line_end) for e in entities]
    expected_ranges = [
        (90, 105),
        (108, 129),
        (132, 134),
        (137, 139),
        (165, 167),
        (170, 172),
        (175, 177),
        (180, 188),
        (192, 194),
        (197, 201),
        (205, 210),
        (213, 282),
    ]
    for start, end in expected_ranges:
        assert (start, end) in start_end, (
            f"Expected line range ({start}, {end}) not found in {start_end}"
        )


def test_get_entities_from_file_go_extensions(entities):
    assert all([e.ext == "go" for e in entities]), (
        "All entities should have the extension 'go'"
    )


def test_get_entities_from_file_go_file_paths(entities, test_file_go):
    assert all([e.file_path == test_file_go for e in entities]), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_go_signatures(entities):
    signatures = [e.signature for e in entities]
    expected_signatures = [
        "func (p *LogFormatterParams) StatusCodeColor() string",
        "func (p *LogFormatterParams) MethodColor() string",
        "func (p *LogFormatterParams) ResetColor() string",
        "func (p *LogFormatterParams) IsOutputColor() bool",
        "func DisableConsoleColor()",
        "func ForceConsoleColor()",
        "func ErrorLogger() HandlerFunc",
        "func ErrorLoggerT(typ ErrorType) HandlerFunc",
        "func Logger() HandlerFunc",
        "func LoggerWithFormatter(f LogFormatter) HandlerFunc",
        "func LoggerWithWriter(out io.Writer, notlogged ...string) HandlerFunc",
        "func LoggerWithConfig(conf LoggerConfig) HandlerFunc",
    ]
    for signature in expected_signatures:
        assert signature in signatures, (
            f"Expected signature '{signature}' not found in {signatures}"
        )


def test_get_entities_from_file_go_signature_empty_interface(tmp_path):
    empty_interface_arg_file = tmp_path / "empty_interface_arg.go"
    empty_interface_arg_file.write_text("func TakesEmptyInterface(a interface{}) {}")
    entities = []
    get_entities_from_file_go(entities, empty_interface_arg_file)
    assert len(entities) == 1
    assert entities[0].signature == "func TakesEmptyInterface(a interface{})"


def test_get_entities_from_file_go_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "func (p *LogFormatterParams) StatusCodeColor() string {\n\t// TODO: Implement this function\n}",
        "func (p *LogFormatterParams) MethodColor() string {\n\t// TODO: Implement this function\n}",
        "func (p *LogFormatterParams) ResetColor() string {\n\t// TODO: Implement this function\n}",
        "func (p *LogFormatterParams) IsOutputColor() bool {\n\t// TODO: Implement this function\n}",
        "func DisableConsoleColor() {\n\t// TODO: Implement this function\n}",
        "func ForceConsoleColor() {\n\t// TODO: Implement this function\n}",
        "func ErrorLogger() HandlerFunc {\n\t// TODO: Implement this function\n}",
        "func ErrorLoggerT(typ ErrorType) HandlerFunc {\n\t// TODO: Implement this function\n}",
        "func Logger() HandlerFunc {\n\t// TODO: Implement this function\n}",
        "func LoggerWithFormatter(f LogFormatter) HandlerFunc {\n\t// TODO: Implement this function\n}",
        "func LoggerWithWriter(out io.Writer, notlogged ...string) HandlerFunc {\n\t// TODO: Implement this function\n}",
        "func LoggerWithConfig(conf LoggerConfig) HandlerFunc {\n\t// TODO: Implement this function\n}",
    ]
    for stub in expected_stubs:
        assert stub in stubs, f"Expected stub '{stub}' not found in {stubs}"


def test_get_entities_from_file_go_complexity(entities):
    complexity_scores = [(e.name, e.complexity) for e in entities]
    expected_scores = [
        ("LogFormatterParams.StatusCodeColor", 18),
        ("LogFormatterParams.MethodColor", 9),
        ("LogFormatterParams.ResetColor", 1),
        ("LogFormatterParams.IsOutputColor", 5),
        ("DisableConsoleColor", 1),
        ("ForceConsoleColor", 1),
        ("ErrorLogger", 1),
        ("ErrorLoggerT", 3),
        ("Logger", 1),
        ("LoggerWithFormatter", 1),
        ("LoggerWithWriter", 1),
        ("LoggerWithConfig", 19),
    ]
    assert complexity_scores == expected_scores


def test_get_entities_from_file_go_complexity_else(tmp_path):
    if_else_file = tmp_path / "if_else.go"
    if_else_file.write_text(
        """
func f(i int) {
	if i == 1 {

	} else if i == 2 {

	} else {

	}
}
    """.strip()
    )
    entities = []
    get_entities_from_file_go(entities, if_else_file)
    assert len(entities) == 1
    assert entities[0].complexity == 7


@pytest.mark.parametrize(
    "func_definition",
    [
        ("func f() { defer func() {}() }"),
        ("func f() { go func() {}() }"),
        ("func f(c chan struct{}) { <-c }"),
        ("func f(c chan struct{}) { c <- struct{}{} }"),
    ],
)
def test_get_entities_from_file_go_complexity_other_statements(
    tmp_path, func_definition
):
    stmt_file = tmp_path / "stmt.go"
    stmt_file.write_text(func_definition)
    entities = []
    get_entities_from_file_go(entities, stmt_file)
    assert len(entities) == 1
    assert entities[0].complexity == 2
