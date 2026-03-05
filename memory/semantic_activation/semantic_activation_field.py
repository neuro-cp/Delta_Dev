from __future__ import annotations

from typing import Dict, Iterable, Optional

from memory.semantic_activation.semantic_activation_record import (
    SemanticActivationRecord,
)
from memory.semantic_activation.semantic_activation_decay import ExponentialDecay


class SemanticActivationField:
    """
    Read-only semantic activation accumulator.

    CONTRACT:
    - Offline only
    - Deterministic
    - No runtime edges
    - No decision influence
    - No interpretation
    """

    def __init__(
        self,
        *,
        decay: ExponentialDecay,
    ) -> None:
        self._decay = decay
        self._levels: Dict[str, float] = {}
        self._last_index: Optional[int] = None

    def ingest(
        self,
        *,
        ontology_terms: Iterable[str],
        snapshot_index: int,
    ) -> None:
        """
        Accumulate activation from an offline snapshot.

        Semantics:
        - Existing activation decays based on Δt
        - Each observed ontology term contributes +1.0
        - No normalization or sparsity applied here
        """
        if self._last_index is None:
            dt = 0
        else:
            dt = max(0, snapshot_index - self._last_index)

        # Decay existing activation
        for key, value in list(self._levels.items()):
            self._levels[key] = self._decay.apply(value, dt=dt)

        # Accumulate new evidence
        for term in ontology_terms:
            self._levels[term] = self._levels.get(term, 0.0) + 1.0

        self._last_index = snapshot_index

    def snapshot(self) -> SemanticActivationRecord:
        """
        Return an immutable snapshot of current activation state.

        snapshot_index:
        - last ingested index
        - -1 if no ingestion has occurred
        """
        return SemanticActivationRecord(
            activations=dict(self._levels),
            snapshot_index=self._last_index if self._last_index is not None else -1,
        )
