import random

from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Enum
from swesmith.constants import (
    DEFAULT_PM_LIKELIHOOD,
    BugRewrite,
    CodeEntity,
    CodeProperty,
)


class ProceduralModifier(ABC):
    """Abstract base class for procedural modifiers."""

    max_attempts: int = 5
    min_complexity: int = 3
    max_complexity: int = float("inf")

    # To be defined in subclasses
    explanation: str
    name: str
    conditions: list = []

    def __init__(self, likelihood: float = DEFAULT_PM_LIKELIHOOD, seed: float = 24):
        assert 0 <= likelihood <= 1, "Likelihood must be between 0 and 1."
        self.rand = random.Random(seed)
        self.likelihood = likelihood

    def flip(self) -> bool:
        return self.rand.random() < self.likelihood

    def can_change(self, code_entity: CodeEntity) -> bool:
        """Check if the CodeEntity satisfies the conditions of the modifier."""
        return (
            all(c in code_entity._tags for c in self.conditions)
            and self.min_complexity <= code_entity.complexity <= self.max_complexity
        )

    @abstractmethod
    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """
        Apply procedural modifications to the given code entity.

        Args:
            code_entity: The code entity to modify

        Returns:
            BugRewrite if modification was successful, None otherwise
        """
        pass


CommonPMProp = namedtuple("CommonPM", ["name", "explanation", "conditions"])


class CommonPMs(Enum):
    """Common procedural modifiers with their properties."""

    CLASS_REMOVE_BASES = CommonPMProp(
        name="func_pm_class_rm_base",
        explanation="The base class has been removed from the class definition.",
        conditions=[CodeProperty.IS_CLASS, CodeProperty.HAS_PARENT],
    )
    CLASS_REMOVE_FUNCS = CommonPMProp(
        name="func_pm_class_rm_funcs",
        explanation="Method(s) and their reference(s) have been removed from the class.",
        conditions=[CodeProperty.IS_CLASS],
    )
    CLASS_SHUFFLE_METHODS = CommonPMProp(
        name="func_pm_class_shuffle_funcs",
        explanation="The methods in a class have been shuffled.",
        conditions=[CodeProperty.IS_CLASS],
    )
    CONTROL_IF_ELSE_INVERT = CommonPMProp(
        name="func_pm_ctrl_invert_if",
        explanation="The if-else conditions may be out of order, or the bodies are inverted.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF_ELSE],
    )
    CONTROL_SHUFFLE_LINES = CommonPMProp(
        name="func_pm_ctrl_shuffle",
        explanation="The lines inside a function may be out of order.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_LOOP],
    )
    OPERATION_CHANGE = CommonPMProp(
        name="func_pm_op_change",
        explanation="The operations in an expression are likely incorrect.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP],
    )
    OPERATION_FLIP_OPERATOR = CommonPMProp(
        name="func_pm_flip_operators",
        explanation="The operators in an expression are likely incorrect.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP],
    )
    OPERATION_SWAP_OPERANDS = CommonPMProp(
        name="func_pm_op_swap",
        explanation="The operands in an expression are likely in the wrong order.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP],
    )
    OPERATION_BREAK_CHAINS = CommonPMProp(
        name="func_pm_op_break_chains",
        explanation="There are expressions or mathematical operations that are likely incomplete.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP],
    )
    OPERATION_CHANGE_CONSTANTS = CommonPMProp(
        name="func_pm_op_change_const",
        explanation="The constants in an expression might be incorrect.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP],
    )
    OPERATION_INC_DEC_FLIP = CommonPMProp(
        name="func_pm_inc_dec_flip",
        explanation="The increment/decrement operation in the code is likely incorrect.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_UNARY_OP],
    )
    OPERATION_COMPOUND_ASSIGN_SWAP = CommonPMProp(
        name="func_pm_aug_assign_swap",
        explanation="The compound assignment operator in the code is likely incorrect.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_ASSIGNMENT],
    )
    OPERATION_BOOL_LITERAL_FLIP = CommonPMProp(
        name="func_pm_bool_negate",
        explanation="A boolean literal has likely been flipped.",
        conditions=[CodeProperty.IS_FUNCTION],
    )
    REMOVE_LOOP = CommonPMProp(
        name="func_pm_remove_loop",
        explanation="There is one or more missing loops that is causing the bug.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_LOOP],
    )
    REMOVE_CONDITIONAL = CommonPMProp(
        name="func_pm_remove_cond",
        explanation="There is one or more missing conditionals that causes the bug.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF],
    )
    REMOVE_ASSIGNMENT = CommonPMProp(
        name="func_pm_remove_assign",
        explanation="There is likely a missing assignment in the code.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_ASSIGNMENT],
    )
    CONTROL_BREAK_CONTINUE_SWAP = CommonPMProp(
        name="func_pm_loop_break_continue_swap",
        explanation="A break/continue statement may be swapped in loop control flow.",
        conditions=[CodeProperty.IS_FUNCTION, CodeProperty.HAS_LOOP],
    )

    def __init__(self, name, explanation, conditions):
        self.pm_name = name
        self.explanation = explanation
        self.conditions = conditions

    @property
    def name(self):
        return self.pm_name
