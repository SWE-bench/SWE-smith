"""
Java-specific procedural modifications for bug generation.
"""

from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.java.boolean import (
    BooleanNegateModifier,
)
from swesmith.bug_gen.procedural.java.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.java.literals import (
    ClassRemoveInterfaceModifier,
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
    RemoveLoopModifier,
)
from swesmith.bug_gen.procedural.java.returns import (
    ReturnNullModifier,
)
from swesmith.bug_gen.procedural.java.wrappers import (
    RemoveNullCheckModifier,
    RemoveTryCatchModifier,
)

# NEW MODIFIERS (for testing) - Added in latest version
NEW_MODIFIERS_JAVA: list[ProceduralModifier] = [
    # Loop modifiers (2)
    LoopBreakContinueSwapModifier(likelihood=0.6),  # Swaps break and continue
    LoopOffByOneModifier(likelihood=0.6),  # Changes < to <= and vice versa
    
    # Wrapper/defensive code removal (2)
    RemoveTryCatchModifier(likelihood=0.4),  # Removes try-catch blocks
    RemoveNullCheckModifier(likelihood=0.5),  # Removes null checks
    
    # Literal modifications (2)
    StringLiteralModifier(likelihood=0.5),  # Modifies string literals
    ClassRemoveInterfaceModifier(likelihood=0.3),  # Removes interface implementations
]

MODIFIERS_JAVA: list[ProceduralModifier] = [
    # 16 modifiers that produce syntactically valid, semantically buggy Java
    # (Removed: BooleanShortCircuit 6.2%, ReturnThis 8.3% - too low success rates)
    
    # Control flow modifiers (2)
    ControlIfElseInvertModifier(likelihood=0.75),  # Swaps if/else bodies
    RemoveConditionalModifier(likelihood=0.4),  # Removes if condition (makes unconditional)
    
    # Operation modifiers (5)
    OperationChangeModifier(likelihood=0.6),  # Changes +/-/*/ (skips string concat)
    OperationFlipOperatorModifier(likelihood=0.6),  # Flips </>/<=/>=
    OperationSwapOperandsModifier(likelihood=0.5),  # Swaps a+b to b+a
    OperationChangeConstantsModifier(likelihood=0.5),  # Changes 0->1, etc
    OperationBreakChainsModifier(likelihood=0.3),  # Breaks method chains
    
    # Boolean modifiers (1)
    BooleanNegateModifier(likelihood=0.5),  # Negates boolean expressions (true->false, !x->x)
    
    # Return modifiers (1)
    ReturnNullModifier(likelihood=0.4),  # Changes return values to null
    
    # Statement modifiers (1)
    RemoveAssignModifier(likelihood=0.4),  # Removes reassignments (not declarations)
    
    # NEW: Loop modifiers (2)
    LoopBreakContinueSwapModifier(likelihood=0.6),  # Swaps break and continue
    LoopOffByOneModifier(likelihood=0.6),  # Changes < to <= and vice versa
    
    # NEW: Wrapper/defensive code removal (2)
    RemoveTryCatchModifier(likelihood=0.4),  # Removes try-catch blocks
    RemoveNullCheckModifier(likelihood=0.5),  # Removes null checks
    
    # NEW: Literal modifications (2)
    StringLiteralModifier(likelihood=0.5),  # Modifies string literals
    ClassRemoveInterfaceModifier(likelihood=0.3),  # Removes interface implementations
    
    # Disabled modifiers (low success rate or too risky):
    # BooleanShortCircuitModifier - 6.2% success rate (rarely affects behavior)
    # ReturnThisModifier - 8.3% success rate (targets wrong methods)
    # ControlShuffleLinesModifier - breaks variable dependencies
    # RemoveLoopModifier - creates undefined variables from loop iterators
]

