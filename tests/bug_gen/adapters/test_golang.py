from swesmith.bug_gen.adapters.golang import (
    get_entities_from_file_go,
)


def test_get_entities_from_file_go(test_file_go):
    entities = []
    get_entities_from_file_go(entities, test_file_go)
    assert len(entities) == 12
    names = [e.name for e in entities]
    for name in [
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
    ]:
        assert name in names, f"Expected entity {name} not found in {names}"
    start_end = [(e.line_start, e.line_end) for e in entities]
    for start, end in [
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
    ]:
        assert (start, end) in start_end, (
            f"Expected line range ({start}, {end}) not found in {start_end}"
        )
    assert all([e.ext == "go" for e in entities]), (
        "All entities should have the extension 'go'"
    )
    assert all([e.file_path == str(test_file_go) for e in entities]), (
        "All entities should have the correct file path"
    )
    signatures = [e.signature for e in entities]
    for signature in [
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
    ]:
        assert signature in signatures, (
            f"Expected signature '{signature}' not found in {signatures}"
        )
    stubs = [e.stub for e in entities]
    for stub in [
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
    ]:
        assert stub in stubs, f"Expected stub '{stub}' not found in {stubs}"
