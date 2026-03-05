from __future__ import annotations

from typing import Dict, Literal


class AttentionBiasAggregator:
    """
    Aggregates attention gain biases from multiple sources.

    CONTRACT:
    - Bias-only (suggestive, never applied)
    - Deterministic
    - Bounded and reversible
    - No mutation of AttentionField
    """

    def __init__(
        self,
        *,
        mode: Literal["multiplicative", "additive"] = "multiplicative",
        min_gain: float = 0.0,
        max_gain: float = 2.0,
    ) -> None:
        self._mode = mode
        self._min = min_gain
        self._max = max_gain

    def aggregate(
        self,
        *,
        base_gains: Dict[str, float],
        bias_sources: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        """
        Combine base attention gains with bias sources.

        Parameters
        ----------
        base_gains:
            Raw attention gains keyed by attention key.
        bias_sources:
            Mapping: source_name -> {key -> bias_value}

        Returns
        -------
        Dict[str, float]
            Bias-adjusted gains (suggestions only).
        """

        result: Dict[str, float] = {}

        for key, base in base_gains.items():
            value = base

            for source_bias in bias_sources.values():
                bias = source_bias.get(key, 1.0)

                if self._mode == "multiplicative":
                    value *= bias
                elif self._mode == "additive":
                    value += bias - 1.0

            # Clamp to bounds
            value = max(self._min, min(self._max, value))
            result[key] = value

        return result
