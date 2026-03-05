from __future__ import annotations


class UrgencySignal:
    """
    Global affective urgency signal.

    Properties:
    - Scalar pressure value in [0.0, 1.0]
    - Time-evolving
    - No learning
    - No decision authority
    """

    def __init__(
        self,
        *,
        initial: float = 0.0,
        rise_rate: float = 0.0,
        decay_rate: float = 0.0,
        max_value: float = 1.0,
        enabled: bool = False,
    ) -> None:
        self.value: float = float(initial)
        self.rise_rate: float = float(rise_rate)
        self.decay_rate: float = float(decay_rate)
        self.max_value: float = float(max_value)
        self.enabled: bool = bool(enabled)

    # --------------------------------------------------
    # Core dynamics
    # --------------------------------------------------

    def step(self, dt: float) -> float:
        """
        Advance urgency one timestep.

        Rules:
        - If enabled and rise_rate > 0 → urgency rises
        - If decay_rate > 0 → urgency decays
        - Always clamped to [0, max_value]

        Returns:
        - Current urgency value
        """

        if not self.enabled:
            self._apply_decay(dt)
            return self.value

        if self.rise_rate > 0.0:
            self.value += self.rise_rate * dt

        self._apply_decay(dt)
        self._clamp()
        return self.value

    # --------------------------------------------------
    # Controls
    # --------------------------------------------------

    def set(self, value: float) -> None:
        """Hard set urgency value (debug / tests only)."""
        self.value = float(value)
        self._clamp()

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def reset(self) -> None:
        self.value = 0.0

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _apply_decay(self, dt: float) -> None:
        if self.decay_rate > 0.0 and self.value > 0.0:
            self.value -= self.decay_rate * dt

    def _clamp(self) -> None:
        if self.value < 0.0:
            self.value = 0.0
        elif self.value > self.max_value:
            self.value = self.max_value

    # --------------------------------------------------
    # Introspection
    # --------------------------------------------------

    def snapshot(self) -> dict:
        """
        Lightweight read-only view for runtime / tracing.
        """
        return {
            "value": self.value,
            "enabled": self.enabled,
            "rise_rate": self.rise_rate,
            "decay_rate": self.decay_rate,
        }
