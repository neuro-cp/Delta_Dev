from __future__ import annotations

from memory.semantic_activation.semantic_activation_decay import ExponentialDecay
from memory.semantic_activation.semantic_activation_field import (
    SemanticActivationField,
)
from memory.semantic_activation.multiscale_field import (
    MultiscaleSemanticActivationField,
)


def test_fast_and_slow_scales_diverge_over_time() -> None:
    fast = SemanticActivationField(
        decay=ExponentialDecay(half_life=1.0)
    )
    slow = SemanticActivationField(
        decay=ExponentialDecay(half_life=10.0)
    )

    multi = MultiscaleSemanticActivationField(
        fields={
            "fast": fast,
            "slow": slow,
        }
    )

    # initial evidence
    multi.ingest(
        ontology_terms=["x"],
        snapshot_index=0,
    )

    # advance time without new evidence
    multi.ingest(
        ontology_terms=[],
        snapshot_index=5,
    )

    snap = multi.snapshot()

    fast_val = snap.activations_by_scale["fast"]["x"]
    slow_val = snap.activations_by_scale["slow"]["x"]

    assert slow_val > fast_val


def test_scales_are_independent() -> None:
    fast = SemanticActivationField(
        decay=ExponentialDecay(half_life=1.0)
    )
    slow = SemanticActivationField(
        decay=ExponentialDecay(half_life=10.0)
    )

    multi = MultiscaleSemanticActivationField(
        fields={
            "fast": fast,
            "slow": slow,
        }
    )

    multi.ingest(
        ontology_terms=["a"],
        snapshot_index=0,
    )

    snap = multi.snapshot()

    assert "a" in snap.activations_by_scale["fast"]
    assert "a" in snap.activations_by_scale["slow"]


def test_single_scale_matches_raw_field_behavior() -> None:
    raw = SemanticActivationField(
        decay=ExponentialDecay(half_life=2.0)
    )

    multi = MultiscaleSemanticActivationField(
        fields={
            "only": raw,
        }
    )

    raw.ingest(
        ontology_terms=["z"],
        snapshot_index=0,
    )
    multi.ingest(
        ontology_terms=["z"],
        snapshot_index=0,
    )

    raw_snap = raw.snapshot()
    multi_snap = multi.snapshot()

    assert multi_snap.activations_by_scale["only"] == raw_snap.activations
