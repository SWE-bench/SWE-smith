import ast

from swesmith.utils import CodeEntity


def filter_all(code_entity: CodeEntity) -> bool:
    return True


def filter_functions(code_entity: CodeEntity) -> bool:
    """
    Check whether node is a function definition
    """
    return isinstance(code_entity.node, ast.FunctionDef)


def filter_classes(code_entity: CodeEntity) -> bool:
    """
    Check whether node is a class definition
    """
    return isinstance(code_entity.node, ast.ClassDef)


def filter_classes_has_parents(code_entity: CodeEntity) -> bool:
    """
    Check whether node is a class definition with parents
    """
    return isinstance(code_entity.node, ast.ClassDef) and code_entity.node.bases


def filter_classes_has_decorators(code_entity: CodeEntity) -> bool:
    """
    Check whether node is a class definition with decorators
    """
    return (
        isinstance(code_entity.node, ast.ClassDef) and code_entity.node.decorator_list
    )


def filter_loops(code_entity: CodeEntity) -> bool:
    """
    Identify functions that have loops in them
    """
    node = code_entity.node
    return any(
        isinstance(n, ast.For) or isinstance(n, ast.While) for n in ast.walk(node)
    )


def filter_list_indexing(code_entity: CodeEntity) -> bool:
    """
    Identify functions that have list indexing in them
    """
    node = code_entity.node
    return any(isinstance(n, ast.Subscript) for n in ast.walk(node))


def filter_conditionals(code_entity: CodeEntity) -> bool:
    """
    Identify functions that have conditionals in them
    """
    node = code_entity.node
    return any(isinstance(n, ast.If) for n in ast.walk(node))


def filter_function_calls(code_entity: CodeEntity) -> bool:
    """
    Identify functions that have function calls in them
    """
    node = code_entity.node
    return any(isinstance(n, ast.Call) for n in ast.walk(node))


def filter_return_statements(code_entity: CodeEntity) -> bool:
    """
    Identify functions that have return statements
    """
    node = code_entity.node
    return any(isinstance(n, ast.Return) for n in ast.walk(node))


def filter_exceptions(code_entity: CodeEntity) -> bool:
    """
    Identify functions that handle exceptions (try/except blocks)
    """
    node = code_entity.node
    return any(isinstance(n, ast.Try) for n in ast.walk(node))


def filter_list_comprehensions(code_entity: CodeEntity) -> bool:
    """
    Identify functions that use list comprehensions
    """
    node = code_entity.node
    return any(isinstance(n, ast.ListComp) for n in ast.walk(node))


def filter_imports(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain import statements
    """
    node = code_entity.node
    return any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(node))


def filter_assignments(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain assignment statements
    """
    node = code_entity.node
    return any(isinstance(n, ast.Assign) for n in ast.walk(node))


def filter_class_definitions(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain class definitions
    """
    node = code_entity.node
    return any(isinstance(n, ast.ClassDef) for n in ast.walk(node))


def filter_lambda_functions(code_entity: CodeEntity) -> bool:
    """
    Identify functions that use lambda expressions
    """
    node = code_entity.node
    return any(isinstance(n, ast.Lambda) for n in ast.walk(node))


def filter_arithmetic_operations(code_entity: CodeEntity) -> bool:
    """
    Identify functions that perform arithmetic operations
    """
    node = code_entity.node
    return any(isinstance(n, (ast.BinOp, ast.UnaryOp)) for n in ast.walk(node))


def filter_decorator_usage(code_entity: CodeEntity) -> bool:
    """
    Identify functions that use decorators
    """
    node = code_entity.node
    return any(
        isinstance(n, ast.FunctionDef) and n.decorator_list for n in ast.walk(node)
    )


def filter_wrappers(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain try or with blocks
    """
    node = code_entity.node
    return any(isinstance(n, (ast.Try, ast.With)) for n in ast.walk(node))


def filter_off_by_one(code_entity: CodeEntity) -> bool:
    """
    Identify functions that may have off-by-one errors
    """
    node = code_entity.node
    return any(
        isinstance(n, ast.Compare)
        and len(n.ops) == 1
        and n.ops[0].__class__.__name__
        in [
            "Lt",
            "Gt",
            "LtE",
            "GtE",
        ]
        for n in ast.walk(node)
    )


def filter_if_else(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain if-else statements
    """
    node = code_entity.node
    return any(isinstance(n, ast.If) and n.orelse for n in ast.walk(node))


def filter_operations_binary(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain binary operations
    """
    node = code_entity.node
    return any(isinstance(n, ast.BinOp) for n in ast.walk(node))


def filter_operations_bool(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain boolean operations
    """
    node = code_entity.node
    return any(isinstance(n, ast.BoolOp) for n in ast.walk(node))


def filter_operations_unary(code_entity: CodeEntity) -> bool:
    """
    Identify functions that contain unary operations
    """
    node = code_entity.node
    return any(isinstance(n, ast.UnaryOp) for n in ast.walk(node))


def calc_simple_complexity(code_entity: CodeEntity) -> int:
    """
    Simple way of calculating the complexity of a function.
    Complexity starts at 1 and increases for each decision point:
    - if/elif/else statements
    - for/while loops
    - and/or operators
    - except clauses
    - boolean operators
    """
    node = code_entity.node
    complexity = 1  # Base complexity

    for n in ast.walk(node):
        # Decision points
        if isinstance(n, (ast.If, ast.While, ast.For)):
            complexity += 1
        # Boolean operators
        elif isinstance(n, ast.BoolOp):
            complexity += len(n.values) - 1
        # Exception handling
        elif isinstance(n, ast.Try):
            complexity += len(n.handlers)
        # Comparison operators
        elif isinstance(n, ast.Compare):
            complexity += len(n.ops)

    return complexity


def filter_min_simple_complexity(code_entity: CodeEntity, threshold: int = 10) -> bool:
    return calc_simple_complexity(code_entity) >= threshold


def filter_max_simple_complexity(code_entity: CodeEntity, threshold: int = 10) -> bool:
    return calc_simple_complexity(code_entity) <= threshold
