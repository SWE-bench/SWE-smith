from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.ruby.base import RUBY_LANGUAGE, RubyProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Parser

# Mapping of Ruby binary operators to their flipped alternatives
FLIPPED_OPERATORS = {
    "+": "-",
    "-": "+",
    "*": "/",
    "/": "*",
    "%": "*",
    "**": "*",
    "==": "!=",
    "!=": "==",
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "&&": "||",
    "||": "&&",
    "and": "or",
    "or": "and",
    "=~": "!~",
    "!~": "=~",
    "..": "...",
    "...": "..",
}

# Operator groups for systematic changes
ARITHMETIC_OPS = ["+", "-", "*", "/", "%", "**"]
BITWISE_OPS = ["&", "|", "^", "<<", ">>"]
COMPARISON_OPS = ["==", "!=", "<", "<=", ">", ">="]
LOGICAL_OPS = ["&&", "||"]
KEYWORD_LOGICAL_OPS = ["and", "or"]
REGEX_OPS = ["=~", "!~"]

ALL_BINARY_OPS = set(
    ARITHMETIC_OPS
    + BITWISE_OPS
    + COMPARISON_OPS
    + LOGICAL_OPS
    + KEYWORD_LOGICAL_OPS
    + REGEX_OPS
)


def _find_operator_child(node):
    """Find the operator child node in a binary expression."""
    for child in node.children:
        text = child.text.decode("utf-8")
        if text in ALL_BINARY_OPS:
            return child
    return None


class OperationChangeModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.OPERATION_CHANGE.explanation
    name: str = CommonPMs.OPERATION_CHANGE.name
    conditions: list = CommonPMs.OPERATION_CHANGE.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Change operators within the same category in Ruby binary expressions."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modifications = []

        def collect(n):
            if n.type == "binary":
                op_node = _find_operator_child(n)
                if op_node and self.flip():
                    op = op_node.text.decode("utf-8")
                    new_op = self._get_alternative(op)
                    if new_op != op:
                        modifications.append((op_node, new_op))
            for child in n.children:
                collect(child)

        collect(tree.root_node)

        if not modifications:
            return None

        source_bytes = code_entity.src_code.encode("utf8")
        for op_node, new_op in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            source_bytes = (
                source_bytes[: op_node.start_byte]
                + new_op.encode("utf8")
                + source_bytes[op_node.end_byte :]
            )

        modified_code = source_bytes.decode("utf8")
        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _get_alternative(self, op: str) -> str:
        """Get an alternative operator from the same category."""
        if op in ARITHMETIC_OPS:
            return self.rand.choice(ARITHMETIC_OPS)
        elif op in BITWISE_OPS:
            return self.rand.choice(BITWISE_OPS)
        elif op in COMPARISON_OPS:
            return self.rand.choice(COMPARISON_OPS)
        elif op in LOGICAL_OPS:
            return self.rand.choice(LOGICAL_OPS)
        elif op in KEYWORD_LOGICAL_OPS:
            return self.rand.choice(KEYWORD_LOGICAL_OPS)
        elif op in REGEX_OPS:
            return self.rand.choice(REGEX_OPS)
        return op


class OperationFlipOperatorModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.OPERATION_FLIP_OPERATOR.explanation
    name: str = CommonPMs.OPERATION_FLIP_OPERATOR.name
    conditions: list = CommonPMs.OPERATION_FLIP_OPERATOR.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Flip operators to their opposites in Ruby binary expressions."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modifications = []

        def collect(n):
            if n.type == "binary":
                op_node = _find_operator_child(n)
                if op_node and self.flip():
                    op = op_node.text.decode("utf-8")
                    if op in FLIPPED_OPERATORS:
                        modifications.append((op_node, FLIPPED_OPERATORS[op]))
            elif n.type == "range":
                for child in n.children:
                    if child.text in (b"..", b"...") and self.flip():
                        op = child.text.decode("utf-8")
                        modifications.append((child, FLIPPED_OPERATORS[op]))
                        break
            for child in n.children:
                collect(child)

        collect(tree.root_node)

        if not modifications:
            return None

        source_bytes = code_entity.src_code.encode("utf8")
        for op_node, new_op in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            source_bytes = (
                source_bytes[: op_node.start_byte]
                + new_op.encode("utf8")
                + source_bytes[op_node.end_byte :]
            )

        modified_code = source_bytes.decode("utf8")
        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class OperationSwapOperandsModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.OPERATION_SWAP_OPERANDS.explanation
    name: str = CommonPMs.OPERATION_SWAP_OPERANDS.name
    conditions: list = CommonPMs.OPERATION_SWAP_OPERANDS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Swap left and right operands in Ruby binary expressions."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modifications = []

        def collect(n):
            collected = False
            if n.type == "binary" and len(n.children) >= 3:
                if self.flip():
                    left = n.children[0]
                    op_node = None
                    right = None
                    for i, child in enumerate(n.children[1:], 1):
                        text = child.text.decode("utf-8")
                        if text in ALL_BINARY_OPS:
                            op_node = child
                            if i + 1 < len(n.children):
                                right = n.children[i + 1]
                            break

                    if left and op_node and right:
                        modifications.append((n, left, op_node, right))
                        collected = True

            if not collected:
                for child in n.children:
                    collect(child)

        collect(tree.root_node)

        if not modifications:
            return None

        source_bytes = code_entity.src_code.encode("utf8")
        for expr, left, op, right in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            left_text = source_bytes[left.start_byte : left.end_byte]
            op_text = source_bytes[op.start_byte : op.end_byte]
            right_text = source_bytes[right.start_byte : right.end_byte]

            new_expr = right_text + b" " + op_text + b" " + left_text
            source_bytes = (
                source_bytes[: expr.start_byte]
                + new_expr
                + source_bytes[expr.end_byte :]
            )

        modified_code = source_bytes.decode("utf8")
        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class OperationBreakChainsModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.OPERATION_BREAK_CHAINS.explanation
    name: str = CommonPMs.OPERATION_BREAK_CHAINS.name
    conditions: list = CommonPMs.OPERATION_BREAK_CHAINS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Break chained binary expressions by removing an operand."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modifications = []

        def collect(n):
            if n.type == "binary" and self.flip():
                left = n.children[0] if n.children else None
                right = None
                for child in reversed(n.children):
                    text = child.text.decode("utf-8")
                    if text not in ALL_BINARY_OPS:
                        right = child
                        break

                # If left is a nested binary, replace outer with inner's left
                if left and left.type == "binary":
                    inner_left = left.children[0] if left.children else None
                    if inner_left:
                        modifications.append((n, inner_left))
                elif right and right.type == "binary":
                    inner_right = None
                    for child in reversed(right.children):
                        text = child.text.decode("utf-8")
                        if text not in ALL_BINARY_OPS:
                            inner_right = child
                            break
                    if inner_right:
                        modifications.append((n, inner_right))

            for child in n.children:
                collect(child)

        collect(tree.root_node)

        if not modifications:
            return None

        source_bytes = code_entity.src_code.encode("utf8")
        for expr, replacement in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            replacement_text = source_bytes[
                replacement.start_byte : replacement.end_byte
            ]
            source_bytes = (
                source_bytes[: expr.start_byte]
                + replacement_text
                + source_bytes[expr.end_byte :]
            )

        modified_code = source_bytes.decode("utf8")
        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class OperationChangeConstantsModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.explanation
    name: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.name
    conditions: list = CommonPMs.OPERATION_CHANGE_CONSTANTS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply off-by-one changes to numeric constants in Ruby binary expressions."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modifications = []

        def collect(n):
            if n.type == "binary":
                for child in n.children:
                    if child.type == "integer" and self.flip():
                        try:
                            value = int(child.text.decode("utf-8"))
                            new_value = value + self.rand.choice([-1, 1])
                            modifications.append((child, str(new_value)))
                        except ValueError:
                            pass
                    elif child.type == "float" and self.flip():
                        try:
                            value = float(child.text.decode("utf-8"))
                            delta = self.rand.choice([-0.1, 0.1, -1.0, 1.0])
                            new_value = value + delta
                            modifications.append((child, str(new_value)))
                        except ValueError:
                            pass
            for child in n.children:
                collect(child)

        collect(tree.root_node)

        if not modifications:
            return None

        source_bytes = code_entity.src_code.encode("utf8")
        for const_node, new_value in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            source_bytes = (
                source_bytes[: const_node.start_byte]
                + new_value.encode("utf8")
                + source_bytes[const_node.end_byte :]
            )

        modified_code = source_bytes.decode("utf8")
        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
