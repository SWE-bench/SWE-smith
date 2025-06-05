import ast

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


def test_get_entities_from_file_py(test_file_py):
    entities = []
    get_entities_from_file_py(entities, test_file_py)
    entities = sorted(entities, key=lambda e: e.name)
    assert len(entities) == 13
    assert all([e.ext == "py" for e in entities]), (
        "All entities should have the extension 'py'"
    )
    assert all([e.file_path == str(test_file_py) for e in entities]), (
        "All entities should have the correct file path"
    )

    for e, (name, line_start, line_end, signature, stub) in zip(
        entities,
        [
            (
                "ExtensionIndex",
                140,
                162,
                "class ExtensionIndex:",
                'class ExtensionIndex(Index):\n    """\n    Index subclass for indexes backed by ExtensionArray.\n    """\n    _data: IntervalArray | NDArrayBackedExtensionArray\n\n    def _validate_fill_value(self, value):\n        """\n        Convert value to be insertable to underlying array.\n        """\n        """TODO: Implement this function"""\n        pass\n\n    @cache_readonly\n    def _isnan(self) ->npt.NDArray[np.bool_]:\n        """TODO: Implement this function"""\n        pass',
            ),
            (
                "NDArrayBackedExtensionIndex",
                165,
                177,
                "class NDArrayBackedExtensionIndex:",
                'class NDArrayBackedExtensionIndex(ExtensionIndex):\n    """\n    Index subclass for indexes backed by NDArrayBackedExtensionArray.\n    """\n    _data: NDArrayBackedExtensionArray\n\n    def _get_engine_target(self) ->np.ndarray:\n        """TODO: Implement this function"""\n        pass\n\n    def _from_join_target(self, result: np.ndarray) ->ArrayLike:\n        """TODO: Implement this function"""\n        pass',
            ),
            (
                "_from_join_target",
                175,
                177,
                "def _from_join_target(self, result: np.ndarray)",
                'def _from_join_target(self, result: np.ndarray) ->ArrayLike:\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "_get_engine_target",
                172,
                173,
                "def _get_engine_target(self)",
                'def _get_engine_target(self) ->np.ndarray:\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "_inherit_from_data",
                36,
                112,
                "def _inherit_from_data(name: str, delegate: type, cache: bool, wrap: bool)",
                'def _inherit_from_data(name: str, delegate: type, cache: bool=False, wrap:\n    bool=False):\n    """\n    Make an alias for a method of the underlying ExtensionArray.\n\n    Parameters\n    ----------\n    name : str\n        Name of an attribute the class should inherit from its EA parent.\n    delegate : class\n    cache : bool, default False\n        Whether to convert wrapped properties into cache_readonly\n    wrap : bool, default False\n        Whether to wrap the inherited result in an Index.\n\n    Returns\n    -------\n    attribute, method, property, or cache_readonly\n    """\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "_isnan",
                159,
                162,
                "def _isnan(self)",
                'def _isnan(self) ->npt.NDArray[np.bool_]:\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "_validate_fill_value",
                152,
                156,
                "def _validate_fill_value(self, value)",
                'def _validate_fill_value(self, value):\n    """\n    Convert value to be insertable to underlying array.\n    """\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "cached",
                62,
                63,
                "def cached(self)",
                'def cached(self):\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "fget",
                71,
                79,
                "def fget(self)",
                'def fget(self):\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "fset",
                81,
                82,
                "def fset(self, value)",
                'def fset(self, value) ->None:\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "inherit_names",
                115,
                137,
                "def inherit_names(names: list[str], delegate: type, cache: bool, wrap: bool)",
                'def inherit_names(names: list[str], delegate: type, cache: bool=False, wrap:\n    bool=False) ->Callable[[type[_ExtensionIndexT]], type[_ExtensionIndexT]]:\n    """\n    Class decorator to pin attributes from an ExtensionArray to a Index subclass.\n\n    Parameters\n    ----------\n    names : List[str]\n    delegate : class\n    cache : bool, default False\n    wrap : bool, default False\n        Whether to wrap the inherited result in an Index.\n    """\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "method",
                96,
                106,
                "def method(self)",
                'def method(self, *args, **kwargs):\n    """TODO: Implement this function"""\n    pass',
            ),
            (
                "wrapper",
                130,
                135,
                "def wrapper(cls: type[_ExtensionIndexT])",
                'def wrapper(cls: type[_ExtensionIndexT]) ->type[_ExtensionIndexT]:\n    """TODO: Implement this function"""\n    pass',
            ),
        ],
    ):
        assert e.name == name, f"Expected name {name}, got {e.name}"
        assert (e.line_start, e.line_end) == (line_start, line_end), (
            f"Expected lines ({line_start}, {line_end}), got ({e.line_start}, {e.line_end})"
        )
        assert e.signature == signature, (
            f"Expected signature {signature}, got {e.signature}"
        )
        assert e.stub == stub, rf"Expected stub {stub!r}, got {e.stub!r}"
