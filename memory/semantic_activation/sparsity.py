from __future__ import annotations

from typing import Dict


class ActivationSparsifier:
    """
    Math-only sparsity / energy control operators for semantic activation.

    CONTRACT:
    - Pure functions
    - No state
    - No thresholds tied to meaning
    - No ranking or selection
    - Deterministic
    - Safe to remove
    """

    @staticmethod
    def soft_threshold(
        activations: Dict[str, float],
        *,
        epsilon: float,
    ) -> Dict[str, float]:
        """
        Apply soft thresholding:
        values <= epsilon are removed,
        values > epsilon are shifted down by epsilon.

        This reduces density without introducing winners.
        """
        if not activations:
            return {}

        if epsilon <= 0:
            return dict(activations)

        sparse: Dict[str, float] = {}
        for k, v in activations.items():
            if v > epsilon:
                sparse[k] = v - epsilon

        return sparse

    @staticmethod
    def energy_budget(
        activations: Dict[str, float],
        *,
        budget: float,
    ) -> Dict[str, float]:
        """
        Enforce a total energy budget by uniform scaling.

        If total mass <= budget, returns unchanged.
        If total mass > budget, scales all values proportionally.

        This preserves relative structure.
        """
        if not activations:
            return {}

        if budget <= 0:
            return {}

        total = sum(activations.values())
        if total <= budget:
            return dict(activations)

        scale = budget / total
        return {k: v * scale for k, v in activations.items()}
