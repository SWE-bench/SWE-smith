from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.ruby.base import RubyProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity, CodeProperty


class RemoveLoopModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.REMOVE_LOOP.explanation
    name: str = CommonPMs.REMOVE_LOOP.name
    conditions: list = CommonPMs.REMOVE_LOOP.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        return self._remove_matching_nodes(code_entity, "while", "until", "for")


class RemoveConditionalModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.REMOVE_CONDITIONAL.explanation
    name: str = CommonPMs.REMOVE_CONDITIONAL.name
    conditions: list = CommonPMs.REMOVE_CONDITIONAL.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        return self._remove_matching_nodes(code_entity, "if", "unless")


class RemoveAssignModifier(RubyProceduralModifier):
    explanation: str = CommonPMs.REMOVE_ASSIGNMENT.explanation
    name: str = CommonPMs.REMOVE_ASSIGNMENT.name
    conditions: list = CommonPMs.REMOVE_ASSIGNMENT.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        return self._remove_matching_nodes(
            code_entity, "assignment", "operator_assignment"
        )


class RemoveRescueEnsureModifier(RubyProceduralModifier):
    explanation: str = "Exception handling (rescue/ensure) may be missing."
    name: str = "func_pm_remove_rescue_ensure"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_EXCEPTION]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        return self._remove_matching_nodes(
            code_entity, "rescue", "ensure", validate=True
        )
