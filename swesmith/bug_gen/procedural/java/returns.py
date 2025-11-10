"""
Return-related procedural modifications for Java code.
"""

import random

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMProp
from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

JAVA_LANGUAGE = Language(tsjava.language())


class ReturnNullModifier(JavaProceduralModifier):
    """Change return statements to return null."""

    explanation: str = "Changed return value to null"
    name: str = "func_pm_return_null"
    conditions: list = []

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_return_to_null(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_return_to_null(self, code: str, node) -> str:
        """Change return statements to return null."""
        candidates = []
        self._find_returns(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        
        # Check if this is already returning null
        for child in target.children:
            if child.type != "return":
                return_expr = code[child.start_byte : child.end_byte]
                if return_expr.strip() in ["null", "null;"]:
                    # Already returning null, skip
                    return code
                # Replace with null
                return code[: child.start_byte] + "null" + code[child.end_byte :]

        return code

    def _find_returns(self, node, candidates):
        """Find return statements with non-null values."""
        if node.type == "return_statement":
            # Check if it's not void return
            has_expression = any(
                child.type not in ["return", ";"] for child in node.children
            )
            if has_expression:
                candidates.append(node)
        for child in node.children:
            self._find_returns(child, candidates)


class ReturnThisModifier(JavaProceduralModifier):
    """Change return statements to return 'this'."""

    explanation: str = "Changed return value to 'this'"
    name: str = "func_pm_return_this"
    conditions: list = []

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._change_return_to_this(code_entity.src_code, tree.root_node)

        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_return_to_this(self, code: str, node) -> str:
        """Change return statements to return 'this'."""
        candidates = []
        self._find_returns(code, node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        
        # Check if this is already returning 'this'
        for child in target.children:
            if child.type not in ["return", ";"]:
                return_expr = code[child.start_byte : child.end_byte]
                if return_expr.strip() in ["this", "this;"]:
                    # Already returning this, skip
                    return code
                # Replace with this
                return code[: child.start_byte] + "this" + code[child.end_byte :]

        return code

    def _find_returns(self, code: str, node, candidates):
        """Find return statements in non-static methods."""
        if node.type == "return_statement":
            # Check if it's not void return
            has_expression = any(
                child.type not in ["return", ";"] for child in node.children
            )
            if has_expression:
                # Check if we're in a static method (skip static methods)
                # For simplicity, we'll just check for 'static' keyword in parent method
                method_node = node.parent
                while method_node and method_node.type != "method_declaration":
                    method_node = method_node.parent
                
                if method_node:
                    # Check if method has 'static' modifier
                    is_static = False
                    for child in method_node.children:
                        if child.type == "modifiers":
                            method_text = code[child.start_byte : child.end_byte]
                            if "static" in method_text:
                                is_static = True
                                break
                    
                    if not is_static:
                        candidates.append(node)
        
        for child in node.children:
            self._find_returns(code, child, candidates)

