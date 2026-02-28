"""
C++-specific procedural modifications for bug generation.
"""

from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.cpp.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.cpp.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)
from swesmith.bug_gen.procedural.cpp.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
)
from swesmith.bug_gen.procedural.cpp.replace_strings import (
    ReplaceStringTypoModifier,
)

MODIFIERS_CPP: list[ProceduralModifier] = [
    # Control flow modifiers
    ControlIfElseInvertModifier(likelihood=0.5),
    ControlShuffleLinesModifier(likelihood=0.5),
    # Remove modifiers
    RemoveAssignModifier(likelihood=0.5),
    RemoveConditionalModifier(likelihood=0.5),
    RemoveLoopModifier(likelihood=0.5),
    # Operation modifiers
    OperationBreakChainsModifier(likelihood=0.5),
    OperationChangeConstantsModifier(likelihood=0.5),
    OperationChangeModifier(likelihood=0.5),
    OperationFlipOperatorModifier(likelihood=0.5),
    OperationSwapOperandsModifier(likelihood=0.5),
    # String modifiers
    ReplaceStringTypoModifier(likelihood=0.5),
]
