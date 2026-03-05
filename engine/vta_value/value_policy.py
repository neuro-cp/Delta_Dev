from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class ValuePolicy:
    """
    Policy governing updates to the tonic VTA value signal.

    CONTRACT:
    - Slow, bounded updates only
    - Step-gated (not wall-clock)
    - No phasic jumps
    - No learning
    - No authority
    """

    # -------------------------
    # Update constraints
    # -------------------------

    max_step_change: float = 0.1      # absolute cap per update
    min_interval_steps: int = 10      # steps between updates

    # -------------------------
    # Safety flags
    # -------------------------

    enabled: bool = True

    # -------------------------
    # Internal bookkeeping
    # -------------------------

    _last_update_step: Optional[int] = None

    # ============================================================
    # Policy API
    # ============================================================

    def evaluate(
        self,
        *,
        current_value: float,
        delta: float,
        current_step: int,
    ) -> Tuple[bool, float, str]:
        """
        Evaluate a proposed value change.

        Returns:
            (accepted, resulting_value, reason)
        """

        if not self.enabled:
            return False, current_value, "policy_disabled"

        if self._last_update_step is not None:
            if (current_step - self._last_update_step) < self.min_interval_steps:
                return False, current_value, "interval_gate"

        # Clamp delta magnitude (no phasic jumps)
        if delta > self.max_step_change:
            delta = self.max_step_change
        elif delta < -self.max_step_change:
            delta = -self.max_step_change

        new_value = _clamp(current_value + delta)

        self._last_update_step = current_step
        return True, new_value, "accepted"

    # ============================================================
    # Lifecycle
    # ============================================================

    def reset(self) -> None:
        """Reset policy state (used on runtime reset)."""
        self._last_update_step = None
