from __future__ import annotations

from typing import Dict, Iterable

from engine.cognition.hypothesis import Hypothesis


class HypothesisBias:
    """
    Phase 6.6: Bounded hypothesis-based interpretive bias.

    Scope:
    - Produces gain-only bias signals
    - Bias is reversible and bounded
    - No authority, no decisions

    Forbidden:
    - Threshold modification
    - Latch access
    - Direct region or assembly mutation
    """

    def __init__(
        self,
        *,
        bias_gain: float = 0.05,
        max_bias: float = 0.2,
    ) -> None:
        if bias_gain < 0.0:
            raise ValueError("bias_gain must be non-negative")
        if max_bias < 0.0:
            raise ValueError("max_bias must be non-negative")

        self.bias_gain = float(bias_gain)
        self.max_bias = float(max_bias)

    # ------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------

    def compute_bias(
        self,
        *,
        stabilized_hypotheses: Iterable[Hypothesis],
    ) -> Dict[str, float]:
        """
        Compute bias contributions from stabilized hypotheses.

        Returns:
            Dict[str, float] mapping hypothesis_id -> bias_value
        """
        bias: Dict[str, float] = {}

        for h in stabilized_hypotheses:
            if not h.active:
                continue

            # bias proportional to activation, but bounded
            value = self.bias_gain * h.activation

            if value > self.max_bias:
                value = self.max_bias

            if value > 0.0:
                bias[h.hypothesis_id] = value

        return bias
