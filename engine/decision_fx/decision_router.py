# engine/decision_fx/decision_router.py
from __future__ import annotations

from typing import Dict, Any


class DecisionRouter:
    """
    Decision → Effect router.

    ROLE:
    - Translate a DecisionPolicy into concrete, downstream-safe effects.
    - Effects are expressed as INTENT, not force.
    - No mutation of dynamics, no learning, no hidden state.

    DESIGN GUARANTEES:
    - Read-only with respect to BrainRuntime
    - Deterministic
    - Idempotent per step
    - Can be ignored safely by downstream systems

    EXPECTED INPUT (policy dict):
        {
            "mode": str,                       # explore | deliberate | commit
            "winner": Optional[str],
            "confidence": float,               # 0.0–1.0
            "commit": bool,
            "suppress_alternatives": bool,
            "bias_snapshot": Dict[str, float],
        }

    OUTPUT (effect bundle) — MUST match DecisionEffects.apply(**bundle):
        {
            "thalamic_gain": float,
            "region_gain": Dict[str, float],
            "suppress_channels": Dict[str, float],
            "lock_action": bool,
        }
    """

    # ---------------------------------------------------------
    # Tunables (policy-space only)
    # ---------------------------------------------------------
    BASE_THALAMIC_GAIN = 1.0
    MAX_THALAMIC_GAIN = 1.25

    # Mild focus gain applied to the winner region (bounded)
    BASE_FOCUS_GAIN = 1.0
    MAX_FOCUS_GAIN = 1.25
    MIN_CONFIDENCE_FOR_FOCUS = 0.45

    # How hard to damp non-winners (bounded and confidence-scaled)
    SUPPRESSION_GAIN = 0.35

    @classmethod
    def route(cls, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a decision policy into an effect bundle.

        This function never touches runtime state directly.
        """

        mode = str(policy.get("mode", "explore") or "explore")
        winner = policy.get("winner")
        confidence = float(policy.get("confidence", 0.0) or 0.0)
        suppress = bool(policy.get("suppress_alternatives", False))
        bias_snapshot = policy.get("bias_snapshot", {}) or {}

        # -----------------------------------------------------
        # Default (neutral) effects
        # -----------------------------------------------------
        effects: Dict[str, Any] = {
            "thalamic_gain": cls.BASE_THALAMIC_GAIN,
            "region_gain": {},          # per-region multiplicative gain (1.0 == neutral)
            "suppress_channels": {},    # per-channel suppression intent (0.0 == none)
            "lock_action": False,
        }

        # -----------------------------------------------------
        # Thalamic gain modulation
        # -----------------------------------------------------
        if mode in ("deliberate", "commit"):
            gain = cls.BASE_THALAMIC_GAIN + confidence * (
                cls.MAX_THALAMIC_GAIN - cls.BASE_THALAMIC_GAIN
            )
            effects["thalamic_gain"] = min(cls.MAX_THALAMIC_GAIN, gain)

    
        # -----------------------------------------------------
        # Winner focus via TargetMap (winner label -> real regions)
        # -----------------------------------------------------
        if winner and confidence >= cls.MIN_CONFIDENCE_FOR_FOCUS:
            from engine.decision_fx.target_map import TargetMap

            # Conservative: keep router bounded, targets decide "where"
            tm = TargetMap(
                focus_gain=min(
                    cls.MAX_FOCUS_GAIN,
                    cls.BASE_FOCUS_GAIN + confidence * (cls.MAX_FOCUS_GAIN - cls.BASE_FOCUS_GAIN),
                ),
                suppress_gain=1.0,  # router doesn't do region suppression yet
            )

            targets = tm.resolve(winner=winner)

            # Merge region_gain (if multiple targets, keep max gain per region)
            for region, g in targets.region_gain.items():
                prev = float(effects["region_gain"].get(region, 1.0))
                effects["region_gain"][region] = max(prev, float(g))

        # -----------------------------------------------------
        # Suppression of alternatives (bounded, confidence-scaled)
        # -----------------------------------------------------
        if suppress and winner and bias_snapshot:
            for ch in bias_snapshot.keys():
                if ch != winner:
                    effects["suppress_channels"][ch] = cls.SUPPRESSION_GAIN * confidence

        # -----------------------------------------------------
        # Action locking (downstream executive systems)
        # -----------------------------------------------------
        if bool(policy.get("commit", False)):
            effects["lock_action"] = True

        return effects
