import libcst
import pytest
from swesmith.bug_gen.procedural.classes import (
    ClassRemoveBasesModifier,
    ClassShuffleMethodsModifier,
    ClassRemoveFuncsModifier,
)


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Remove single base
        (
            """
class Foo(Bar):
    pass
""",
            [
                "class Foo():\n    pass",
            ],
        ),
        # Remove one of multiple bases
        (
            """
class Foo(Bar, Baz):
    pass
""",
            [
                "class Foo(Bar):\n    pass",
                "class Foo(Baz):\n    pass",
                "class Foo():\n    pass",
            ],
        ),
    ],
)
def test_class_remove_bases(src, expected_variants):
    module = libcst.parse_module(src)
    modifier = ClassRemoveBasesModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert any(
        modified.code.strip() == variant.strip() for variant in expected_variants
    )


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Shuffle two methods
        (
            """class Foo:
    def a(self):
        pass
    def b(self):
        pass
""",
            [
                "class Foo:\n    def a(self):\n        pass\n    def b(self):\n        pass",
                "class Foo:\n    def b(self):\n        pass\n    def a(self):\n        pass",
            ],
        ),
        # No shuffle if only one method
        (
            """class Bar:
    def a(self):
        pass
""",
            [
                "class Bar:\n    def a(self):\n        pass",
            ],
        ),
    ],
)
def test_class_shuffle_methods(src, expected_variants):
    module = libcst.parse_module(src)
    modifier = ClassShuffleMethodsModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert any(
        modified.code.strip() == variant.strip() for variant in expected_variants
    )


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Remove a method and its reference
        (
            """class Foo:
    def a(self):
        pass
    def b(self):
        self.a()
        return 1
""",
            [
                # Only b remains, and self.a() is replaced with None
                "class Foo:\n    def b(self):\n        None\n        return 1\n",
                # Only a remains
                "class Foo:\n    def a(self):\n        pass\n",
                # Both removed
                "class Foo:\n    pass\n",
            ],
        ),
        # Remove both methods
        (
            """class Bar:
    def a(self):
        pass
    def b(self):
        pass
""",
            [
                "class Bar:\n    pass\n",
                "class Bar:\n\n",
            ],
        ),
        # No removal if no methods
        (
            """class Baz:
    x = 1
""",
            [
                "class Baz:\n    x = 1\n",
            ],
        ),
    ],
)
def test_class_remove_funcs(src, expected_variants):
    module = libcst.parse_module(src)
    modifier = ClassRemoveFuncsModifier(likelihood=1.0, seed=42)
    modified = module.visit(modifier)
    assert any(
        modified.code.strip() == variant.strip() for variant in expected_variants
    )
