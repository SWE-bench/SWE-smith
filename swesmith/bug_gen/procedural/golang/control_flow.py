import tree_sitter_go as tsgo

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.golang.base import GolangProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Language, Parser

GO_LANGUAGE = Language(tsgo.language())


class ControlIfElseInvertModifier(GolangProceduralModifier):
    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = 5

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply if-else inversion to the Go code."""
        if not self.flip():
            return None

        # Parse the code
        parser = Parser(GO_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        changed = False

        for _ in range(self.max_attempts):
            # Find if-else statements to modify
            modified_code = self._invert_if_else_statements(
                code_entity.src_code, tree.root_node
            )

            if modified_code != code_entity.src_code:
                changed = True
                break

        if not changed:
            return None

        return BugRewrite(
            rewrite=modified_code,  # Fixed: was "rewritten" but should be "rewrite"
            explanation=self.explanation,
            strategy=self.name,  # Added: required parameter
        )

    def _invert_if_else_statements(self, source_code: str, node) -> str:
        """Recursively find and invert if-else statements by swapping the bodies."""
        modifications = []

        def collect_if_statements(n):
            if n.type == "if_statement":
                # Parse the if statement structure
                # Go if statement structure: if [condition] block [else block]
                if_condition = None
                if_body = None
                else_clause = None
                else_body = None

                for i, child in enumerate(n.children):
                    if child.type == "if":
                        continue  # Skip the "if" keyword
                    elif if_condition is None and child.type in [
                        "parenthesized_expression",
                        "binary_expression",
                        "identifier",
                        "short_var_declaration",
                    ]:
                        # This is the condition (could be complex with short var declaration)
                        # For short var declarations like "userDefault, ok := logging.Logs[DefaultLoggerName]; ok"
                        # we need to find the actual condition part
                        if child.type == "short_var_declaration":
                            # Look for the next non-semicolon child as the condition
                            for j in range(i + 1, len(n.children)):
                                next_child = n.children[j]
                                if next_child.type not in [";", "else", "block"]:
                                    if_condition = next_child
                                    break
                        else:
                            if_condition = child
                    elif child.type == "block" and if_body is None:
                        if_body = child  # First block is the if body
                    elif child.type == "else":
                        else_clause = child
                        # Find the else body (next block after else)
                        if (
                            i + 1 < len(n.children)
                            and n.children[i + 1].type == "block"
                        ):
                            else_body = n.children[i + 1]
                        break

                # Only modify if we have a complete if-else structure
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

        # Apply modifications from end to start to preserve byte offsets
        modified_source = source_code
        for if_node, condition, if_body, else_body in reversed(modifications):
            # For complex if statements with short var declarations, we need to preserve the entire prefix
            # Extract the complete if statement prefix (everything before the first block)
            if_start = if_node.start_byte
            if_body_start = if_body.start_byte

            # Extract the prefix (if + condition)
            prefix = source_code[if_start:if_body_start].strip()

            # Extract the body texts
            if_body_text = source_code[if_body.start_byte : if_body.end_byte]
            else_body_text = source_code[else_body.start_byte : else_body.end_byte]

            # Create the new if-else statement with swapped bodies
            new_if_else = f"{prefix} {else_body_text} else {if_body_text}"

            # Replace the original if-else statement
            start_byte = if_node.start_byte
            end_byte = if_node.end_byte

            modified_source = (
                modified_source[:start_byte] + new_if_else + modified_source[end_byte:]
            )

        return modified_source


class ControlShuffleLinesModifier(GolangProceduralModifier):
    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions
    max_complexity: int = 10

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply line shuffling to the Go function body."""
        parser = Parser(GO_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Shuffle lines in function bodies
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
            if n.type in ["function_declaration", "method_declaration"]:
                # Find the function body (block statement)
                body_block = None
                for child in n.children:
                    if child.type == "block":
                        body_block = child
                        break

                if body_block:
                    # Get the statements inside the block (excluding braces)
                    statements = []
                    for child in body_block.children:
                        candidate_stmts = [child]
                        if child.type == "statement_list":
                            candidate_stmts = child.children
                        for stmt in candidate_stmts:
                            # Skip opening and closing braces, collect actual statements
                            if stmt.type not in ["{", "}"]:
                                statements.append(stmt)

                    # Only shuffle if there are at least 2 statements
                    if len(statements) >= 2:
                        modifications.append((body_block, statements))

            for child in n.children:
                collect_function_declarations(child)

        collect_function_declarations(node)

        if not modifications:
            return source_code

        # Apply modifications from end to start to preserve byte offsets
        modified_source = source_code
        for body_block, statements in reversed(modifications):
            # Create shuffled indices
            shuffled_indices = list(range(len(statements)))
            self.rand.shuffle(shuffled_indices)

            # Check if shuffling actually changed the order
            if shuffled_indices == list(range(len(statements))):
                # If by chance we got the same order, force a different shuffle
                if len(statements) >= 2:
                    # Simple swap of first two elements to guarantee change
                    shuffled_indices[0], shuffled_indices[1] = (
                        shuffled_indices[1],
                        shuffled_indices[0],
                    )

            # Extract statement texts and shuffle them
            statement_texts = []
            for stmt in statements:
                stmt_text = source_code[stmt.start_byte : stmt.end_byte]
                statement_texts.append(stmt_text)

            shuffled_texts = [statement_texts[i] for i in shuffled_indices]

            # Find the range to replace (from first statement to last statement)
            first_stmt_start = statements[0].start_byte
            last_stmt_end = statements[-1].end_byte

            # Get indentation from the first statement
            line_start = source_code.rfind("\n", 0, first_stmt_start) + 1
            indent = source_code[line_start:first_stmt_start]

            # Join shuffled statements with proper newlines and indentation
            new_content = ("\n" + indent).join(shuffled_texts)

            # Replace the original statements with shuffled ones
            modified_source = (
                modified_source[:first_stmt_start]
                + new_content
                + modified_source[last_stmt_end:]
            )

        return modified_source
