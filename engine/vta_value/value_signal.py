from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValueSignal:
    """
    Tonic VTA value signal.

    This represents slow, bounded meaning / outcome bias.
    It does NOT represent reward, urgency, learning, or prediction error.

    Design invariants:
    - Read-only with respect to decision commitment
    - No phasic components
    - No learning
    - No direct motor or gating influence
    """

    # -------------------------
    # Core signal state
    # -------------------------

    value: float = 0.0

    # -------------------------
    # Bounds (hard safety rails)
    # -------------------------

    min_value: float = -1.0
    max_value: float = 1.0

    # -------------------------
    # Dynamics
    # -------------------------

    decay_tau: float = 5.0      # slower than salience, faster than memory
    enabled: bool = True

    # -------------------------
    # Internal bookkeeping
    # -------------------------

    _last_update_time: Optional[float] = None

    # ============================================================
    # Public API
    # ============================================================

    def reset(self) -> None:
        """Hard reset to baseline (used on runtime reset)."""
        self.value = 0.0
        self._last_update_time = None

    def get(self) -> float:
        """Read current tonic value."""
        return self.value

    def set(self, new_value: float) -> None:
        """
        Set value directly (policy-gated elsewhere).

        This method enforces hard bounds only.
        """
        if not self.enabled:
            return

        self.value = self._clamp(new_value)

    def step(self, dt: float) -> None:
        """
        Apply passive decay toward baseline.

        No learning, no reinforcement, no coupling.
        """
        if not self.enabled:
            return

        if self.decay_tau <= 0.0:
            return

        # Exponential decay toward zero
        decay_factor = dt / self.decay_tau
        self.value *= max(0.0, 1.0 - decay_factor)

    # ============================================================
    # Internals
    # ============================================================

    def _clamp(self, x: float) -> float:
        if x < self.min_value:
            return self.min_value
        if x > self.max_value:
            return self.max_value
        return x
