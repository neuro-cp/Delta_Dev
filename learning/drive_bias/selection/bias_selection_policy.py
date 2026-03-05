from typing import Dict, List


class BiasSelectionPolicy:
    """Pure, deterministic selection policy."""

    def select(
        self,
        scores: Dict[str, float],
        threshold: float = 0.0,
    ) -> List[str]:
        # Filter by threshold
        filtered = {k: v for k, v in scores.items() if v >= threshold}

        # Deterministic ordering: highest score first, tie-break by id
        ordered = sorted(
            filtered.items(),
            key=lambda item: (-item[1], item[0])
        )

        return [proposal_id for proposal_id, _ in ordered]
