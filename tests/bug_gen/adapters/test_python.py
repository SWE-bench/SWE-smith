import ast

from swesmith.bug_gen.adapters.python import (
    _build_entity,
)


def parse_func(code):
    return ast.parse(code).body[0]


def test_signature_simple():
    code = "def foo(a, b): pass"
    node = parse_func(code)
    assert _build_entity(node, code, "test.py").signature == "def foo(a, b)"


def test_signature_no_args():
    code = "def bar(): pass"
    node = parse_func(code)
    assert _build_entity(node, code, "test.py").signature == "def bar()"


def test_signature_with_defaults():
    code = "def baz(a, b=2): pass"
    node = parse_func(code)
    assert _build_entity(node, code, "test.py").signature == "def baz(a, b)"


def test_signature_varargs():
    code = "def qux(*args, **kwargs): pass"
    node = parse_func(code)
    assert _build_entity(node, code, "test.py").signature == "def qux()"


def test_signature_annotations():
    code = "def annotated(a: int, b: str) -> None: pass"
    node = parse_func(code)
    assert (
        _build_entity(node, code, "test.py").signature
        == "def annotated(a: int, b: str)"
    )
