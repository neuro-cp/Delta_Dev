from __future__ import annotations

from typing import Dict, Iterable

from memory.semantic_activation.semantic_activation_field import (
    SemanticActivationField,
)
from memory.semantic_activation.semantic_activation_record import (
    SemanticActivationRecord,
)
from memory.semantic_activation.multiscale_record import (
    MultiscaleActivationRecord,
)


class MultiscaleSemanticActivationField:
    """
    Container for multiple semantic activation fields at different timescales.

    CONTRACT:
    - Offline only
    - Deterministic
    - No aggregation or dominance
    - No interpretation
    - Each scale evolves independently
    """

    def __init__(
        self,
        *,
        fields: Dict[str, SemanticActivationField],
    ) -> None:
        if not fields:
            raise ValueError("At least one scale must be provided")
        self._fields = fields

    def ingest(
        self,
        *,
        ontology_terms: Iterable[str],
        snapshot_index: int,
    ) -> None:
        """
        Ingest the same evidence into all timescales.
        """
        for field in self._fields.values():
            field.ingest(
                ontology_terms=ontology_terms,
                snapshot_index=snapshot_index,
            )

    def snapshot(self) -> MultiscaleActivationRecord:
        """
        Snapshot all scales independently.
        """
        records: Dict[str, SemanticActivationRecord] = {
            name: field.snapshot()
            for name, field in self._fields.items()
        }

        # All snapshot indices should match by construction; pick any
        any_record = next(iter(records.values()))

        return MultiscaleActivationRecord(
            activations_by_scale={
                name: rec.activations for name, rec in records.items()
            },
            snapshot_index=any_record.snapshot_index,
        )
