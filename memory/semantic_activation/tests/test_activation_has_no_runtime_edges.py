from __future__ import annotations

from memory.semantic_activation.semantic_activation_field import (
    SemanticActivationField,
)
from memory.semantic_activation.semantic_activation_decay import ExponentialDecay


def test_activation_has_no_runtime_edges() -> None:
    """
    Structural invariant: construction and use must not
    import runtime, cognition, sleep, or control.
    """
    decay = ExponentialDecay(half_life=5.0)
    field = SemanticActivationField(decay=decay)

    field.ingest(
        ontology_terms=["temporal_recurrence"],
        snapshot_index=1,
    )

    snap = field.snapshot()
    assert isinstance(snap.activations, dict)
