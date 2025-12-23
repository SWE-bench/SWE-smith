import tree_sitter_rust as tsrs

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.rust.base import RustProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Language, Parser

RUST_LANGUAGE = Language(tsrs.language())


class ControlIfElseInvertModifier(RustProceduralModifier):
    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = 5

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply if-else inversion to the Rust code."""
        if not self.flip():
            return None

        parser = Parser(RUST_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        changed = False

        for _ in range(self.max_attempts):
            modified_code = self._invert_if_else_statements(
                code_entity.src_code, tree.root_node
            )

            if modified_code != code_entity.src_code:
                changed = True
                break

        if not changed:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _invert_if_else_statements(self, source_code: str, node) -> str:
        """Recursively find and invert if-else statements by swapping the bodies."""
        modifications = []

        def collect_if_statements(n):
            if n.type == "if_expression":
                if_condition = None
                if_body = None
                else_clause = None
                else_body = None

                for i, child in enumerate(n.children):
                    if child.type == "if":
                        continue
                    elif if_condition is None and child.type in [
                        "binary_expression",
                        "identifier",
                        "call_expression",
                        "field_expression",
                        "unary_expression",
                    ]:
                        if_condition = child
                    elif child.type == "block" and if_body is None:
                        if_body = child
                    elif child.type == "else_clause":
                        else_clause = child
                        for else_child in child.children:
                            if else_child.type == "block":
                                else_body = else_child
                                break
                        break

                if (
                    if_condition
                    and if_body
                    and else_clause
                    and else_body
                    and self.flip()
                ):
                    modifications.append((n, if_condition, if_body, else_body))

            for child in n.children:
                collect_if_statements(child)

        collect_if_statements(node)

        if not modifications:
            return source_code

        modified_source = source_code
        for if_node, condition, if_body, else_body in reversed(modifications):
            if_start = if_node.start_byte
            if_body_start = if_body.start_byte

            prefix = source_code[if_start:if_body_start].strip()

            if_body_text = source_code[if_body.start_byte : if_body.end_byte]
            else_body_text = source_code[else_body.start_byte : else_body.end_byte]

            new_if_else = f"{prefix} {else_body_text} else {if_body_text}"

            start_byte = if_node.start_byte
            end_byte = if_node.end_byte

            modified_source = (
                modified_source[:start_byte] + new_if_else + modified_source[end_byte:]
            )

        return modified_source


class ControlShuffleLinesModifier(RustProceduralModifier):
    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions
    max_complexity: int = 10

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply line shuffling to the Rust function body."""
        parser = Parser(RUST_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._shuffle_function_statements(
            code_entity.src_code, tree.root_node
        )

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _shuffle_function_statements(self, source_code: str, node) -> str:
        """Recursively find function declarations and shuffle their statements."""
        modifications = []

        def collect_function_declarations(n):
            if n.type == "function_item":
                body_block = None
                for child in n.children:
                    if child.type == "block":
                        body_block = child
                        break

                if body_block:
                    statements = []
                    for child in body_block.children:
                        if child.type not in ["{", "}"]:
                            statements.append(child)

                    if len(statements) >= 2:
                        modifications.append((body_block, statements))

            for child in n.children:
                collect_function_declarations(child)

        collect_function_declarations(node)

        if not modifications:
            return source_code

        modified_source = source_code
        for body_block, statements in reversed(modifications):
            shuffled_indices = list(range(len(statements)))
            self.rand.shuffle(shuffled_indices)

            if shuffled_indices == list(range(len(statements))):
                if len(statements) >= 2:
                    shuffled_indices[0], shuffled_indices[1] = (
                        shuffled_indices[1],
                        shuffled_indices[0],
                    )

            statement_texts = []
            for stmt in statements:
                stmt_text = source_code[stmt.start_byte : stmt.end_byte]
                statement_texts.append(stmt_text)

            shuffled_texts = [statement_texts[i] for i in shuffled_indices]

            first_stmt_start = statements[0].start_byte
            last_stmt_end = statements[-1].end_byte

            line_start = source_code.rfind("\n", 0, first_stmt_start) + 1
            indent = source_code[line_start:first_stmt_start]

            new_content = ("\n" + indent).join(shuffled_texts)

            modified_source = (
                modified_source[:first_stmt_start]
                + new_content
                + modified_source[last_stmt_end:]
            )

        return modified_source
