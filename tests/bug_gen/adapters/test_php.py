from swesmith.bug_gen.adapters.php import (
    get_entities_from_file_php,
)


def test_get_entities_from_file_php(test_file_php):
    entities = []
    get_entities_from_file_php(entities, test_file_php)
    assert len(entities) == 5
    names = [e.name for e in entities]
    for name in [
        "ControllerDispatcher",
        "ControllerDispatcher::__construct",
        "ControllerDispatcher::dispatch",
        "ControllerDispatcher::resolveParameters",
        "ControllerDispatcher::getMiddleware",
    ]:
        assert name in names, f"Expected entity {name} not found in {names}"

    start_end = [(e.line_start, e.line_end) for e in entities]
    for start, end in [
        (10, 82),  # ControllerDispatcher class
        (26, 29),  # ControllerDispatcher::__construct
        (39, 48),  # ControllerDispatcher::dispatch
        (58, 63),  # ControllerDispatcher::resolveParameters
        (72, 81),  # ControllerDispatcher::getMiddleware
    ]:
        assert (start, end) in start_end, (
            f"Expected line range ({start}, {end}) not found in {start_end}"
        )

    assert all([e.ext == "php" for e in entities]), (
        "All entities should have the extension 'php'"
    )
    assert all([e.file_path == str(test_file_php) for e in entities]), (
        "All entities should have the correct file path"
    )

    signatures = [e.signature for e in entities]
    for signature in [
        "class ControllerDispatcher implements ControllerDispatcherContract",
        "public function __construct(Container $container)",
        "public function dispatch(Route $route, $controller, $method)",
        "protected function resolveParameters(Route $route, $controller, $method)",
        "public function getMiddleware($controller, $method)",
    ]:
        assert signature in signatures, (
            f"Expected signature '{signature}' not found in {signatures}"
        )

    stubs = [e.stub for e in entities]
    for stub in [
        "class ControllerDispatcher implements ControllerDispatcherContract {\n\t// TODO: Implement this function\n}",
        "public function __construct(Container $container) {\n\t// TODO: Implement this function\n}",
        "public function dispatch(Route $route, $controller, $method) {\n\t// TODO: Implement this function\n}",
        "protected function resolveParameters(Route $route, $controller, $method) {\n\t// TODO: Implement this function\n}",
        "public function getMiddleware($controller, $method) {\n\t// TODO: Implement this function\n}",
    ]:
        assert stub in stubs, f"Expected stub '{stub}' not found in {stubs}"


def test_get_entities_from_file_php_max(test_file_php):
    """Should cap the number of returned entities when *max_entities* is set."""
    entities: list = []
    get_entities_from_file_php(entities, test_file_php, 3)

    # Only three entities should be returned and they should be in the order
    # encountered in the file (depth-first traversal used by the adapter).
    assert len(entities) == 3
    assert [e.name for e in entities] == [
        "ControllerDispatcher",
        "ControllerDispatcher::__construct",
        "ControllerDispatcher::dispatch",
    ]


def test_get_entities_from_file_php_unreadable():
    """Asserting that unreadable / non-existent files are handled gracefully."""
    entities: list = []
    # The adapter swallows exceptions internally and simply returns the (still
    # empty) *entities* list, so we just verify that behaviour.
    get_entities_from_file_php(entities, "non-existent-file.php")
    assert entities == []


def test_get_entities_from_file_php_no_entities(tmp_path):
    """A PHP file with no top-level functions, methods or classes yields no entities."""
    no_entities_file = tmp_path / "no_entities.php"
    no_entities_file.write_text("<?php\n// Silence is golden\n")

    entities: list = []
    get_entities_from_file_php(entities, no_entities_file)
    assert len(entities) == 0


def test_php_entity_one_line_function(tmp_path):
    """Correctly pick up a function that lives entirely on one line."""
    one_line_file = tmp_path / "one_line.php"
    one_line_file.write_text("<?php\nfunction one_line_function() { return 42; }\n")

    entities: list = []
    get_entities_from_file_php(entities, one_line_file)

    assert len(entities) == 1
    entity = entities[0]
    assert entity.name == "one_line_function"
    assert entity.signature == "function one_line_function()"
    assert (
        entity.stub
        == "function one_line_function() {\n\t// TODO: Implement this function\n}"
    )


def test_php_entity_multi_line_signature(tmp_path):
    """Multi-line function signatures should be preserved in *signature*."""
    multi_line_file = tmp_path / "multi_line.php"
    multi_line_file.write_text(
        "<?php\nfunction multi_line_function(\n    $param1,\n    $param2\n) {\n    return $param1 + $param2;\n}\n"
    )

    entities: list = []
    get_entities_from_file_php(entities, multi_line_file)

    assert len(entities) == 1
    entity = entities[0]
    assert entity.name == "multi_line_function"
    assert (
        entity.signature
        == "function multi_line_function(\n    $param1,\n    $param2\n)"
    )
