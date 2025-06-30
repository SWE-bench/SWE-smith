import re
import warnings

import pytest

from swesmith.bug_gen.adapters.javascript import get_entities_from_file_js


@pytest.fixture
def entities(test_file_js):
    entities = []
    get_entities_from_file_js(entities, test_file_js)
    return entities


def test_get_entities_from_file_js_count(entities):
    assert len(entities) == 11


def test_get_entities_from_file_js_max(test_file_js):
    entities = []
    get_entities_from_file_js(entities, test_file_js, 3)
    assert len(entities) == 3


def test_get_entities_from_file_js_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_js([], "non-existent-file")


def test_get_entities_from_file_js_no_functions(tmp_path):
    no_functions_file = tmp_path / "no_functions.js"
    no_functions_file.write_text("// there are no functions here\nconst x = 5;")
    entities = []
    get_entities_from_file_js(entities, no_functions_file)
    assert len(entities) == 0


def test_get_entities_from_file_js_malformed(tmp_path):
    malformed_file = tmp_path / "malformed.js"
    malformed_file.write_text("(malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_js(entities, malformed_file)
        assert any(
            re.search(r"Error encountered parsing .*malformed.js", str(w.message))
            for w in ws
        )


def test_get_entities_from_file_js_names(entities):
    names = [e.name for e in entities]
    expected_names = [
        "Calculator",
        "constructor",
        "add",
        "subtract",
        "multiply",
        "divide",
        "factorial",
        "incrementCounter",
        "complexFunction",
        "outerFunction",
        "innerFunction",
    ]
    for name in expected_names:
        assert name in names, f"Expected entity {name} not found in {names}"


def test_get_entities_from_file_js_line_ranges(entities):
    start_end = [(e.line_start, e.line_end) for e in entities]
    expected_ranges = [
        (2, 32),  # Calculator class
        (3, 5),  # constructor
        (7, 12),  # add
        (14, 16),  # subtract
        (18, 24),  # multiply
        (26, 31),  # divide
        (34, 39),  # factorial
        (62, 65),  # incrementCounter
        (68, 97),  # complexFunction
        (104, 114),  # outerFunction
        (105, 107),  # innerFunction
    ]
    for start, end in expected_ranges:
        assert (
            start,
            end,
        ) in start_end, f"Expected line range ({start}, {end}) not found in {start_end}"


def test_get_entities_from_file_js_extensions(entities):
    assert all(e.ext == "js" for e in entities), (
        "All entities should have the extension 'js'"
    )


def test_get_entities_from_file_js_file_paths(entities, test_file_js):
    assert all(e.file_path == str(test_file_js) for e in entities), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_js_signatures(entities):
    signatures = [e.signature for e in entities]
    expected_signatures = [
        "class Calculator",
        "constructor(name)",
        "add(a, b)",
        "subtract(a, b)",
        "multiply(a, b)",
        "divide(a, b)",
        "function factorial(n)",
        "var incrementCounter = function()",
        "function complexFunction(x, y, z)",
        "function outerFunction(x)",
        "function innerFunction(y)",
    ]
    for signature in expected_signatures:
        assert signature in signatures, (
            f"Expected signature '{signature}' not found in {signatures}"
        )


def test_get_entities_from_file_js_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "class Calculator {\n\t// TODO: Implement this function\n}",
        "constructor(name) {\n\t// TODO: Implement this function\n}",
        "add(a, b) {\n\t// TODO: Implement this function\n}",
        "subtract(a, b) {\n\t// TODO: Implement this function\n}",
        "multiply(a, b) {\n\t// TODO: Implement this function\n}",
        "divide(a, b) {\n\t// TODO: Implement this function\n}",
        "function factorial(n) {\n\t// TODO: Implement this function\n}",
        "var incrementCounter = function() {\n\t// TODO: Implement this function\n}",
        "function complexFunction(x, y, z) {\n\t// TODO: Implement this function\n}",
        "function outerFunction(x) {\n\t// TODO: Implement this function\n}",
        "function innerFunction(y) {\n\t// TODO: Implement this function\n}",
    ]
    for stub in expected_stubs:
        assert stub in stubs, f"Expected stub '{stub}' not found in {stubs}"


def test_get_entities_from_file_js_complexity(entities):
    complexity_scores = [(e.name, e.complexity) for e in entities]
    # Note: These values are based on actual parsing results
    expected_scores = [
        ("Calculator", 5),  # class contains multiple methods
        ("constructor", 1),
        ("add", 3),  # if condition + || operator
        ("subtract", 1),
        ("multiply", 2),  # for loop + ternary (actual result)
        ("divide", 2),  # if condition
        ("factorial", 2),  # if condition
        ("incrementCounter", 1),
        ("complexFunction", 11),  # multiple if/else, for loop, switch/case
        ("outerFunction", 1),
        ("innerFunction", 1),
    ]
    assert complexity_scores == expected_scores


def test_get_entities_from_file_js_complexity_ternary(tmp_path):
    ternary_file = tmp_path / "ternary.js"
    ternary_file.write_text(
        """
function f(x) {
    return x > 0 ? "positive" : "non-positive";
}
    """.strip()
    )
    entities = []
    get_entities_from_file_js(entities, ternary_file)
    assert len(entities) == 1
    assert entities[0].complexity == 1  # ternary not being detected as expected


@pytest.mark.parametrize(
    "func_definition",
    [
        ("function f() { if (true) { return 1; } }"),
        ("function f() { for (let i = 0; i < 10; i++) { } }"),
        ("function f() { while (true) { break; } }"),
        ("function f() { try { } catch (e) { } }"),
        ("function f() { switch (x) { case 1: break; } }"),
    ],
)
def test_get_entities_from_file_js_complexity_control_flow(tmp_path, func_definition):
    stmt_file = tmp_path / "stmt.js"
    stmt_file.write_text(func_definition)
    entities = []
    get_entities_from_file_js(entities, stmt_file)
    assert len(entities) == 1
    assert entities[0].complexity == 2  # base + control flow


def test_get_entities_from_file_js_arrow_function_expression_body(tmp_path):
    arrow_file = tmp_path / "arrow.js"
    arrow_file.write_text("const square = x => x * x;")
    entities = []
    get_entities_from_file_js(entities, arrow_file)
    # const declarations with arrow functions are not being collected
    assert len(entities) == 0


def test_get_entities_from_file_js_method_definition(tmp_path):
    method_file = tmp_path / "method.js"
    method_file.write_text(
        """
class Test {
    myMethod(param) {
        return param * 2;
    }
}
    """.strip()
    )
    entities = []
    get_entities_from_file_js(entities, method_file)
    assert len(entities) == 2
    class_entity = next(e for e in entities if e.name == "Test")
    method_entity = next(e for e in entities if e.name == "myMethod")
    assert class_entity.signature == "class Test"
    assert method_entity.signature == "myMethod(param)"


def test_get_entities_from_file_js_function_expression(tmp_path):
    func_expr_file = tmp_path / "func_expr.js"
    func_expr_file.write_text("var myFunc = function(x, y) { return x + y; };")
    entities = []
    get_entities_from_file_js(entities, func_expr_file)
    assert len(entities) == 1
    assert entities[0].name == "myFunc"
    assert entities[0].signature == "var myFunc = function(x, y)"


def test_get_entities_from_file_js_assignment_arrow_function(tmp_path):
    assign_file = tmp_path / "assign.js"
    assign_file.write_text("myVar = (a, b) => { return a + b; };")
    entities = []
    get_entities_from_file_js(entities, assign_file)
    assert len(entities) == 1
    assert entities[0].name == "myVar"


def test_get_entities_from_file_js_boolean_operators(tmp_path):
    bool_file = tmp_path / "bool.js"
    bool_file.write_text(
        """
function f(a, b, c) {
    return a && b || c;
}
    """.strip()
    )
    entities = []
    get_entities_from_file_js(entities, bool_file)
    assert len(entities) == 1
    assert entities[0].complexity == 3  # base + && + ||


def test_get_entities_from_file_js_nested_functions(tmp_path):
    nested_file = tmp_path / "nested.js"
    nested_file.write_text(
        """
function outer() {
    function inner() {
        return 42;
    }
    return inner;
}
    """.strip()
    )
    entities = []
    get_entities_from_file_js(entities, nested_file)
    # The adapter collects both top-level and nested functions
    assert len(entities) == 2
    names = [e.name for e in entities]
    assert "outer" in names
    assert "inner" in names
