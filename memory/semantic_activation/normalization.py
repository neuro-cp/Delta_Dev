from __future__ import annotations

from typing import Dict


class ActivationNormalizer:
    """
    Stateless normalization operators for semantic activation fields.

    CONTRACT:
    - Pure functions
    - No state
    - No thresholds
    - No authority
    - Safe to remove
    """

    @staticmethod
    def max_normalize(activations: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize activations by the maximum value.

        If all values are zero or dict is empty,
        returns a shallow copy unchanged.
        """
        if not activations:
            return {}

        max_val = max(activations.values())
        if max_val <= 0:
            return dict(activations)

        return {k: v / max_val for k, v in activations.items()}

    @staticmethod
    def sum_normalize(activations: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize activations so total mass sums to 1.0.

        If sum is zero or dict is empty,
        returns a shallow copy unchanged.
        """
        if not activations:
            return {}

        total = sum(activations.values())
        if total <= 0:
            return dict(activations)

        return {k: v / total for k, v in activations.items()}
