import ast
import pytest

from swesmith.bug_gen.adapters.python import (
    get_entities_from_file_py,
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


@pytest.fixture
def entities(test_file_py):
    entities = []
    get_entities_from_file_py(entities, test_file_py)
    return sorted(entities, key=lambda e: e.name)


def test_get_entities_from_file_py_count(entities):
    assert len(entities) == 13


def test_get_entities_from_file_py_extensions(entities):
    assert all([e.ext == "py" for e in entities]), (
        "All entities should have the extension 'py'"
    )


def test_get_entities_from_file_py_file_paths(entities, test_file_py):
    assert all([e.file_path == test_file_py for e in entities]), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_py_names(entities):
    expected_names = [
        "ExtensionIndex",
        "NDArrayBackedExtensionIndex",
        "_from_join_target",
        "_get_engine_target",
        "_inherit_from_data",
        "_isnan",
        "_validate_fill_value",
        "cached",
        "fget",
        "fset",
        "inherit_names",
        "method",
        "wrapper",
    ]
    for e, expected_name in zip(entities, expected_names):
        assert e.name == expected_name, f"Expected name {expected_name}, got {e.name}"


def test_get_entities_from_file_py_line_ranges(entities):
    expected_ranges = [
        (140, 162),  # ExtensionIndex
        (165, 177),  # NDArrayBackedExtensionIndex
        (175, 177),  # _from_join_target
        (172, 173),  # _get_engine_target
        (36, 112),  # _inherit_from_data
        (159, 162),  # _isnan
        (152, 156),  # _validate_fill_value
        (62, 63),  # cached
        (71, 79),  # fget
        (81, 82),  # fset
        (115, 137),  # inherit_names
        (96, 106),  # method
        (130, 135),  # wrapper
    ]
    for e, (expected_start, expected_end) in zip(entities, expected_ranges):
        assert (e.line_start, e.line_end) == (expected_start, expected_end), (
            f"Expected lines ({expected_start}, {expected_end}), got ({e.line_start}, {e.line_end})"
        )


def test_get_entities_from_file_py_signatures(entities):
    expected_signatures = [
        "class ExtensionIndex:",
        "class NDArrayBackedExtensionIndex:",
        "def _from_join_target(self, result: np.ndarray)",
        "def _get_engine_target(self)",
        "def _inherit_from_data(name: str, delegate: type, cache: bool, wrap: bool)",
        "def _isnan(self)",
        "def _validate_fill_value(self, value)",
        "def cached(self)",
        "def fget(self)",
        "def fset(self, value)",
        "def inherit_names(names: list[str], delegate: type, cache: bool, wrap: bool)",
        "def method(self)",
        "def wrapper(cls: type[_ExtensionIndexT])",
    ]
    for e, expected_signature in zip(entities, expected_signatures):
        assert e.signature == expected_signature, (
            f"Expected signature {expected_signature}, got {e.signature}"
        )


def test_get_entities_from_file_py_stubs(entities):
    expected_stubs = [
        'class ExtensionIndex(Index):\n    """\n    Index subclass for indexes backed by ExtensionArray.\n    """\n    _data: IntervalArray | NDArrayBackedExtensionArray\n\n    def _validate_fill_value(self, value):\n        """\n        Convert value to be insertable to underlying array.\n        """\n        """TODO: Implement this function"""\n        pass\n\n    @cache_readonly\n    def _isnan(self) ->npt.NDArray[np.bool_]:\n        """TODO: Implement this function"""\n        pass',
        'class NDArrayBackedExtensionIndex(ExtensionIndex):\n    """\n    Index subclass for indexes backed by NDArrayBackedExtensionArray.\n    """\n    _data: NDArrayBackedExtensionArray\n\n    def _get_engine_target(self) ->np.ndarray:\n        """TODO: Implement this function"""\n        pass\n\n    def _from_join_target(self, result: np.ndarray) ->ArrayLike:\n        """TODO: Implement this function"""\n        pass',
        'def _from_join_target(self, result: np.ndarray) ->ArrayLike:\n    """TODO: Implement this function"""\n    pass',
        'def _get_engine_target(self) ->np.ndarray:\n    """TODO: Implement this function"""\n    pass',
        'def _inherit_from_data(name: str, delegate: type, cache: bool=False, wrap:\n    bool=False):\n    """\n    Make an alias for a method of the underlying ExtensionArray.\n\n    Parameters\n    ----------\n    name : str\n        Name of an attribute the class should inherit from its EA parent.\n    delegate : class\n    cache : bool, default False\n        Whether to convert wrapped properties into cache_readonly\n    wrap : bool, default False\n        Whether to wrap the inherited result in an Index.\n\n    Returns\n    -------\n    attribute, method, property, or cache_readonly\n    """\n    """TODO: Implement this function"""\n    pass',
        'def _isnan(self) ->npt.NDArray[np.bool_]:\n    """TODO: Implement this function"""\n    pass',
        'def _validate_fill_value(self, value):\n    """\n    Convert value to be insertable to underlying array.\n    """\n    """TODO: Implement this function"""\n    pass',
        'def cached(self):\n    """TODO: Implement this function"""\n    pass',
        'def fget(self):\n    """TODO: Implement this function"""\n    pass',
        'def fset(self, value) ->None:\n    """TODO: Implement this function"""\n    pass',
        'def inherit_names(names: list[str], delegate: type, cache: bool=False, wrap:\n    bool=False) ->Callable[[type[_ExtensionIndexT]], type[_ExtensionIndexT]]:\n    """\n    Class decorator to pin attributes from an ExtensionArray to a Index subclass.\n\n    Parameters\n    ----------\n    names : List[str]\n    delegate : class\n    cache : bool, default False\n    wrap : bool, default False\n        Whether to wrap the inherited result in an Index.\n    """\n    """TODO: Implement this function"""\n    pass',
        'def method(self, *args, **kwargs):\n    """TODO: Implement this function"""\n    pass',
        'def wrapper(cls: type[_ExtensionIndexT]) ->type[_ExtensionIndexT]:\n    """TODO: Implement this function"""\n    pass',
    ]
    for e, expected_stub in zip(entities, expected_stubs):
        assert e.stub == expected_stub, (
            rf"Expected stub {expected_stub!r}, got {e.stub!r}"
        )
