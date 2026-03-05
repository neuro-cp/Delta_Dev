from __future__ import annotations

from typing import Iterable

from engine.cognition.hypothesis import Hypothesis


class HypothesisDynamics:
    """
    Phase 6.2: Internal hypothesis dynamics.

    Scope:
    - Activation persistence
    - Decay over time
    - Deactivation when inactive

    Explicitly forbidden:
    - Runtime coupling
    - Region / assembly access
    - Salience or routing bias
    - Memory or episodic emission
    """

    def __init__(
        self,
        *,
        decay_rate: float = 0.01,
        min_activation: float = 1e-6,
    ) -> None:
        if decay_rate < 0.0:
            raise ValueError("decay_rate must be non-negative")

        self.decay_rate = float(decay_rate)
        self.min_activation = float(min_activation)

    # ------------------------------------------------------------
    # Core dynamics
    # ------------------------------------------------------------

    def step(self, hypotheses: Iterable[Hypothesis]) -> None:
        """
        Advance hypothesis dynamics by one timestep.

        This must be called explicitly.
        """
        for h in hypotheses:
            if not h.active:
                continue

            # exponential-like decay (linear approximation per step)
            h.activation -= self.decay_rate * h.activation

            if h.activation < self.min_activation:
                h.activation = 0.0
                h.active = False
