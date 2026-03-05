
from __future__ import annotations

from memory.semantic_activation.semantic_activation_field import (
    SemanticActivationField,
)
from memory.semantic_activation.semantic_activation_decay import ExponentialDecay


def test_activation_accumulates_from_replay() -> None:
    decay = ExponentialDecay(half_life=10.0)
    field = SemanticActivationField(decay=decay)

    field.ingest(
        ontology_terms=["structural_frequency", "temporal_persistence"],
        snapshot_index=1,
    )
    field.ingest(
        ontology_terms=["structural_frequency"],
        snapshot_index=2,
    )

    snap = field.snapshot()

    assert snap.activations["structural_frequency"] > 1.0
    assert snap.activations["temporal_persistence"] > 0.0
