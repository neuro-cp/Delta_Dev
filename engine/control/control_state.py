# engine/control/control_state.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal


ControlPhase = Literal[
    "pre-decision",
    "commit",
    "post-commit",
    "cooldown",
]


@dataclass(frozen=True)
class ControlState:
    """
    Read-only snapshot of the system's control mode.

    This is NOT a policy and MUST NOT mutate dynamics.
    It exists to describe system phase and commitment state.
    """

    # --- time ---
    step: int
    t_runtime: float

    # --- phase ---
    phase: ControlPhase

    # --- decision ---
    decision_made: bool
    decision_winner: Optional[str]

    # --- commitment ---
    committed: bool
    suppress_alternatives: bool

    # --- working state ---
    working_state_active: bool

    # --- regulation ---
    fatigue_flag: bool
    saturation_flag: bool

    def summary(self) -> str:
        return (
            f"ControlState(step={self.step}, "
            f"t={self.t_runtime:.3f}, "
            f"phase={self.phase}, "
            f"decision={self.decision_made}, "
            f"winner={self.decision_winner}, "
            f"committed={self.committed}, "
            f"suppress={self.suppress_alternatives}, "
            f"working={self.working_state_active})"
        )

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "time": self.t_runtime,
            "phase": self.phase,
            "decision_made": self.decision_made,
            "decision_winner": self.decision_winner,
            "committed": self.committed,
            "suppress_alternatives": self.suppress_alternatives,
            "working_state_active": self.working_state_active,
            "fatigue_flag": self.fatigue_flag,
            "saturation_flag": self.saturation_flag,
        }
