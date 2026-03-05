from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from learning.diffing.learning_bundle_diff import diff_learning_bundles

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_learning_bundle_diff_is_read_only_and_deterministic():
    adapter = LearningPipelineInputAdapter()

    sem1 = SemanticActivationRecord(
        activations={"sem:a": 0.3},
        snapshot_index=1,
    )
    sem2 = SemanticActivationRecord(
        activations={"sem:a": 0.6},
        snapshot_index=2,
    )

    sig = EpisodeSignature(
        length_steps=4,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"GPi"}),
        transition_counts=(),
    )

    patterns = PatternRecord(pattern_counts={sig: 1})

    bundle_a = adapter.from_inspection_surface(
        replay_id="replay:diff",
        semantic_activation_records=[sem1],
        pattern_record=patterns,
    )

    bundle_b = adapter.from_inspection_surface(
        replay_id="replay:diff",
        semantic_activation_records=[sem2],
        pattern_record=patterns,
    )

    # --- run diff twice ---
    diff_1 = diff_learning_bundles(bundle_a, bundle_b)
    diff_2 = diff_learning_bundles(bundle_a, bundle_b)

    # Determinism
    assert diff_1 == diff_2

    # Diff must not mutate inputs
    assert bundle_a.semantic_activation_snapshots == (
        (1, (("sem:a", 0.3),)),
    )
    assert bundle_b.semantic_activation_snapshots == (
        (2, (("sem:a", 0.6),)),
    )
