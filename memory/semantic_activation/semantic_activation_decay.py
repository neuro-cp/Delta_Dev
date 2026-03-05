from __future__ import annotations

import math


class ExponentialDecay:
    """
    Simple exponential decay operator.

    Pure math. No side effects.
    Deterministic.
    """

    def __init__(self, *, half_life: float) -> None:
        if half_life <= 0:
            raise ValueError("half_life must be > 0")
        # decay constant: ln(2) / half_life
        self._k = math.log(2.0) / half_life

    def apply(self, value: float, *, dt: float) -> float:
        """
        Apply exponential decay over time delta dt.

        - value <= 0 → 0.0
        - dt <= 0 → unchanged
        """
        if value <= 0:
            return 0.0
        if dt <= 0:
            return value
        return value * math.exp(-self._k * dt)
