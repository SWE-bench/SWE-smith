"""
Java-specific procedural modifications for bug generation.
"""

from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.java.boolean import (
    BooleanNegateModifier,
)
from swesmith.bug_gen.procedural.java.control_flow import (
    ControlIfElseInvertModifier,
)
from swesmith.bug_gen.procedural.java.literals import (
    StringLiteralModifier,
)
from swesmith.bug_gen.procedural.java.loops import (
    LoopBreakContinueSwapModifier,
    LoopOffByOneModifier,
)
from swesmith.bug_gen.procedural.java.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)
from swesmith.bug_gen.procedural.java.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
)
from swesmith.bug_gen.procedural.java.returns import (
    ReturnNullModifier,
)
from swesmith.bug_gen.procedural.java.wrappers import (
    RemoveNullCheckModifier,
    RemoveTryCatchModifier,
)

MODIFIERS_JAVA: list[ProceduralModifier] = [
    # Control flow modifiers
    ControlIfElseInvertModifier(likelihood=0.75),  # Swaps if/else bodies
    RemoveConditionalModifier(
        likelihood=0.4
    ),  # Removes if condition (makes unconditional)
    # Operation modifiers
    OperationChangeModifier(likelihood=0.6),  # Changes +/-/*/ (skips string concat)
    OperationFlipOperatorModifier(likelihood=0.6),  # Flips </>/<=/>=
    OperationSwapOperandsModifier(likelihood=0.5),  # Swaps a+b to b+a
    OperationChangeConstantsModifier(likelihood=0.5),  # Changes 0->1, etc
    OperationBreakChainsModifier(likelihood=0.3),  # Breaks method chains
    # Boolean modifiers
    BooleanNegateModifier(
        likelihood=0.5
    ),  # Negates boolean expressions (true->false, !x->x)
    # Return modifiers
    ReturnNullModifier(likelihood=0.4),  # Changes return values to null
    # Statement modifiers
    RemoveAssignModifier(likelihood=0.4),  # Removes reassignments (not declarations)
    # Loop modifiers
    LoopBreakContinueSwapModifier(likelihood=0.6),  # Swaps break and continue
    LoopOffByOneModifier(likelihood=0.6),  # Changes < to <= and vice versa
    # Wrapper/defensive code removal
    RemoveTryCatchModifier(likelihood=0.4),  # Removes try-catch blocks
    RemoveNullCheckModifier(likelihood=0.5),  # Removes null checks
    # Literal modifications
    StringLiteralModifier(likelihood=0.5),  # Modifies string literals
]
