from __future__ import annotations

import math


class SupportToActivation:
    """
    Deterministic offline adapter mapping support -> activation.

    Design constraints:
    - monotonic
    - bounded in [0, max_activation]
    - stateless
    - no learning
    - no history
    """

    def __init__(
        self,
        *,
        gain: float = 1.0,
        midpoint: float = 0.5,
        max_activation: float = 1.0,
    ) -> None:
        self.gain = float(gain)
        self.midpoint = float(midpoint)
        self.max_activation = float(max_activation)

    def map(self, support: float) -> float:
        """
        Map support -> activation using a smooth bounded function.

        Logistic curve centered at midpoint with defensive
        numerical clamping to prevent overflow.
        """
        # Defensive handling of non-finite input
        if not math.isfinite(support):
            return 0.0

        x = self.gain * (support - self.midpoint)

        # Numerical safety: beyond this range the logistic is
        # already saturated to machine precision
        if x >= 60.0:
            return self.max_activation
        if x <= -60.0:
            return 0.0

        act = 1.0 / (1.0 + math.exp(-x))

        # Final hard bounds (paranoia, preserves contract)
        if act < 0.0:
            return 0.0
        if act > self.max_activation:
            return self.max_activation
        return act
### passed all tests ###