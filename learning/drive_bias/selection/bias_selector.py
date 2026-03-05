from typing import Dict, List
from .bias_selection_policy import BiasSelectionPolicy


class BiasSelector:
    """Offline selection surface (no mutation)."""

    def __init__(self) -> None:
        self._policy = BiasSelectionPolicy()

    def compute_selection(
        self,
        scores: Dict[str, float],
        threshold: float = 0.0,
    ) -> List[str]:
        return self._policy.select(scores=scores, threshold=threshold)
