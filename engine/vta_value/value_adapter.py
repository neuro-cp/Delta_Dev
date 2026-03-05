from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class ValueAdapter:
    """
    Adapter that applies tonic VTA value to downstream systems.

    Allowed injection targets ONLY:
      - DecisionBias (bias scaling)
      - PFC persistence gain

    Explicitly forbidden:
      - GPi / gate relief
      - Latch thresholds
      - Sustain counters
      - Salience
      - Context memory
      - Urgency / affect
    """

    # -------------------------
    # Injection gains
    # -------------------------

    decision_bias_gain: float = 0.5
    pfc_persistence_gain: float = 0.3

    enabled: bool = True

    # ============================================================
    # Injection API
    # ============================================================

    def apply_to_decision_bias(
        self,
        *,
        value: float,
        bias_map: dict[str, float],
    ) -> dict[str, float]:
        """
        Apply value as a soft bias scaling to DecisionBias.

        CONTRACT:
        - Symmetric scaling only
        - Preserves relative structure
        - Never selects a winner
        """
        if not bias_map:
            return bias_map

        if not self.enabled:
            return dict(bias_map)

        safe_value = _clamp(value)
        scale = 1.0 + (safe_value * self.decision_bias_gain)

        return {
            key: val * scale
            for key, val in bias_map.items()
        }

    def apply_to_pfc_persistence(
        self,
        *,
        value: float,
        base_gain: float,
    ) -> float:
        """
        Apply value as a persistence-supporting gain to PFC.

        CONTRACT:
        - Post-commit support only
        - No working memory creation
        """
        if not self.enabled:
            return base_gain

        safe_value = _clamp(value)
        return base_gain * (1.0 + safe_value * self.pfc_persistence_gain)

    # ============================================================
    # Inspection
    # ============================================================

    def snapshot(self) -> dict[str, float | bool]:
        """
        Inspection-only snapshot.
        """
        return {
            "enabled": self.enabled,
            "decision_bias_gain": self.decision_bias_gain,
            "pfc_persistence_gain": self.pfc_persistence_gain,
        }

    # ============================================================
    # Lifecycle
    # ============================================================

    def reset(self) -> None:
        """No internal state to reset (included for symmetry)."""
        return
