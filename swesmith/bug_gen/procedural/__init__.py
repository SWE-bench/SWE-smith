import libcst
import random

from swesmith.constants import DEFAULT_PM_LIKELIHOOD
from swesmith.utils import CodeEntity


class PythonProceduralModifier(libcst.CSTTransformer):
    min_complexity: int = 3
    max_complexity: int = float("inf")

    def __init__(self, likelihood: float = DEFAULT_PM_LIKELIHOOD, seed: float = 24):
        super().__init__()
        assert 0 <= likelihood <= 1, "Likelihood must be between 0 and 1."
        self.rand = random.Random(seed)
        self.likelihood = likelihood

    def flip(self) -> bool:
        return self.rand.random() < self.likelihood

    def can_change(self, code_entity: CodeEntity) -> bool:
        """Check if the CodeEntity satisfies the conditions of the modifier."""
        return (
            all(c in code_entity._tags for c in self.conditions)
            and self.min_complexity <= code_entity.complexity() <= self.max_complexity
        )


FLIPPED_OPERATORS = {
    libcst.Add: libcst.Subtract,
    libcst.And: libcst.Or,
    libcst.BitAnd: libcst.BitOr,
    libcst.BitAnd: libcst.BitXor,
    libcst.BitOr: libcst.BitAnd,
    libcst.BitXor: libcst.BitAnd,
    libcst.Divide: libcst.Multiply,
    libcst.Equal: libcst.NotEqual,
    libcst.FloorDivide: libcst.Modulo,
    libcst.GreaterThan: libcst.LessThan,
    libcst.GreaterThanEqual: libcst.LessThanEqual,
    libcst.In: libcst.NotIn,
    libcst.Is: libcst.IsNot,
    libcst.IsNot: libcst.Is,
    libcst.LeftShift: libcst.RightShift,
    libcst.LessThan: libcst.GreaterThan,
    libcst.LessThanEqual: libcst.GreaterThanEqual,
    libcst.Modulo: libcst.FloorDivide,
    libcst.Multiply: libcst.Divide,
    libcst.NotEqual: libcst.Equal,
    libcst.NotIn: libcst.In,
    libcst.Or: libcst.And,
    libcst.Power: libcst.Multiply,
    libcst.RightShift: libcst.LeftShift,
    libcst.Subtract: libcst.Add,
}
