"""
Operation-related procedural modifications for Java code.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty

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
BITWISE_OPS = {"&", "|", "^", "<<", ">>", ">>>"}
SUPPORTED_BINARY_OPERATORS = ARITHMETIC_OPS | COMPARISON_OPS | LOGICAL_OPS | BITWISE_OPS
INTEGER_LITERAL_TYPES = {
    "decimal_integer_literal",
    "hex_integer_literal",
    "octal_integer_literal",
    "binary_integer_literal",
}
FLOAT_LITERAL_TYPES = {"decimal_floating_point_literal", "hex_floating_point_literal"}
NUMERIC_LITERAL_TYPES = INTEGER_LITERAL_TYPES | FLOAT_LITERAL_TYPES


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
        target = self.rand.choice(candidates)
        operator_text = code[target.start_byte : target.end_byte]

        # Choose a replacement from the same category
        replacement = None
        if operator_text in ARITHMETIC_OPS:
            ops = list(ARITHMETIC_OPS - {operator_text})
            replacement = self.rand.choice(ops) if ops else None
        elif operator_text in COMPARISON_OPS:
            ops = list(COMPARISON_OPS - {operator_text})
            replacement = self.rand.choice(ops) if ops else None
        elif operator_text in LOGICAL_OPS:
            ops = list(LOGICAL_OPS - {operator_text})
            replacement = self.rand.choice(ops) if ops else None
        elif operator_text in BITWISE_OPS:
            ops = list(BITWISE_OPS - {operator_text})
            replacement = self.rand.choice(ops) if ops else None

        if replacement:
            return code[: target.start_byte] + replacement + code[target.end_byte :]

        return code

    def _find_operations(self, node, candidates):
        """Find all binary operators in the AST (excluding string concatenations)."""
        if node.type == "binary_expression" and len(node.children) >= 3:
            operator_node = node.children[1]
            operator_text = (
                operator_node.text.decode("utf-8")
                if hasattr(operator_node, "text")
                else ""
            )

            if operator_text in SUPPORTED_BINARY_OPERATORS:
                if operator_text != "+" or not self._is_potential_string_concat(node):
                    candidates.append(operator_node)
        for child in node.children:
            self._find_operations(child, candidates)

    def _is_potential_string_concat(self, binary_node) -> bool:
        """Treat '+' as string concat when either side contains string literals."""
        if len(binary_node.children) < 3:
            return False
        left = binary_node.children[0]
        right = binary_node.children[2]
        return self._contains_string_literal(left) or self._contains_string_literal(
            right
        )

    def _contains_string_literal(self, node) -> bool:
        """Return True when subtree contains a string literal."""
        if node.type == "string_literal":
            return True
        return any(self._contains_string_literal(child) for child in node.children)


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

        target = self.rand.choice(candidates)
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

        target = self.rand.choice(candidates)
        original = code[target.start_byte : target.end_byte]

        replacement = self._mutate_numeric_literal(original, target.type)
        if replacement is None:
            return code
        return code[: target.start_byte] + replacement + code[target.end_byte :]

    def _mutate_numeric_literal(self, literal: str, literal_type: str) -> str | None:
        """Mutate Java numeric literals, including long suffixes and hex floats."""
        cleaned = literal.replace("_", "")

        try:
            if literal_type in INTEGER_LITERAL_TYPES:
                suffix = ""
                core = cleaned
                if core[-1] in {"l", "L"}:
                    suffix = core[-1]
                    core = core[:-1]
                value = int(core, 0)
                new_value = value + self.rand.choice([-1, 1, -10, 10])
                return f"{new_value}{suffix}"

            if literal_type in FLOAT_LITERAL_TYPES:
                suffix = ""
                core = cleaned
                if core[-1] in {"f", "F", "d", "D"}:
                    suffix = core[-1]
                    core = core[:-1]

                if (
                    literal_type == "hex_floating_point_literal"
                    or core.lower().startswith(("0x", "+0x", "-0x"))
                ):
                    value = float.fromhex(core)
                else:
                    value = float(core)

                new_value = value + self.rand.choice([-1.0, 1.0, -0.1, 0.1])
                return f"{new_value}{suffix}"
        except (ValueError, OverflowError, IndexError):
            return None

        return None

    def _find_numeric_literals(self, node, candidates):
        """Find numeric literal nodes."""
        if node.type in NUMERIC_LITERAL_TYPES:
            candidates.append(node)
        for child in node.children:
            self._find_numeric_literals(child, candidates)


class OperationBreakChainsModifier(JavaProceduralModifier):
    """Break method chains."""

    explanation: str = CommonPMs.OPERATION_BREAK_CHAINS.explanation
    name: str = CommonPMs.OPERATION_BREAK_CHAINS.name
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_FUNCTION_CALL]

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

        target = self.rand.choice(candidates)
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
