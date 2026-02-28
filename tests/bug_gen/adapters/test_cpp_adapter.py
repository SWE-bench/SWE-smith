"""Tests for the C++ adapter's tag analysis and complexity calculation."""

from swesmith.bug_gen.adapters.cpp import get_entities_from_file_cpp
from swesmith.constants import CodeProperty


class TestCPlusPlusEntityTags:
    """Test that CPlusPlusEntity correctly tags code properties."""

    def test_function_tag(self, tmp_path):
        """Test that functions are tagged with IS_FUNCTION."""
        src = """int foo() {
    return 42;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.IS_FUNCTION in entities[0]._tags

    def test_loop_tags(self, tmp_path):
        """Test that loop constructs are tagged with HAS_LOOP."""
        test_cases = [
            ("for loop", "void foo() { for (int i = 0; i < 10; i++) {} }"),
            ("while loop", "void foo() { while (true) {} }"),
            ("do-while loop", "void foo() { do {} while (true); }"),
            ("range-based for", "void foo() { for (auto& x : vec) {} }"),
        ]

        for name, src in test_cases:
            test_file = tmp_path / f"test_{name.replace(' ', '_')}.cpp"
            test_file.write_text(src, encoding="utf-8")

            entities = []
            get_entities_from_file_cpp(entities, str(test_file))
            assert len(entities) == 1, f"Failed for {name}"
            assert CodeProperty.HAS_LOOP in entities[0]._tags, (
                f"Expected HAS_LOOP for {name}"
            )

    def test_if_statement_tag(self, tmp_path):
        """Test that if statements are tagged with HAS_IF."""
        src = """void foo(int x) {
    if (x > 0) {
        return;
    }
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_IF in entities[0]._tags

    def test_if_else_tag(self, tmp_path):
        """Test that if-else statements are tagged with HAS_IF_ELSE."""
        src = """void foo(int x) {
    if (x > 0) {
        return;
    } else {
        return;
    }
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_IF in entities[0]._tags
        assert CodeProperty.HAS_IF_ELSE in entities[0]._tags

    def test_switch_tag(self, tmp_path):
        """Test that switch statements are tagged with HAS_SWITCH."""
        src = """void foo(int x) {
    switch (x) {
        case 1: break;
        default: break;
    }
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_SWITCH in entities[0]._tags

    def test_binary_op_tag(self, tmp_path):
        """Test that binary operations are tagged with HAS_BINARY_OP."""
        src = """int foo(int a, int b) {
    return a + b;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_BINARY_OP in entities[0]._tags

    def test_arithmetic_tag(self, tmp_path):
        """Test that arithmetic operations are tagged with HAS_ARITHMETIC."""
        test_cases = [
            ("plus", "int foo() { return 1 + 2; }"),
            ("minus", "int foo() { return 1 - 2; }"),
            ("times", "int foo() { return 1 * 2; }"),
            ("divide", "int foo() { return 1 / 2; }"),
            ("modulo", "int foo() { return 1 % 2; }"),
        ]

        for op_name, src in test_cases:
            test_file = tmp_path / f"test_{op_name}.cpp"
            test_file.write_text(src, encoding="utf-8")

            entities = []
            get_entities_from_file_cpp(entities, str(test_file))
            assert len(entities) == 1, f"Failed for operator {op_name}"
            assert CodeProperty.HAS_ARITHMETIC in entities[0]._tags, (
                f"Expected HAS_ARITHMETIC for operator {op_name}"
            )

    def test_comparison_off_by_one_tag(self, tmp_path):
        """Test that comparison operators are tagged with HAS_OFF_BY_ONE."""
        test_cases = [
            ("<", "bool foo() { return 1 < 2; }"),
            (">", "bool foo() { return 1 > 2; }"),
            ("<=", "bool foo() { return 1 <= 2; }"),
            (">=", "bool foo() { return 1 >= 2; }"),
        ]

        for op, src in test_cases:
            test_file = (
                tmp_path
                / f"test_{op.replace('<', 'lt').replace('>', 'gt').replace('=', 'eq')}.cpp"
            )
            test_file.write_text(src, encoding="utf-8")

            entities = []
            get_entities_from_file_cpp(entities, str(test_file))
            assert len(entities) == 1, f"Failed for operator {op}"
            assert CodeProperty.HAS_OFF_BY_ONE in entities[0]._tags, (
                f"Expected HAS_OFF_BY_ONE for operator {op}"
            )

    def test_boolean_op_tag(self, tmp_path):
        """Test that boolean operators are tagged with HAS_BOOL_OP."""
        test_cases = [
            ("&&", "bool foo() { return true && false; }"),
            ("||", "bool foo() { return true || false; }"),
        ]

        for op, src in test_cases:
            test_file = tmp_path / f"test_{'and' if op == '&&' else 'or'}.cpp"
            test_file.write_text(src, encoding="utf-8")

            entities = []
            get_entities_from_file_cpp(entities, str(test_file))
            assert len(entities) == 1, f"Failed for operator {op}"
            assert CodeProperty.HAS_BOOL_OP in entities[0]._tags, (
                f"Expected HAS_BOOL_OP for operator {op}"
            )

    def test_unary_op_tag(self, tmp_path):
        """Test that unary operations are tagged with HAS_UNARY_OP."""
        src = """int foo(int x) {
    return -x;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_UNARY_OP in entities[0]._tags

    def test_function_call_tag(self, tmp_path):
        """Test that function calls are tagged with HAS_FUNCTION_CALL."""
        src = """void foo() {
    bar();
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_FUNCTION_CALL in entities[0]._tags

    def test_return_tag(self, tmp_path):
        """Test that return statements are tagged with HAS_RETURN."""
        src = """int foo() {
    return 42;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_RETURN in entities[0]._tags

    def test_assignment_expression_tag(self, tmp_path):
        """Test that assignment expressions are tagged with HAS_ASSIGNMENT."""
        src = """void foo() {
    int x;
    x = 5;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_ASSIGNMENT in entities[0]._tags

    def test_init_declarator_assignment_tag(self, tmp_path):
        """Test that variable initialization is tagged with HAS_ASSIGNMENT."""
        src = """void foo() {
    int x = 5;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert CodeProperty.HAS_ASSIGNMENT in entities[0]._tags


class TestCPlusPlusEntityComplexity:
    """Test that CPlusPlusEntity correctly calculates cyclomatic complexity."""

    def test_simple_function_complexity(self, tmp_path):
        """Test that a simple function has complexity 1."""
        src = """int foo() {
    return 42;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert entities[0].complexity == 1

    def test_single_if_complexity(self, tmp_path):
        """Test that a function with one if has complexity 2."""
        src = """int foo(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert entities[0].complexity == 2

    def test_for_loop_complexity(self, tmp_path):
        """Test that a for loop adds to complexity."""
        src = """void foo() {
    for (int i = 0; i < 10; i++) {
        doSomething();
    }
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert entities[0].complexity == 2

    def test_while_loop_complexity(self, tmp_path):
        """Test that a while loop adds to complexity."""
        src = """void foo() {
    while (true) {
        doSomething();
    }
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert entities[0].complexity == 2

    def test_do_while_loop_complexity(self, tmp_path):
        """Test that a do-while loop adds to complexity."""
        src = """void foo() {
    do {
        doSomething();
    } while (true);
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert entities[0].complexity == 2

    def test_range_for_loop_complexity(self, tmp_path):
        """Test that a range-based for loop adds to complexity."""
        src = """void foo() {
    for (auto& x : vec) {
        doSomething();
    }
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        assert entities[0].complexity == 2

    def test_switch_case_complexity(self, tmp_path):
        """Test that switch cases add to complexity."""
        src = """int foo(int x) {
    switch (x) {
        case 1: return 1;
        case 2: return 2;
        case 3: return 3;
        default: return 0;
    }
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        # Base 1 + 4 case statements = 5
        assert entities[0].complexity == 5

    def test_nested_if_complexity(self, tmp_path):
        """Test that nested ifs add to complexity."""
        src = """int foo(int x, int y) {
    if (x > 0) {
        if (y > 0) {
            return 1;
        }
    }
    return 0;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        # Base 1 + 2 if statements = 3
        assert entities[0].complexity == 3

    def test_complex_function_complexity(self, tmp_path):
        """Test a complex function with multiple control structures."""
        src = """int foo(int x) {
    if (x > 0) {
        for (int i = 0; i < x; i++) {
            if (i % 2 == 0) {
                doSomething();
            }
        }
    } else {
        while (x < 0) {
            x++;
        }
    }
    return x;
}"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(src, encoding="utf-8")

        entities = []
        get_entities_from_file_cpp(entities, str(test_file))
        assert len(entities) == 1
        # Base 1 + if 1 + for 1 + if 1 + while 1 = 5
        assert entities[0].complexity == 5
