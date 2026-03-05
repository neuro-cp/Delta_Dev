from __future__ import annotations

from typing import Dict, Any, Optional

from memory.working_state.working_state import WorkingState
from memory.working_state.working_policy import WorkingPolicy


class WorkingRuntimeHook:
    """
    Runtime integration hook for Working State.

    ROLE:
    - Bridge decision latch output to working-state dynamics
    - Apply WorkingPolicy intent to WorkingState
    - Track hold duration
    - Expose read-only bias hints to downstream systems

    HARD GUARANTEES:
    - Does NOT decide
    - Does NOT override BG
    - Does NOT learn
    - All effects are reversible
    """

    def __init__(
        self,
        *,
        state: Optional[WorkingState] = None,
        policy: Optional[WorkingPolicy] = None,
    ):
        self.state = state or WorkingState()
        self.policy = policy or WorkingPolicy()

        # Number of consecutive steps working state has been engaged
        self._steps_held: int = 0

    # --------------------------------------------------
    # Runtime entry point
    # --------------------------------------------------

    def ingest(
        self,
        *,
        decision_state: Dict[str, Any],
    ) -> None:
        """
        Ingest decision latch output for this timestep.

        Expected decision_state keys:
            {
                "commit": bool,
                "winner": Optional[str],
                "confidence": float,
            }
        """

        intent = self.policy.evaluate(
            decision_state=decision_state,
            working_engaged=self.state.is_engaged(),
            steps_held=self._steps_held if self.state.is_engaged() else None,
        )

        # -------------------------
        # Apply release first
        # -------------------------
        if intent.get("release", False):
            self.state.release()
            self._steps_held = 0

        # -------------------------
        # Apply engage
        # -------------------------
        if intent.get("engage", False):
            channel = intent.get("channel")
            if channel is not None:
                self.state.engage(channel)
                self._steps_held = 0

    # --------------------------------------------------
    # Dynamics step
    # --------------------------------------------------

    def step(self, dt: float) -> None:
        """
        Advance working-state dynamics.
        """
        self.state.step(dt)

        if self.state.is_engaged():
            self._steps_held += 1
        else:
            self._steps_held = 0

    # --------------------------------------------------
    # Read-only exposure
    # --------------------------------------------------

    def is_engaged(self) -> bool:
        return self.state.is_engaged()

    def active_channel(self) -> Optional[str]:
        return self.state.active_channel()

    def strength(self) -> float:
        return self.state.strength()

    def steps_held(self) -> int:
        return self._steps_held

    def suppressive_bias(self) -> Dict[str, float]:
        """
        Return a weak suppressive bias hint for non-active channels.

        This does NOT apply inhibition directly.
        It is an advisory signal for BG or attention systems.
        """
        if not self.state.is_engaged():
            return {}

        active = self.state.active_channel()
        strength = self.state.strength()

        if active is None or strength <= 0.0:
            return {}

        # Simple v0 rule: suppress everything else proportional to strength
        return {
            active: strength
        }

    def snapshot(self) -> Dict[str, Any]:
        """
        Diagnostic snapshot for logging or debugging.
        """
        return {
            "engaged": self.state.is_engaged(),
            "active_channel": self.state.active_channel(),
            "strength": self.state.strength(),
            "steps_held": self._steps_held,
        }

    def reset(self) -> None:
        """
        Hard reset. For testing only.
        """
        self.state.clear()
        self._steps_held = 0
