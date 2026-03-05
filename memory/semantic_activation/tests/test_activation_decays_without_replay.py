from __future__ import annotations

from memory.semantic_activation.semantic_activation_field import (
    SemanticActivationField,
)
from memory.semantic_activation.semantic_activation_decay import ExponentialDecay


def test_activation_decays_without_replay() -> None:
    decay = ExponentialDecay(half_life=1.0)
    field = SemanticActivationField(decay=decay)

    field.ingest(
        ontology_terms=["decision_silence"],
        snapshot_index=1,
    )

    # advance time with no new evidence
    field.ingest(
        ontology_terms=[],
        snapshot_index=5,
    )

    snap = field.snapshot()

    assert snap.activations["decision_silence"] < 1.0
