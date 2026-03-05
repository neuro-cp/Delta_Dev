from __future__ import annotations

from typing import Dict, Any, Optional


class WorkingPolicy:
    """
    Policy governing entry, maintenance, and release of working state.

    PURPOSE:
    - Decide WHEN working state should engage or disengage
    - Interpret decision latch signals
    - Enforce guardrails against re-entry storms or chatter

    HARD CONSTRAINTS:
    - No state mutation
    - No time integration
    - No learning
    - No BG authority

    This policy produces INTENT only.
    """

    def __init__(
        self,
        *,
        min_confidence: float = 0.5,
        allow_override: bool = False,
        release_on_new_decision: bool = True,
        auto_release: bool = True,
        max_hold_steps: Optional[int] = 800,
    ):
        """
        Parameters
        ----------
        min_confidence:
            Minimum decision confidence required to engage working state.

        allow_override:
            Whether a new decision may override an active working state.

        release_on_new_decision:
            If True, a new decision causes release before optional re-engage.

        auto_release:
            If True, working state may be released automatically
            (requires external step counting).

        max_hold_steps:
            Optional maximum number of steps to hold working state
            before auto-release.
        """
        self.min_confidence = float(min_confidence)
        self.allow_override = bool(allow_override)
        self.release_on_new_decision = bool(release_on_new_decision)
        self.auto_release = bool(auto_release)
        self.max_hold_steps = int(max_hold_steps) if max_hold_steps is not None else None

    # --------------------------------------------------
    # Core policy decision
    # --------------------------------------------------

    def evaluate(
        self,
        *,
        decision_state: Dict[str, Any],
        working_engaged: bool,
        steps_held: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate whether to engage or release working state.

        Returns an INTENT dict:
            {
                "engage": bool,
                "release": bool,
                "channel": Optional[str],
            }
        """
        intent = {
            "engage": False,
            "release": False,
            "channel": None,
        }

        commit = bool(decision_state.get("commit", False))
        winner = decision_state.get("winner")
        confidence = float(decision_state.get("confidence", 0.0))

        # ----------------------------------------------
        # Auto-release (global) — allow release even if commit sticks
        # ----------------------------------------------
        if (
            self.auto_release
            and working_engaged
            and self.max_hold_steps is not None
            and steps_held is not None
            and steps_held >= self.max_hold_steps
        ):
            intent["release"] = True
            return intent

        # ----------------------------------------------
        # No decision → no policy action
        # ----------------------------------------------
        if not commit or winner is None:
            return intent

        # ----------------------------------------------
        # Confidence gate
        # ----------------------------------------------
        if confidence < self.min_confidence:
            return intent

        # ----------------------------------------------
        # Decision present
        # ----------------------------------------------
        if not working_engaged:
            # Fresh engage
            intent["engage"] = True
            intent["channel"] = winner
            return intent

        # ----------------------------------------------
        # Working state already engaged
        # ----------------------------------------------
        if not self.allow_override:
            return intent

        # Override path
        if self.release_on_new_decision:
            intent["release"] = True

        intent["engage"] = True
        intent["channel"] = winner
        return intent
