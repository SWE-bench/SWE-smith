from swesmith.bug_gen.llm.utils import extract_code_block


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
