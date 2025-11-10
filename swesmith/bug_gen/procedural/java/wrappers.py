"""
Wrapper and defensive code removal for Java.
"""

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.java.base import JavaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty

JAVA_LANGUAGE = Language(tsjava.language())


class RemoveTryCatchModifier(JavaProceduralModifier):
    """Removes try-catch blocks, exposing exceptions."""
    
    name = "func_pm_remove_try_catch"
    explanation = "Try-catch blocks may be missing or incomplete."
    conditions = [CodeProperty.IS_FUNCTION]
    
    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        
        # Find try statements
        try_statements = []
        self._find_try_statements(tree.root_node, try_statements)
        
        if not try_statements:
            return None
        
        # Pick one randomly
        target = self.rand.choice(try_statements)
        
        # Find the try block body
        try_block = None
        for child in target.children:
            if child.type == "block" and child.start_byte > target.start_byte:
                try_block = child
                break
        
        if not try_block:
            return None
        
        # Extract the content of the try block (without the braces)
        try_body_content = self._extract_block_content(code_entity.src_code, try_block)
        
        if try_body_content is None:
            return None
        
        # Replace the entire try-catch with just the try body content
        modified_code = (
            code_entity.src_code[:target.start_byte] +
            try_body_content +
            code_entity.src_code[target.end_byte:]
        )
        
        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None
        
        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )
    
    def _find_try_statements(self, node, results):
        """Find all try statements."""
        if node.type == "try_statement":
            results.append(node)
        for child in node.children:
            self._find_try_statements(child, results)
    
    def _extract_block_content(self, code: str, block_node):
        """Extract content inside block braces."""
        block_text = code[block_node.start_byte:block_node.end_byte]
        
        # Remove opening and closing braces
        if block_text.startswith('{') and block_text.endswith('}'):
            return block_text[1:-1]
        return None


class RemoveNullCheckModifier(JavaProceduralModifier):
    """Removes null checks, potentially causing NPEs."""
    
    name = "func_pm_remove_null_check"
    explanation = "Null checks may be missing in the code."
    conditions = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF]
    
    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        
        # Find if statements with null checks
        null_check_ifs = []
        self._find_null_check_ifs(tree.root_node, code_entity.src_code, null_check_ifs)
        
        if not null_check_ifs:
            return None
        
        # Pick one randomly
        target = self.rand.choice(null_check_ifs)
        
        # Find the if body (what gets executed when condition is true)
        if_body = None
        for child in target.children:
            if child.type == "block" or child.type in ["expression_statement", "return_statement", "throw_statement"]:
                if_body = child
                break
        
        if not if_body:
            return None
        
        # Extract the if body content
        if if_body.type == "block":
            body_content = self._extract_block_content(code_entity.src_code, if_body)
        else:
            body_content = code_entity.src_code[if_body.start_byte:if_body.end_byte]
        
        if body_content is None:
            return None
        
        # Replace the entire if statement with just the body
        modified_code = (
            code_entity.src_code[:target.start_byte] +
            body_content +
            code_entity.src_code[target.end_byte:]
        )
        
        # Validate syntax before returning
        if not self.validate_syntax(code_entity.src_code, modified_code):
            return None
        
        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )
    
    def _find_null_check_ifs(self, node, code: str, results):
        """Find if statements with null checks (x != null, x == null)."""
        if node.type == "if_statement":
            # Check if condition contains null comparison
            condition_node = None
            for child in node.children:
                if child.type == "parenthesized_expression":
                    condition_node = child
                    break
            
            if condition_node:
                condition_text = code[condition_node.start_byte:condition_node.end_byte]
                if "null" in condition_text and ("!=" in condition_text or "==" in condition_text):
                    results.append(node)
        
        for child in node.children:
            self._find_null_check_ifs(child, code, results)
    
    def _extract_block_content(self, code: str, block_node):
        """Extract content inside block braces."""
        block_text = code[block_node.start_byte:block_node.end_byte]
        
        # Remove opening and closing braces
        if block_text.startswith('{') and block_text.endswith('}'):
            return block_text[1:-1]
        return None

