import ast
import astor
import re


PROMPT_KEYS = ["system", "demonstration", "instance"]


def extract_code_block(text: str) -> str:
    pattern = r"```(?:\w+)?\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def get_function_signature(node):
    """Generate the function signature as a string."""
    args = [ast.unparse(arg) for arg in node.args.args]  # For Python 3.9+
    args_str = ", ".join(args)
    return f"def {node.name}({args_str})"


def strip_function_body(source_code):
    tree = ast.parse(source_code)

    class FunctionBodyStripper(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            # Keep the original arguments and decorator list
            new_node = ast.FunctionDef(
                name=node.name,
                args=node.args,
                body=[],  # Empty body initially
                decorator_list=node.decorator_list,
                returns=node.returns,
                type_params=getattr(node, "type_params", None),  # For Python 3.12+
            )

            # Add docstring if it exists
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Str)
            ):
                new_node.body.append(node.body[0])

            # Add a comment indicating to implement this function
            new_node.body.append(ast.Expr(ast.Str("TODO: Implement this function")))

            # Add a 'pass' statement after the docstring
            new_node.body.append(ast.Pass())

            return new_node

    stripped_tree = FunctionBodyStripper().visit(tree)
    ast.fix_missing_locations(stripped_tree)

    return astor.to_source(stripped_tree)
