import re

from swesmith.bug_gen.procedural.ruby.base import RUBY_LANGUAGE, RubyProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty
from tree_sitter import Parser


_RUBY_IDENTIFIER_PATTERN = r"^[a-zA-Z_]\w*[?!]?$"


class SymbolStringSwapModifier(RubyProceduralModifier):
    explanation: str = "A symbol/string type may be incorrect."
    name: str = "func_pm_ruby_symbol_string_swap"
    conditions: list = [CodeProperty.IS_FUNCTION]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Swap a :symbol to "string" or vice versa."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        candidates = []

        # Find simple symbols (:foo) — not dynamic symbols
        symbols = self.find_nodes(tree.root_node, "simple_symbol")
        for node in symbols:
            text = node.text.decode("utf8")
            # Strip leading : to get the name
            name = text[1:]
            if re.match(_RUBY_IDENTIFIER_PATTERN, name):
                candidates.append(("symbol_to_string", node, name))

        # Find simple strings ("foo") — no interpolation, alphanumeric
        strings = self.find_nodes(tree.root_node, "string")
        for node in strings:
            # A simple string has children: [string_beginning, string_content, string_end]
            content_nodes = [c for c in node.children if c.type == "string_content"]
            if len(content_nodes) == 1:
                content = content_nodes[0].text.decode("utf8")
                if re.match(_RUBY_IDENTIFIER_PATTERN, content):
                    candidates.append(("string_to_symbol", node, content))

        if not candidates:
            return None

        kind, target, name = self.rand.choice(candidates)
        if kind == "symbol_to_string":
            replacement = f'"{name}"'
        else:
            replacement = f":{name}"

        modified_code = self.replace_node(code_entity.src_code, target, replacement)

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class BlockMutationModifier(RubyProceduralModifier):
    explanation: str = "Block parameters or yield arguments may be incorrect."
    name: str = "func_pm_ruby_block_mutation"
    conditions: list = [CodeProperty.IS_FUNCTION]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove block parameters or strip yield arguments."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Collect two types of candidates
        block_params = self.find_nodes(tree.root_node, "block_parameters")
        yield_nodes = [
            n
            for n in self.find_nodes(tree.root_node, "yield")
            if any(c.type == "argument_list" for c in n.children)
        ]

        candidates = []
        for bp in block_params:
            candidates.append(("remove_params", bp))
        for yn in yield_nodes:
            candidates.append(("strip_yield", yn))

        if not candidates:
            return None

        kind, target = self.rand.choice(candidates)

        if kind == "remove_params":
            # Remove the |x, y| block parameters
            modified_code = self.replace_node(code_entity.src_code, target, "")
        else:
            # Replace yield(args) with bare yield
            modified_code = self.replace_node(code_entity.src_code, target, "yield")

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
