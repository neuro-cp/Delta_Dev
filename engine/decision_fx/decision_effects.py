# engine/decision_fx/decision_effects.py
from __future__ import annotations

from typing import Dict, Any, Optional


class DecisionEffects:
    """
    Decision → Runtime effect applier.

    ROLE:
    - Apply *bounded*, *reversible* effects produced by DecisionRouter.
    - Effects are gain modifiers only — no state mutation, no learning.
    - Designed to sit *after* decision formation and *before* action execution.

    DESIGN GUARANTEES:
    - No hard overrides (multiplicative / additive gains only)
    - Effects decay naturally unless reasserted
    - Safe to disable entirely
    - Deterministic per step

    EXPECTED EFFECT BUNDLE:
        {
            "thalamic_gain": float,
            "cortical_focus": Optional[str],
            "suppress_channels": Dict[str, float],
            "lock_action": bool,
        }
    """

    # ---------------------------------------------------------
    # Tunables (effect-space)
    # ---------------------------------------------------------
    MAX_GAIN = 1.5
    MIN_GAIN = 0.25

    SUPPRESSION_FLOOR = 0.3

    def __init__(self) -> None:
        # Ephemeral per-step state
        self._last_effects: Optional[Dict[str, Any]] = None

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def apply(
        self,
        *,
        thalamic_gain: float,
        region_gain: Dict[str, float],
        suppress_channels: Dict[str, float],
        lock_action: bool = False,
    ) -> Dict[str, Any]:
        """
        Apply effects in a read-only, gain-only fashion.

        Returns a normalized effect snapshot for observability.
        """

        # -----------------------------
        # Thalamic gain (global gate)
        # -----------------------------
        tg = max(self.MIN_GAIN, min(self.MAX_GAIN, thalamic_gain))

        # -----------------------------
        # Region gain (focus routing)
        # -----------------------------
        rg_out: Dict[str, float] = {}
        for region, gain in (region_gain or {}).items():
            rg_out[region] = max(self.MIN_GAIN, min(self.MAX_GAIN, gain))

        # -----------------------------
        # Suppression (non-winners)
        # -----------------------------
        sup_out: Dict[str, float] = {}
        for ch, strength in (suppress_channels or {}).items():
            sup_out[ch] = max(self.SUPPRESSION_FLOOR, 1.0 - strength)

        snapshot = {
            "thalamic_gain": tg,
            "region_gain": rg_out,
            "suppress_channels": sup_out,
            "lock_action": bool(lock_action),
        }

        self._last_effects = snapshot
        return snapshot

    # ---------------------------------------------------------
    # Diagnostics
    # ---------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return self._last_effects or {}
