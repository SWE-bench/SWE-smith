"""
Operation-related procedural modifications for Java code.
"""

import random

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

JAVA_LANGUAGE = Language(tsjava.language())

# Operator mappings for Java
FLIPPED_OPERATORS = {
    "==": "!=",
    "!=": "==",
    "<": ">=",
    "<=": ">",
    ">": "<=",
    ">=": "<",
    "&&": "||",
    "||": "&&",
}

ARITHMETIC_OPS = {"+", "-", "*", "/", "%"}
COMPARISON_OPS = {"<", ">", "<=", ">=", "==", "!="}
LOGICAL_OPS = {"&&", "||"}


class OperationChangeModifier(JavaProceduralModifier):
    """Randomly change operations in Java code."""

    explanation: str = CommonPMs.OPERATION_CHANGE.explanation
    name: str = CommonPMs.OPERATION_CHANGE.name
    conditions: list = CommonPMs.OPERATION_CHANGE.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_operations(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_operations(self, code: str, node) -> str:
        """Change random operations in the code."""
        candidates = []
        self._find_operations(node, candidates)

        if not candidates:
            return code

        # Select a random operation to change
        target = random.choice(candidates)
        operator_text = code[target.start_byte : target.end_byte]

        # Choose a replacement from the same category
        replacement = None
        if operator_text in ARITHMETIC_OPS:
            ops = list(ARITHMETIC_OPS - {operator_text})
            replacement = random.choice(ops) if ops else None
        elif operator_text in COMPARISON_OPS:
            ops = list(COMPARISON_OPS - {operator_text})
            replacement = random.choice(ops) if ops else None
        elif operator_text in LOGICAL_OPS:
            ops = list(LOGICAL_OPS - {operator_text})
            replacement = random.choice(ops) if ops else None

        if replacement:
            return code[: target.start_byte] + replacement + code[target.end_byte :]

        return code

    def _find_operations(self, node, candidates):
        """Find all binary operators in the AST (excluding string concatenations)."""
        if node.type == "binary_expression":
            # Check if this is a string concatenation
            has_string_literal = any(
                child.type == "string_literal" for child in node.children
            )
            
            # Find the operator child
            for child in node.children:
                # Skip + operator if it involves strings (string concatenation)
                if child.type == "+" and has_string_literal:
                    continue
                if child.type in ["+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!=", "&&", "||"]:
                    # Only add arithmetic ops if no string literals involved
                    if child.type in ["+", "-", "*", "/", "%"] and has_string_literal:
                        continue
                    candidates.append(child)
        for child in node.children:
            self._find_operations(child, candidates)


class OperationFlipOperatorModifier(JavaProceduralModifier):
    """Flip comparison and logical operators."""

    explanation: str = CommonPMs.OPERATION_FLIP_OPERATOR.explanation
    name: str = CommonPMs.OPERATION_FLIP_OPERATOR.name
    conditions: list = CommonPMs.OPERATION_FLIP_OPERATOR.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._flip_operators(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _flip_operators(self, code: str, node) -> str:
        """Flip comparison/logical operators."""
        candidates = []
        self._find_flippable_operators(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        operator_text = code[target.start_byte : target.end_byte]

        if operator_text in FLIPPED_OPERATORS:
            replacement = FLIPPED_OPERATORS[operator_text]
            return code[: target.start_byte] + replacement + code[target.end_byte :]

        return code

    def _find_flippable_operators(self, node, candidates):
        """Find operators that can be flipped."""
        if node.type == "binary_expression":
            for child in node.children:
                text = child.text.decode("utf-8") if hasattr(child, "text") else ""
                if text in FLIPPED_OPERATORS:
                    candidates.append(child)
        for child in node.children:
            self._find_flippable_operators(child, candidates)


class OperationSwapOperandsModifier(JavaProceduralModifier):
    """Swap operands in commutative operations."""

    explanation: str = CommonPMs.OPERATION_SWAP_OPERANDS.explanation
    name: str = CommonPMs.OPERATION_SWAP_OPERANDS.name
    conditions: list = CommonPMs.OPERATION_SWAP_OPERANDS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._swap_operands(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
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

        target = random.choice(candidates)
        if len(target.children) >= 3:
            left = target.children[0]
            right = target.children[2]

            left_text = code[left.start_byte : left.end_byte]
            right_text = code[right.start_byte : right.end_byte]

            # Reconstruct with swapped operands
            operator_node = target.children[1]
            operator_text = code[operator_node.start_byte : operator_node.end_byte]

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


class OperationChangeConstantsModifier(JavaProceduralModifier):
    """Change numeric constants."""

    explanation: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.explanation
    name: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.name
    conditions: list = CommonPMs.OPERATION_CHANGE_CONSTANTS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_constants(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_constants(self, code: str, node) -> str:
        """Change numeric constants."""
        candidates = []
        self._find_numeric_literals(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        original = code[target.start_byte : target.end_byte]

        try:
            if "." in original:
                value = float(original)
                new_value = value + random.choice([-1.0, 1.0, -0.1, 0.1])
            else:
                value = int(original, 0)  # Handles hex, octal, etc.
                new_value = value + random.choice([-1, 1, -10, 10])

            return code[: target.start_byte] + str(new_value) + code[target.end_byte :]
        except (ValueError, OverflowError):
            return code

    def _find_numeric_literals(self, node, candidates):
        """Find numeric literal nodes."""
        if node.type in ["decimal_integer_literal", "hex_integer_literal", "octal_integer_literal", 
                         "binary_integer_literal", "decimal_floating_point_literal", "hex_floating_point_literal"]:
            candidates.append(node)
        for child in node.children:
            self._find_numeric_literals(child, candidates)


class OperationBreakChainsModifier(JavaProceduralModifier):
    """Break method chains."""

    explanation: str = CommonPMs.OPERATION_BREAK_CHAINS.explanation
    name: str = CommonPMs.OPERATION_BREAK_CHAINS.name
    conditions: list = CommonPMs.OPERATION_BREAK_CHAINS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._break_chains(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _break_chains(self, code: str, node) -> str:
        """Break method call chains."""
        candidates = []
        self._find_method_chains(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        # Remove one method call from the chain
        if len(target.children) >= 2:
            # Keep just the first part
            first_part = target.children[0]
            return (
                code[: target.start_byte]
                + code[first_part.start_byte : first_part.end_byte]
                + code[target.end_byte :]
            )

        return code

    def _find_method_chains(self, node, candidates):
        """Find chained method calls."""
        if node.type == "method_invocation":
            # Check if object is also a method invocation (chained)
            if node.children and node.children[0].type == "method_invocation":
                candidates.append(node)
        for child in node.children:
            self._find_method_chains(child, candidates)

