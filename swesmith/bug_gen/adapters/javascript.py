import re
import warnings

import tree_sitter_javascript as tsjs

from swesmith.constants import CodeEntity, CodeProperty, TODO_REWRITE
from tree_sitter import Language, Parser

JS_LANGUAGE = Language(tsjs.language())


class JavaScriptEntity(CodeEntity):
    def _analyze_properties(self):
        """Analyze JavaScript/TypeScript code properties."""
        node = self.node

        # Core entity types
        if node.type in [
            "function_declaration",
            "function",
            "arrow_function",
            "method_definition",
        ]:
            self._tags.add(CodeProperty.IS_FUNCTION)
        elif node.type in ["class_declaration", "class"]:
            self._tags.add(CodeProperty.IS_CLASS)

        # Control flow analysis
        self._walk_for_properties(node)

    def _walk_for_properties(self, n):
        """Walk the AST and analyze properties."""
        self._check_control_flow(n)
        self._check_operations(n)
        self._check_binary_expressions(n)

        for child in n.children:
            self._walk_for_properties(child)

    def _check_control_flow(self, n):
        """Check for control flow patterns."""
        if n.type in [
            "for_statement",
            "for_in_statement",
            "for_of_statement",
            "while_statement",
            "do_statement",
        ]:
            self._tags.add(CodeProperty.HAS_LOOP)
        if n.type == "if_statement":
            self._tags.add(CodeProperty.HAS_IF)
            if any(child.type == "else_clause" for child in n.children):
                self._tags.add(CodeProperty.HAS_IF_ELSE)
        if n.type in ["try_statement", "catch_clause", "throw_statement"]:
            self._tags.add(CodeProperty.HAS_EXCEPTION)

    def _check_operations(self, n):
        """Check for various operations."""
        if n.type in ["subscript_expression", "member_expression"]:
            self._tags.add(CodeProperty.HAS_LIST_INDEXING)
        if n.type == "call_expression":
            self._tags.add(CodeProperty.HAS_FUNCTION_CALL)
        if n.type == "return_statement":
            self._tags.add(CodeProperty.HAS_RETURN)
        if n.type in ["import_statement", "import_clause"]:
            self._tags.add(CodeProperty.HAS_IMPORT)
        if n.type in ["assignment_expression", "variable_declaration"]:
            self._tags.add(CodeProperty.HAS_ASSIGNMENT)
        if n.type == "arrow_function":
            self._tags.add(CodeProperty.HAS_LAMBDA)
        if n.type in ["binary_expression", "unary_expression", "update_expression"]:
            self._tags.add(CodeProperty.HAS_ARITHMETIC)
        if n.type == "decorator":
            self._tags.add(CodeProperty.HAS_DECORATOR)
        if n.type in ["try_statement", "with_statement"]:
            self._tags.add(CodeProperty.HAS_WRAPPER)
        if n.type == "class_declaration" and any(
            child.type == "class_heritage" for child in n.children
        ):
            self._tags.add(CodeProperty.HAS_PARENT)
        if n.type in ["unary_expression", "update_expression"]:
            self._tags.add(CodeProperty.HAS_UNARY_OP)

    def _check_binary_expressions(self, n):
        """Check binary expression patterns."""
        if n.type == "binary_expression":
            self._tags.add(CodeProperty.HAS_BINARY_OP)
            # Check for boolean operators
            if any(
                hasattr(child, "text") and child.text.decode("utf-8") in ["&&", "||"]
                for child in n.children
            ):
                self._tags.add(CodeProperty.HAS_BOOL_OP)
            # Check for comparison operators (off by one potential)
            for child in n.children:
                if hasattr(child, "text") and child.text.decode("utf-8") in [
                    "<",
                    ">",
                    "<=",
                    ">=",
                ]:
                    self._tags.add(CodeProperty.HAS_OFF_BY_ONE)

    @property
    def name(self) -> str:
        return self._extract_name_from_node()

    def _extract_name_from_node(self) -> str:
        """Extract name from different node types."""
        # Function declarations
        if self.node.type == "function_declaration":
            return self._find_child_text("identifier")

        # Method definitions
        if self.node.type == "method_definition":
            return self._find_child_text("property_identifier")

        # Class declarations
        if self.node.type == "class_declaration":
            return self._find_child_text("identifier")

        # Variable declarations with function expressions
        if self.node.type == "variable_declarator":
            return self._find_child_text("identifier")

        # Assignment expressions with function expressions
        if self.node.type == "assignment_expression":
            return self._find_child_text("identifier")

        return ""

    def _find_child_text(self, child_type: str) -> str:
        """Find and return text from child node of specified type."""
        for child in self.node.children:
            if child.type == child_type:
                return child.text.decode("utf-8")
        return ""

    @property
    def signature(self) -> str:
        # Find the body of the function/class and return everything before it
        for child in self.node.children:
            if child.type in ["statement_block", "class_body"]:
                body_start_byte = child.start_byte - self.node.start_byte
                signature = self.src_code[:body_start_byte].strip()
                # Remove trailing { if present
                if signature.endswith(" {"):
                    signature = signature[:-2].strip()
                return signature

        # For arrow functions with expression body
        if self.node.type == "arrow_function" and "=>" in self.src_code:
            return self.src_code.split("=>")[0].strip() + " =>"

        # For function expressions, extract just the declaration part
        if self.node.type == "variable_declarator":
            # Handle cases like "var myFunc = function(x, y) { ... }"
            src_lines = self.src_code.split("\n")
            first_line = src_lines[0]
            if " = function" in first_line:
                # Find the opening brace and cut before it
                brace_pos = first_line.find(" {")
                if brace_pos != -1:
                    return first_line[:brace_pos].strip()
                else:
                    # Remove any trailing semicolon or brace
                    result = first_line.strip()
                    if result.endswith(";"):
                        result = result[:-1].strip()
                    return result

        return self.src_code.split("\n")[0].strip()

    @property
    def stub(self) -> str:
        signature = self.signature

        if self.node.type == "class_declaration":
            return f"{signature} {{\n\t// {TODO_REWRITE}\n}}"
        elif self.node.type == "arrow_function":
            if "=>" in signature:
                return f"{signature} {{\n\t// {TODO_REWRITE}\n}}"
            else:
                return f"{signature} => {{\n\t// {TODO_REWRITE}\n}}"
        else:
            return f"{signature} {{\n\t// {TODO_REWRITE}\n}}"

    @property
    def complexity(self) -> int:
        def walk(node):
            score = 0

            # Decision points and control flow
            if node.type in [
                "if_statement",
                "else_clause",
                "for_statement",
                "for_in_statement",
                "for_of_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "case_clause",
                "catch_clause",
                "conditional_expression",  # ternary operator
            ]:
                score += 1

            # Boolean operators
            if node.type == "binary_expression":
                for child in node.children:
                    if hasattr(child, "text") and child.text.decode("utf-8") in [
                        "&&",
                        "||",
                    ]:
                        score += 1

            for child in node.children:
                score += walk(child)

            return score

        return 1 + walk(self.node)


def get_entities_from_file_js(
    entities: list[JavaScriptEntity],
    file_path: str,
    max_entities: int = -1,
) -> list[JavaScriptEntity]:
    """
    Parse a .js/.ts file and return up to max_entities top-level functions and classes.
    If max_entities < 0, collects them all.
    """
    parser = Parser(JS_LANGUAGE)

    try:
        file_content = open(file_path, "r", encoding="utf8").read()
    except UnicodeDecodeError:
        warnings.warn(f"Could not decode file {file_path}", stacklevel=2)
        return entities

    tree = parser.parse(bytes(file_content, "utf8"))
    root = tree.root_node
    lines = file_content.splitlines()

    _walk_and_collect(root, entities, lines, str(file_path), max_entities)
    return entities


def _walk_and_collect(node, entities, lines, file_path, max_entities):
    """Walk the AST and collect entities."""
    # stop if we've hit the limit
    if 0 <= max_entities == len(entities):
        return

    if node.type == "ERROR":
        warnings.warn(f"Error encountered parsing {file_path}", stacklevel=2)
        return

    # Collect functions, methods, and classes
    if node.type in [
        "function_declaration",
        "method_definition",
        "class_declaration",
    ]:
        entities.append(_build_entity(node, lines, file_path))
        if 0 <= max_entities == len(entities):
            return

    # Also collect variable declarations that contain function expressions
    elif node.type == "variable_declaration":
        _collect_variable_functions(node, entities, lines, file_path, max_entities)

    # Collect assignment expressions with function values
    elif node.type == "assignment_expression":
        _collect_assignment_functions(node, entities, lines, file_path, max_entities)

    for child in node.children:
        _walk_and_collect(child, entities, lines, file_path, max_entities)


def _collect_variable_functions(node, entities, lines, file_path, max_entities):
    """Collect function expressions from variable declarations."""
    for child in node.children:
        if child.type == "variable_declarator":
            for grandchild in child.children:
                if grandchild.type in ["function_expression", "arrow_function"]:
                    entities.append(_build_entity(child, lines, file_path))
                    if 0 <= max_entities == len(entities):
                        return


def _collect_assignment_functions(node, entities, lines, file_path, max_entities):
    """Collect function expressions from assignment expressions."""
    for child in node.children:
        if child.type in ["function_expression", "arrow_function"]:
            entities.append(_build_entity(node, lines, file_path))
            if 0 <= max_entities == len(entities):
                return


def _build_entity(node, lines, file_path: str) -> JavaScriptEntity:
    """
    Turn a Tree-sitter node into JavaScriptEntity.
    """
    # start_point/end_point are (row, col) zero-based
    start_row, _ = node.start_point
    end_row, _ = node.end_point

    # slice out the raw lines
    snippet = lines[start_row : end_row + 1]

    # detect indent on first line
    first = snippet[0]
    m = re.match(r"^(?P<indent>[\t ]*)", first)
    indent_str = m.group("indent") if m else ""
    # tabs count as size=1, else use count of spaces, fallback to 2 (common in JS)
    indent_size = 1 if "\t" in indent_str else (len(indent_str) or 2)
    indent_level = len(indent_str) // indent_size

    # dedent each line
    dedented = []
    for line in snippet:
        if len(line) >= indent_level * indent_size:
            dedented.append(line[indent_level * indent_size :])
        else:
            dedented.append(line.lstrip("\t "))

    return JavaScriptEntity(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_start=start_row + 1,
        line_end=end_row + 1,
        node=node,
        src_code="\n".join(dedented),
    )
