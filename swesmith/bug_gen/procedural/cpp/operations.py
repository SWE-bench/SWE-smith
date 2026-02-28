"""
Operation-related procedural modifications for C++ code.
"""

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.cpp.base import CppProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

CPP_LANGUAGE = Language(tscpp.language())

# Operator mappings for C++
FLIPPED_OPERATORS = {
    "==": "!=",
    "!=": "==",
    "<": ">=",
    "<=": ">",
    ">": "<=",
    ">=": "<",
    "&&": "||",
    "||": "&&",
    "&": "|",
    "|": "&",
    "<<": ">>",
    ">>": "<<",
}

# Aggressive operator transformations that are more likely to break tests
AGGRESSIVE_ARITHMETIC_TRANSFORMS = {
    "+": ["-", "*", "/"],  # Addition -> subtraction, multiplication, or division
    "-": ["+", "*", "/"],  # Subtraction -> addition, multiplication, or division
    "*": [
        "/",
        "-",
        "+",
    ],  # Multiplication -> division (can cause div by zero), subtraction, or addition
    "/": [
        "*",
        "+",
        "-",
    ],  # Division -> multiplication (can cause overflow), addition, or subtraction
    "%": ["/", "*", "-"],  # Modulo -> division, multiplication, or subtraction
}

ARITHMETIC_OPS = {"+", "-", "*", "/", "%"}
COMPARISON_OPS = {"<", ">", "<=", ">=", "==", "!="}
LOGICAL_OPS = {"&&", "||"}
BITWISE_OPS = {"&", "|", "^", "<<", ">>"}
SUPPORTED_BINARY_OPERATORS = ARITHMETIC_OPS | COMPARISON_OPS | LOGICAL_OPS | BITWISE_OPS


class OperationChangeModifier(CppProceduralModifier):
    """Randomly change operations in C++ code."""

    explanation: str = CommonPMs.OPERATION_CHANGE.explanation
    name: str = CommonPMs.OPERATION_CHANGE.name
    conditions: list = CommonPMs.OPERATION_CHANGE.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_operations(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_operations(self, code: str, node) -> str:
        """Change operations in the code with aggressive transformations."""
        candidates = []
        self._find_operations(node, candidates)

        if not candidates:
            return code

        # Select a random operation to change
        target = self.rand.choice(candidates)
        operator_text = code[target.start_byte : target.end_byte]

        # Choose a replacement with aggressive transformations
        replacement = None
        if operator_text in AGGRESSIVE_ARITHMETIC_TRANSFORMS:
            # Use aggressive arithmetic transformations (more likely to break)
            replacement = self.rand.choice(
                AGGRESSIVE_ARITHMETIC_TRANSFORMS[operator_text]
            )
        elif operator_text in FLIPPED_OPERATORS:
            replacement = FLIPPED_OPERATORS[operator_text]
        elif operator_text in BITWISE_OPS:
            replacement = self.rand.choice(list(BITWISE_OPS - {operator_text}))

        if replacement:
            return code[: target.start_byte] + replacement + code[target.end_byte :]

        return code

    def _find_operations(self, node, candidates):
        """Find all binary operators in the AST."""
        if node.type == "binary_expression":
            # In C++ tree-sitter, the operator is typically the 2nd child (after first operand)
            # We need to find the operator token
            for child in node.children:
                # Check if this is an operator by looking for patterns
                if child.type in SUPPORTED_BINARY_OPERATORS:
                    candidates.append(child)
        for child in node.children:
            self._find_operations(child, candidates)


class OperationFlipOperatorModifier(CppProceduralModifier):
    """Flip comparison, logical, and selected bitwise operators."""

    explanation: str = CommonPMs.OPERATION_FLIP_OPERATOR.explanation
    name: str = CommonPMs.OPERATION_FLIP_OPERATOR.name
    conditions: list = CommonPMs.OPERATION_FLIP_OPERATOR.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._flip_operators(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _flip_operators(self, code: str, node) -> str:
        """Flip operators that have a mapped opposite."""
        candidates = []
        self._find_flippable_operators(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)
        operator_text = code[target.start_byte : target.end_byte]

        if operator_text in FLIPPED_OPERATORS:
            replacement = FLIPPED_OPERATORS[operator_text]
            return code[: target.start_byte] + replacement + code[target.end_byte :]

        return code

    def _find_flippable_operators(self, node, candidates):
        """Find operators that can be flipped."""
        if node.type == "binary_expression":
            for child in node.children:
                if child.type in FLIPPED_OPERATORS:
                    candidates.append(child)
        for child in node.children:
            self._find_flippable_operators(child, candidates)


class OperationSwapOperandsModifier(CppProceduralModifier):
    """Swap operands in binary expressions (including non-commutative operations)."""

    explanation: str = CommonPMs.OPERATION_SWAP_OPERANDS.explanation
    name: str = CommonPMs.OPERATION_SWAP_OPERANDS.name
    conditions: list = CommonPMs.OPERATION_SWAP_OPERANDS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._swap_operands(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _swap_operands(self, code: str, node) -> str:
        """Swap operands in binary expressions."""
        candidates = []
        self._find_binary_expressions(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)
        if len(target.children) >= 3:
            left = target.children[0]
            right = target.children[2]

            left_text = code[left.start_byte : left.end_byte]
            right_text = code[right.start_byte : right.end_byte]

            # Reconstruct with swapped operands
            operator_node = target.children[1]
            operator_text = code[operator_node.start_byte : operator_node.end_byte]

            # Swap operands - this will break non-commutative operations like -, /, %, <, >, etc.
            return (
                code[: left.start_byte]
                + right_text
                + " "
                + operator_text
                + " "
                + left_text
                + code[right.end_byte :]
            )

        return code

    def _find_binary_expressions(self, node, candidates):
        """Find binary expressions."""
        if node.type == "binary_expression" and len(node.children) >= 3:
            candidates.append(node)
        for child in node.children:
            self._find_binary_expressions(child, candidates)


class OperationChangeConstantsModifier(CppProceduralModifier):
    """Change numeric constants."""

    explanation: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.explanation
    name: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.name
    conditions: list = CommonPMs.OPERATION_CHANGE_CONSTANTS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_constants(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_constants(self, code: str, node) -> str:
        """Change numeric constants with aggressive transformations."""
        candidates = []
        self._find_numeric_literals(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)
        original = code[target.start_byte : target.end_byte]

        try:
            if "." in original:
                value = float(original)
                # Aggressive changes: multiply/divide by large factors, or change to 0/1/-1
                transformations = [
                    value * 10,
                    value * 100,
                    value / 10,
                    value / 100,
                    value + 100.0,
                    value - 100.0,
                    0.0,
                    1.0,
                    -1.0,
                    value * -1,  # Negate
                ]
                new_value = self.rand.choice(transformations)
            else:
                value = int(original, 0)  # Handles hex, octal, etc.
                # Aggressive changes: multiply/divide by large factors, or change to 0/1/-1
                transformations = [
                    value * 10,
                    value * 100,
                    value // 10 if value != 0 else 0,
                    value // 100 if value != 0 else 0,
                    value + 100,
                    value - 100,
                    0,
                    1,
                    -1,
                    value * -1,  # Negate
                    abs(value) + 1,  # Always positive + 1
                ]
                new_value = self.rand.choice(transformations)
                # Ensure we don't create invalid values
                if (
                    new_value < 0
                    and original.startswith("0x")
                    and "u" in original.lower()
                ):
                    # Unsigned hex, keep positive
                    new_value = abs(new_value)

            return code[: target.start_byte] + str(new_value) + code[target.end_byte :]
        except (ValueError, OverflowError, ZeroDivisionError):
            return code

    def _find_numeric_literals(self, node, candidates):
        """Find numeric literal nodes."""
        if node.type == "number_literal":
            candidates.append(node)
        for child in node.children:
            self._find_numeric_literals(child, candidates)


class OperationBreakChainsModifier(CppProceduralModifier):
    """Break function calls by removing the call (keeps callee, removes arguments).

    Note: The C++ implementation breaks function call chains (e.g., getValue() -> getValue),
    while the Python implementation breaks binary expression chains (e.g., a + b + c -> a + c).
    This difference is intentional as it targets common patterns in each language.
    """

    explanation: str = CommonPMs.OPERATION_BREAK_CHAINS.explanation
    name: str = CommonPMs.OPERATION_BREAK_CHAINS.name
    conditions: list = CommonPMs.OPERATION_BREAK_CHAINS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._break_chains(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _break_chains(self, code: str, node) -> str:
        """Break function call chains by removing one level of a call."""
        candidates = []
        self._find_all_function_calls(node, candidates)

        if not candidates:
            return code

        target = self.rand.choice(candidates)
        # Remove one function call from the chain
        # In C++ tree-sitter, call_expression structure: [callee, arguments]
        if len(target.children) >= 1:
            # Keep just the callee part (removes the function call and arguments)
            callee = target.children[0]
            return (
                code[: target.start_byte]
                + code[callee.start_byte : callee.end_byte]
                + code[target.end_byte :]
            )

        return code

    def _find_all_function_calls(self, node, candidates):
        """Find all function calls to break."""
        if node.type == "call_expression":
            candidates.append(node)
        for child in node.children:
            self._find_all_function_calls(child, candidates)
