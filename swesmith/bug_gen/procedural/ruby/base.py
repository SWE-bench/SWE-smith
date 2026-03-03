from abc import ABC

import tree_sitter_ruby as tsruby
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

RUBY_LANGUAGE = Language(tsruby.language())


class RubyProceduralModifier(ProceduralModifier, ABC):
    """Base class for Ruby-specific procedural modifications."""

    @staticmethod
    def validate_syntax(original: str, modified: str) -> bool | None:
        """Return True if valid, False if errors, None if unchanged."""
        if original == modified:
            return None
        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(modified, "utf8"))

        def has_errors(node):
            if node.type in ("ERROR", "MISSING"):
                return True
            return any(has_errors(c) for c in node.children)

        return not has_errors(tree.root_node)

    @staticmethod
    def find_nodes(node, *types) -> list:
        """Recursively find all AST nodes matching any of the given types."""
        results = []

        def walk(n):
            if n.type in types:
                results.append(n)
            for child in n.children:
                walk(child)

        walk(node)
        return results

    @staticmethod
    def replace_node(code: str, node, replacement: str) -> str:
        """Replace a tree-sitter node's text via byte offsets."""
        code_bytes = code.encode("utf8")
        new_bytes = (code_bytes[:node.start_byte]
                     + replacement.encode("utf8") + code_bytes[node.end_byte:])
        return new_bytes.decode("utf8")

    def _remove_matching_nodes(
        self, code_entity: CodeEntity, *node_types: str, validate: bool = False
    ) -> BugRewrite | None:
        """Remove AST nodes matching the given types from the source code."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        removals = []

        def collect(n):
            if n.type in node_types and self.flip():
                removals.append(n)
            for child in n.children:
                collect(child)

        collect(tree.root_node)

        if not removals:
            return None

        source_bytes = code_entity.src_code.encode("utf8")
        for node in sorted(removals, key=lambda x: x.start_byte, reverse=True):
            source_bytes = source_bytes[:node.start_byte] + source_bytes[node.end_byte:]

        modified_code = source_bytes.decode("utf8")

        if validate:
            valid = self.validate_syntax(code_entity.src_code, modified_code)
            if not valid:
                return None
        elif modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
