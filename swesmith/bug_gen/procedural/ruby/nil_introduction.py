from swesmith.bug_gen.procedural.ruby.base import RUBY_LANGUAGE, RubyProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty
from tree_sitter import Parser


class SafeNavigationRemovalModifier(RubyProceduralModifier):
    explanation: str = (
        "A safe navigation operator (&.) has been removed, allowing nil to propagate."
    )
    name: str = "func_pm_ruby_safe_nav_removal"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_FUNCTION_CALL]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Replace &. with . in method calls."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find call nodes that use &. operator
        calls = self.find_nodes(tree.root_node, "call")
        candidates = []
        for call in calls:
            for child in call.children:
                if child.type == "&.":
                    candidates.append(child)

        if not candidates:
            return None

        target = self.rand.choice(candidates)
        modified_code = self.replace_node(code_entity.src_code, target, ".")

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class OrDefaultRemovalModifier(RubyProceduralModifier):
    explanation: str = (
        "A fallback default (|| value) has been removed, allowing nil to propagate."
    )
    name: str = "func_pm_ruby_or_default_removal"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP]

    @staticmethod
    def _in_conditional(node) -> bool:
        """Check if node is inside a conditional's condition subtree."""
        ancestor = node
        while ancestor.parent is not None:
            parent = ancestor.parent
            cond = parent.child_by_field_name("condition")
            if cond is not None and cond.id == ancestor.id:
                return True
            ancestor = parent
        return False

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Replace `x || default` with just `x`."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        binaries = self.find_nodes(tree.root_node, "binary")
        candidates = []
        for node in binaries:
            is_or = False
            for child in node.children:
                if hasattr(child, "text") and child.text in (b"||", b"or"):
                    is_or = True
                    break
            if is_or and not self._in_conditional(node):
                candidates.append(node)

        if not candidates:
            return None

        target = self.rand.choice(candidates)
        # Replace with just the left operand
        left = target.children[0]
        left_text = code_entity.src_code.encode("utf8")[
            left.start_byte : left.end_byte
        ].decode("utf8")

        modified_code = self.replace_node(code_entity.src_code, target, left_text)

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class PresenceStripModifier(RubyProceduralModifier):
    explanation: str = "A .presence call has been removed."
    name: str = "func_pm_ruby_presence_strip"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_FUNCTION_CALL]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove .presence calls, leaving just the receiver."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        calls = self.find_nodes(tree.root_node, "call")
        candidates = []
        for call in calls:
            # Check if the method name is "presence" and there's no argument_list
            method_name = None
            has_args = False
            receiver = None
            for child in call.children:
                if child.type == "identifier":
                    method_name = child.text.decode("utf8")
                elif child.type == "argument_list":
                    has_args = True
                elif child.type in (".", "&."):
                    pass  # operator
                else:
                    if receiver is None:
                        receiver = child

            if method_name == "presence" and not has_args and receiver:
                candidates.append((call, receiver))

        if not candidates:
            return None

        call, receiver = self.rand.choice(candidates)
        src_bytes = code_entity.src_code.encode("utf8")
        receiver_text = src_bytes[receiver.start_byte : receiver.end_byte].decode(
            "utf8"
        )
        modified_code = self.replace_node(code_entity.src_code, call, receiver_text)

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


BANG_METHODS = {"first!", "last!", "take!", "find_by!"}


class BangMethodStripModifier(RubyProceduralModifier):
    explanation: str = (
        "A bang method (!) has been replaced with its non-raising variant."
    )
    name: str = "func_pm_ruby_bang_method_strip"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_FUNCTION_CALL]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove trailing ! from allowlisted bang methods."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        calls = self.find_nodes(tree.root_node, "call")
        candidates = []
        for call in calls:
            for child in call.children:
                if child.type == "identifier":
                    name = child.text.decode("utf8")
                    if name in BANG_METHODS:
                        candidates.append(child)

        if not candidates:
            return None

        target = self.rand.choice(candidates)
        name = target.text.decode("utf8")
        modified_code = self.replace_node(code_entity.src_code, target, name[:-1])

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class OrEqualsRemovalModifier(RubyProceduralModifier):
    explanation: str = (
        "A memoization operator (||=) has been replaced with plain assignment."
    )
    name: str = "func_pm_ruby_or_equals_removal"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_ASSIGNMENT]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Replace ||= with = in operator assignments."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        op_assigns = self.find_nodes(tree.root_node, "operator_assignment")
        candidates = []
        for node in op_assigns:
            for child in node.children:
                if hasattr(child, "text") and child.text == b"||=":
                    candidates.append(child)

        if not candidates:
            return None

        target = self.rand.choice(candidates)
        modified_code = self.replace_node(code_entity.src_code, target, "=")

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )


class NilGuardRemovalModifier(RubyProceduralModifier):
    explanation: str = "A nil guard clause has been removed."
    name: str = "func_pm_ruby_nil_guard_removal"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove guard clause lines like `return if x.nil?`."""
        if not self.flip():
            return None

        parser = Parser(RUBY_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        nodes = self.find_nodes(tree.root_node, "if_modifier", "unless_modifier")
        guard_keywords = {"return", "next", "break", "raise"}

        candidates = []
        for node in nodes:
            # The body is the first child of modifier conditionals
            body = node.children[0] if node.children else None
            if body:
                body_text = body.text.decode("utf8").strip()
                first_word = body_text.split()[0] if body_text.split() else ""
                if first_word in guard_keywords:
                    candidates.append(node)

        if not candidates:
            return None

        target = self.rand.choice(candidates)
        modified_code = self.replace_node(code_entity.src_code, target, "")

        valid = self.validate_syntax(code_entity.src_code, modified_code)
        if not valid:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
