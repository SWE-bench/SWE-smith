from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.ruby.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
    GuardClauseInvertModifier,
)
from swesmith.bug_gen.procedural.ruby.nil_introduction import (
    BangMethodStripModifier,
    NilGuardRemovalModifier,
    OrDefaultRemovalModifier,
    OrEqualsRemovalModifier,
    PresenceStripModifier,
    SafeNavigationRemovalModifier,
)
from swesmith.bug_gen.procedural.ruby.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)
from swesmith.bug_gen.procedural.ruby.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
    RemoveRescueEnsureModifier,
)
from swesmith.bug_gen.procedural.ruby.ruby_specific import (
    BlockMutationModifier,
    SymbolStringSwapModifier,
)

MODIFIERS_RUBY: list[ProceduralModifier] = [
    # Standard modifiers (CommonPMs)
    ControlIfElseInvertModifier(likelihood=0.75),
    ControlShuffleLinesModifier(likelihood=0.75),
    OperationChangeModifier(likelihood=0.4),
    OperationFlipOperatorModifier(likelihood=0.4),
    OperationSwapOperandsModifier(likelihood=0.4),
    OperationBreakChainsModifier(likelihood=0.3),
    OperationChangeConstantsModifier(likelihood=0.4),
    RemoveAssignModifier(likelihood=0.25),
    RemoveConditionalModifier(likelihood=0.25),
    RemoveLoopModifier(likelihood=0.25),
    # Ruby-specific
    GuardClauseInvertModifier(likelihood=0.6),
    RemoveRescueEnsureModifier(likelihood=0.4),
    BlockMutationModifier(likelihood=0.4),
    SymbolStringSwapModifier(likelihood=0.5),
    # Nil introduction
    SafeNavigationRemovalModifier(likelihood=0.5),
    OrDefaultRemovalModifier(likelihood=0.4),
    PresenceStripModifier(likelihood=0.5),
    BangMethodStripModifier(likelihood=0.4),
    OrEqualsRemovalModifier(likelihood=0.4),
    NilGuardRemovalModifier(likelihood=0.5),
]
