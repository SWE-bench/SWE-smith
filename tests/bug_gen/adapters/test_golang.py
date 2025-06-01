from swesmith.bug_gen.adapters.golang import (
    go_get_entities_from_file,
)


def test_go_get_entities_from_file(test_file_go):
    entities = []
    go_get_entities_from_file(entities, test_file_go)
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
