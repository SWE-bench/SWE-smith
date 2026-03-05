from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.ruby.base import RUBY_LANGUAGE, RubyProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty
from tree_sitter import Parser


class ControlIfElseInvertModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = 5

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Swap if-body and else-body in Ruby if/unless statements."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._invert_if_else(code_entity.src_code, tree.root_node)

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _invert_if_else(self, source_code: str, node) -> str:
        """Find if/unless statements with else clauses and swap bodies."""
        modifications = []

        def collect(n):
            if n.type in ("if", "unless"):
                then_node = None
                else_node = None
                for child in n.children:
                    if child.type == "then":
                        then_node = child
                    elif child.type == "else":
                        else_node = child

                if then_node and else_node and self.flip():
                    modifications.append((then_node, else_node))

            for child in n.children:
                collect(child)

        collect(node)

        if not modifications:
            return source_code

        source_bytes = source_code.encode("utf8")
        for then_node, else_node in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            # Get the statement children (not keywords) from each branch
            then_stmts = [c for c in then_node.children if c.type != "then"]
            else_stmts = [c for c in else_node.children if c.type != "else"]

            if not then_stmts or not else_stmts:
                continue

            # Extract the text of the actual statement content
            then_content = source_bytes[
                then_stmts[0].start_byte : then_stmts[-1].end_byte
            ]
            else_content = source_bytes[
                else_stmts[0].start_byte : else_stmts[-1].end_byte
            ]

            # Determine indentation for each branch by looking at the first
            # non-whitespace content position
            def get_indent(node_list):
                start = node_list[0].start_byte
                # Walk backwards from start to find the beginning of the line
                line_start = source_bytes.rfind(b"\n", 0, start)
                if line_start == -1:
                    return b""
                return source_bytes[line_start + 1 : start]

            then_indent = get_indent(then_stmts)
            else_indent = get_indent(else_stmts)

            # Re-indent the swapped content
            def reindent(content, from_indent, to_indent):
                lines = content.split(b"\n")
                result = []
                for i, line in enumerate(lines):
                    if i == 0:
                        result.append(line)
                    elif line.startswith(from_indent):
                        result.append(to_indent + line[len(from_indent) :])
                    else:
                        result.append(line)
                return b"\n".join(result)

            new_then = reindent(else_content, else_indent, then_indent)
            new_else = reindent(then_content, then_indent, else_indent)

            # Replace else body first (later in file), then then body
            source_bytes = (
                source_bytes[: else_stmts[0].start_byte]
                + new_else
                + source_bytes[else_stmts[-1].end_byte :]
            )
            source_bytes = (
                source_bytes[: then_stmts[0].start_byte]
                + new_then
                + source_bytes[then_stmts[-1].end_byte :]
            )

        return source_bytes.decode("utf8")


class ControlShuffleLinesModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions
    max_complexity: int = 10

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Shuffle top-level statements in a Ruby method body."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._shuffle_statements(code_entity.src_code, tree.root_node)

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _shuffle_statements(self, source_code: str, node) -> str:
        """Find body_statement nodes in methods and shuffle their children."""
        modifications = []

        def collect(n):
            if n.type in ("method", "singleton_method"):
                for child in n.children:
                    if child.type == "body_statement":
                        # Collect top-level statements (skip comments)
                        statements = [
                            c
                            for c in child.children
                            if c.type not in ("comment",) and c.start_byte != c.end_byte
                        ]
                        if len(statements) >= 2:
                            modifications.append(statements)
            for child in n.children:
                collect(child)

        collect(node)

        if not modifications:
            return source_code

        source_bytes = source_code.encode("utf8")
        for statements in reversed(modifications):
            indices = list(range(len(statements)))
            self.rand.shuffle(indices)

            # Ensure we actually changed the order
            if indices == list(range(len(statements))):
                if len(statements) >= 2:
                    indices[0], indices[1] = indices[1], indices[0]

            texts = [source_bytes[s.start_byte : s.end_byte] for s in statements]
            shuffled = [texts[i] for i in indices]

            first_start = statements[0].start_byte
            last_end = statements[-1].end_byte

            # Get indentation
            line_start = source_bytes.rfind(b"\n", 0, first_start) + 1
            indent = source_bytes[line_start:first_start]

            new_content = (b"\n" + indent).join(shuffled)

            source_bytes = (
                source_bytes[:first_start] + new_content + source_bytes[last_end:]
            )

        return source_bytes.decode("utf8")


class GuardClauseInvertModifier(RubyProceduralModifier):
    explanation: str = "A guard clause conditional has been inverted."
    name: str = "func_pm_guard_clause_invert"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Flip postfix if <-> unless in guard clauses."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        nodes = self.find_nodes(tree.root_node, "if_modifier", "unless_modifier")
        if not nodes:
            return None

        # Pick one to flip
        target = self.rand.choice(nodes)

        # Find the keyword child ("if" or "unless")
        keyword_node = None
        for child in target.children:
            text = child.text.decode("utf8")
            if text in ("if", "unless"):
                keyword_node = child
                break

        if not keyword_node:
            return None

        old_kw = keyword_node.text.decode("utf8")
        new_kw = "unless" if old_kw == "if" else "if"

        modified_code = self.replace_node(code_entity.src_code, keyword_node, new_kw)

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
