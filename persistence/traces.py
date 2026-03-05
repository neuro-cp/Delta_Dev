# persistence/traces.py
from __future__ import annotations

import math


class ExponentialTrace:
    """
    Slow, bounded persistence trace.

    DESIGN:
    - Additive reinforcement
    - Exponential decay toward 0
    - Hard-bounded to [0, max_value]
    - No learning; this is just a leaky accumulator
    """

    def __init__(
        self,
        decay_tau: float = 30.0,  # seconds
        max_value: float = 1.0,
        min_value: float = 0.0,
    ):
        self.value = 0.0
        self.decay_tau = float(decay_tau)
        self.max_value = float(max_value)
        self.min_value = float(min_value)

        # Safety: ensure bounds make sense
        if self.max_value < self.min_value:
            self.max_value, self.min_value = self.min_value, self.max_value

        self.value = self._clamp(self.value)

    def _clamp(self, x: float) -> float:
        if x < self.min_value:
            return self.min_value
        if x > self.max_value:
            return self.max_value
        return x

    def step(self, dt: float) -> None:
        """
        Exponential decay: value *= exp(-dt/tau)

        If tau is ~0 or dt <= 0, we either clear fast or do nothing.
        """
        dt = float(dt)
        if dt <= 0.0:
            return

        tau = float(self.decay_tau)
        if tau <= 1e-9:
            # effectively instant decay
            self.value = self.min_value
            return

        self.value *= math.exp(-dt / tau)
        self.value = self._clamp(self.value)

    def reinforce(self, amount: float) -> None:
        """
        Additively reinforce the trace (then clamp).
        """
        a = float(amount)
        if a == 0.0:
            return
        self.value = self._clamp(self.value + a)
