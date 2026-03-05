from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.episode_signature import EpisodeSignature
from memory.proto_structural.pattern_record import PatternRecord


def test_learning_bundle_from_inspection_surface_is_deterministic_and_sane():
    adapter = LearningPipelineInputAdapter()

    # --- semantic activation artifacts (as produced by replay → semantics) ---
    sem_a = SemanticActivationRecord(
        activations={"sem:alpha": 0.4, "sem:beta": 0.2},
        snapshot_index=1,
    )
    sem_b = SemanticActivationRecord(
        activations={"sem:alpha": 0.7},
        snapshot_index=2,
    )

    # --- proto-structural artifacts (as produced by episodic → signatures → accumulator) ---
    sig = EpisodeSignature(
        length_steps=10,
        event_count=3,
        event_types=frozenset({"start", "decision", "close"}),
        region_ids=frozenset({"TRN", "GPi"}),
        transition_counts=(("start", "decision", 1), ("decision", "close", 1)),
    )
    patterns = PatternRecord(pattern_counts={sig: 5})

    # --- build bundle twice with identical content ---
    bundle_a = adapter.from_inspection_surface(
        replay_id="replay:test",
        semantic_activation_records=[sem_a, sem_b],
        pattern_record=patterns,
    )

    bundle_b = adapter.from_inspection_surface(
        replay_id="replay:test",
        semantic_activation_records=[sem_a, sem_b],
        pattern_record=patterns,
    )

    # Determinism / idempotence
    assert bundle_a == bundle_b

    # Sanity checks (no invention)
    assert bundle_a.replay_id == "replay:test"
    assert len(bundle_a.semantic_ids) >= 1
    assert len(bundle_a.semantic_activation_snapshots) == 2
    assert len(bundle_a.pattern_counts) == 1

    # Order invariance on inputs
    bundle_c = adapter.from_inspection_surface(
        replay_id="replay:test",
        semantic_activation_records=[sem_b, sem_a],  # reversed
        pattern_record=patterns,
    )
    assert bundle_a == bundle_c
##validated##