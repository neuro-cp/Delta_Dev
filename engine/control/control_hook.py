# engine/control/control_hook.py
from __future__ import annotations

from typing import Optional

from engine.control.control_policy import ControlPolicy
from engine.control.control_state import ControlState


class ControlHook:
    """
    Read-only control-state capture hook.

    Called once per runtime step AFTER:
      - decision latch evaluation
      - decision FX application
      - salience / context modulation

    NEVER mutates runtime state.
    """

    @staticmethod
    def compute(runtime) -> Optional[ControlState]:
        """
        Compute and return a read-only ControlState snapshot.
        """

        # ---------------- decision state ----------------
        decision = runtime.get_decision_state() if hasattr(runtime, "get_decision_state") else None
        decision_made = decision is not None
        decision_winner = decision.get("winner") if decision else None

        # ---------------- commitment ----------------
        committed = bool(decision_made)
        suppress_alternatives = False
        if hasattr(runtime, "decision_bias") and decision_made:
            suppress_alternatives = True

        # ---------------- working state ----------------
        working_state_active = False
        if hasattr(runtime, "pfc_adapter"):
            working_state_active = runtime.pfc_adapter.is_engaged()

        # ---------------- regulation flags (placeholders, descriptive only) ----------------
        fatigue_flag = False
        saturation_flag = False

        # ---------------- phase determination ----------------
        if not decision_made:
            phase = "pre-decision"
        elif committed and runtime.step_count == decision.get("step"):
            phase = "commit"
        elif committed:
            phase = "post-commit"
        else:
            phase = "cooldown"

        return ControlState(
            step=runtime.step_count,
            t_runtime=runtime.time,
            phase=phase,
            decision_made=decision_made,
            decision_winner=decision_winner,
            committed=committed,
            suppress_alternatives=suppress_alternatives,
            working_state_active=working_state_active,
            fatigue_flag=fatigue_flag,
            saturation_flag=saturation_flag,
        )
