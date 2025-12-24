from swesmith.constants import TODO_REWRITE, CodeEntity
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_ruby as tsr
import warnings
from swesmith.bug_gen.adapters.utils import build_entity

RUBY_LANGUAGE = Language(tsr.language())


class RubyEntity(CodeEntity):
    @property
    def name(self) -> str:
        query = Query(
            RUBY_LANGUAGE,
            """
            (method name: (identifier) @method.name)
            (singleton_method name: (identifier) @method.name)
            """,
        )
        captures = QueryCursor(query).captures(self.node)
        if "method.name" in captures:
            name_nodes = captures["method.name"]
            if name_nodes:
                return name_nodes[0].text.decode("utf-8")
        return ""

    @property
    def signature(self) -> str:
        query = Query(
            RUBY_LANGUAGE,
            """
            (method body: (body_statement) @method.body)
            (singleton_method body: (body_statement) @method.body)
            """,
        )

        captures = QueryCursor(query).captures(self.node)
        if "method.body" in captures:
            body_nodes = captures["method.body"]
            if not body_nodes:
                return ""
            body = body_nodes[0]
            method_start_row, method_start_col = self.node.start_point
            body_start_row, body_start_col = body.start_point

            src_lines = self.src_code.split("\n")
            if body_start_row == method_start_row:
                line = src_lines[0]
                signature = line[: body_start_col - method_start_col].strip()
                if signature.endswith(";"):
                    signature = signature[:-1].strip()
                return signature
            else:
                signature_lines = src_lines[: body_start_row - method_start_row]
                return "\n".join(signature_lines).strip()
        return ""

    @property
    def stub(self) -> str:
        return f"{self.signature}\n\t# {TODO_REWRITE}\nend"

    @property
    def complexity(self) -> int:
        def walk(node) -> int:
            score = 0

            if node.type in [
                # binary expressions, operators including and, or, ||, &&...
                "binary",
                # blocks
                "block",
                "do_block",
                "block_argument",
                # assignment operators +=, -=, ||=, |=, &&=...
                "operator_assignment",
                # expression modifiers "perform_foo if bar?"
                "if_modifier",
                "rescue_modifier",
                "unless_modifier",
                "until_modifier",
                "while_modifier",
            ]:
                score += 1

            # ternary
            if node.type == "conditional":
                score += 2

            if (
                node.type
                in ["if", "elsif", "else", "ensure", "rescue", "unless", "when"]
                and node.child_count > 0
            ):
                score += 1

            for child in node.children:
                score += walk(child)

            return score

        return 1 + walk(self.node)


def get_entities_from_file_rb(
    entities: list[RubyEntity],
    file_path: str,
    max_entities: int = -1,
) -> None:
    """
    Parse a .rb file and return up to max_entities top-level funcs and types.
    If max_entities < 0, collects them all.
    """
    parser = Parser(RUBY_LANGUAGE)

    file_content = open(file_path, "r", encoding="utf8").read()
    tree = parser.parse(bytes(file_content, "utf8"))
    root = tree.root_node
    lines = file_content.splitlines()

    def walk(node) -> None:
        # stop if we've hit the limit
        if 0 <= max_entities == len(entities):
            return

        if node.type == "ERROR":
            warnings.warn(f"Error encountered parsing {file_path}")
            return

        # ignoring setter and alias methods
        if node.type in [
            "method",
            "singleton_method",
        ]:
            if any(child.type == "body_statement" for child in node.children):
                entities.append(build_entity(node, lines, file_path, RubyEntity))
                if 0 <= max_entities == len(entities):
                    return

        for child in node.children:
            walk(child)

    walk(root)
