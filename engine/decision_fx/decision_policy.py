# engine/decision_fx/decision_policy.py
from __future__ import annotations

from typing import Dict, Any, Optional


class DecisionPolicy:
    """
    Decision → Policy translator.

    ROLE:
    - Convert a latched decision + dominance + relief + bias
      into an explicit, read-only policy object.
    - No learning
    - No mutation of runtime state
    - Deterministic and side-effect free

    INPUTS (expected shapes):
    - decision_state:
        {
            "time": float,
            "step": int,
            "winner": str,
            "delta_dominance": float,
            "relief": float,
        }

    - dominance:
        { channel_name: dominance_value }
        (read-only; optional, future-facing)

    - bias_map:
        { channel_name: bias_value }

    OUTPUT (policy dict):
        {
            "mode": str,
            "winner": Optional[str],
            "confidence": float,
            "commit": bool,
            "suppress_alternatives": bool,
            "bias_snapshot": Dict[str, float],
        }
    """

    # ---------------------------------------------------------
    # Tunables (policy-space, NOT dynamics)
    # ---------------------------------------------------------
    CONFIDENCE_CLIP = 1.0
    MIN_CONFIDENCE = 0.0

    COMMIT_CONFIDENCE_THRESHOLD = 0.55
    SUPPRESS_CONFIDENCE_THRESHOLD = 0.65

    @classmethod
    def compute(
        cls,
        *,
        decision_state: Optional[Dict[str, Any]],
        dominance: Optional[Dict[str, float]] = None,
        bias_map: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Produce a policy snapshot from the current decision state.

        - dominance is accepted for interface stability and future use
        - dominance is NOT used for policy strength in this version
        """

        bias_map = bias_map or {}

        # -----------------------------------------------------
        # No decision → neutral / exploratory mode
        # -----------------------------------------------------
        if not decision_state:
            return {
                "mode": "explore",
                "winner": None,
                "confidence": 0.0,
                "commit": False,
                "suppress_alternatives": False,
                "bias_snapshot": dict(bias_map),
            }

        # -----------------------------------------------------
        # Extract decision signals
        # -----------------------------------------------------
        winner = decision_state.get("winner")
        delta = float(decision_state.get("delta_dominance", 0.0))
        relief = float(decision_state.get("relief", 0.0))

        # -----------------------------------------------------
        # Confidence model (simple, monotonic, bounded)
        # -----------------------------------------------------
        # Interpretation:
        # - dominance → decisiveness
        # - relief → downstream permissiveness
        #
        # Confidence is policy strength, not probability.
        confidence = delta * relief
        confidence = max(cls.MIN_CONFIDENCE, min(cls.CONFIDENCE_CLIP, confidence))

        # -----------------------------------------------------
        # Policy flags
        # -----------------------------------------------------
        commit = confidence >= cls.COMMIT_CONFIDENCE_THRESHOLD
        suppress = confidence >= cls.SUPPRESS_CONFIDENCE_THRESHOLD

        # -----------------------------------------------------
        # Mode selection
        # -----------------------------------------------------
        mode = "commit" if commit else "deliberate"

        # -----------------------------------------------------
        # Assemble policy (read-only snapshot)
        # -----------------------------------------------------
        return {
            "mode": mode,
            "winner": winner,
            "confidence": confidence,
            "commit": commit,
            "suppress_alternatives": suppress,
            "bias_snapshot": dict(bias_map),
        }
