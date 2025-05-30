import ast
from swesmith.bug_gen.llm.utils import extract_code_block, get_function_signature


def parse_func(code):
    return ast.parse(code).body[0]


def test_extract_code_block_basic():
    text = """
    Here is some code:
    ```python\nprint('hello')\n```
    """
    assert extract_code_block(text) == "print('hello')"


def test_extract_code_block_no_language():
    text = """
    Example:
    ```\nfoo = 1\nbar = 2\n```
    """
    assert extract_code_block(text) == "foo = 1\nbar = 2"


def test_extract_code_block_no_block():
    text = "No code block here."
    assert extract_code_block(text) == ""


def test_extract_code_block_multiple_blocks():
    text = """
    ```python\nfirst = True\n```
    Some text
    ```python\nsecond = False\n```
    """
    # Should extract only the first block
    assert extract_code_block(text) == "first = True"


def test_extract_code_block_strip_whitespace():
    text = """
    ```\n   a = 1\n   b = 2   \n\n```
    """
    assert extract_code_block(text) == "a = 1\n   b = 2"


def test_get_function_signature_simple():
    node = parse_func("def foo(a, b): pass")
    assert get_function_signature(node) == "def foo(a, b)"


def test_get_function_signature_no_args():
    node = parse_func("def bar(): pass")
    assert get_function_signature(node) == "def bar()"


def test_get_function_signature_with_defaults():
    node = parse_func("def baz(a, b=2): pass")
    assert get_function_signature(node) == "def baz(a, b)"


def test_get_function_signature_varargs():
    node = parse_func("def qux(*args, **kwargs): pass")
    assert get_function_signature(node) == "def qux()"


def test_get_function_signature_annotations():
    node = parse_func("def annotated(a: int, b: str) -> None: pass")
    assert get_function_signature(node) == "def annotated(a: int, b: str)"
