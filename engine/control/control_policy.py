# engine/control/control_policy.py
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from engine.control.control_state import ControlState

if TYPE_CHECKING:
    from engine.runtime import BrainRuntime

class ControlPolicy:
    """
    Derives ControlState from the runtime.
    This class MUST NOT modify runtime behavior.
    """

    @staticmethod
    def compute(runtime: BrainRuntime) -> ControlState:
        decision = runtime.decision_state

        decision_made = decision is not None
        decision_winner: Optional[str] = None
        committed = False
        suppress = False

        if decision_made:
            decision_winner = decision.get("winner")
            committed = bool(decision.get("commit", False))
            suppress = bool(decision.get("suppress_alternatives", False))

        # Working state (if present)
        working_active = False
        if hasattr(runtime, "working_state"):
            working_active = runtime.working_state.is_active()

        return ControlState(
            step=runtime.step,
            t_runtime=runtime.t,
            decision_made=decision_made,
            decision_winner=decision_winner,
            committed=committed,
            suppress_alternatives=suppress,
            working_state_active=working_active,
            fatigue_flag=False,
            saturation_flag=False,
        )
