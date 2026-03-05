from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from learning.diffing.learning_bundle_diff import diff_learning_bundles

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_learning_bundle_diff_structural_changes_detected():
    adapter = LearningPipelineInputAdapter()

    sem = SemanticActivationRecord(
        activations={"sem:a": 0.2},
        snapshot_index=1,
    )

    sig1 = EpisodeSignature(
        length_steps=2,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"GPi"}),
        transition_counts=(),
    )
    sig2 = EpisodeSignature(
        length_steps=4,
        event_count=2,
        event_types=frozenset({"start", "close"}),
        region_ids=frozenset({"GPi"}),
        transition_counts=(("start", "close", 1),),
    )

    patterns_a = PatternRecord(pattern_counts={sig1: 1})
    patterns_b = PatternRecord(pattern_counts={sig2: 1})

    bundle_a = adapter.from_inspection_surface(
        replay_id="replay:structural",
        semantic_activation_records=[sem],
        pattern_record=patterns_a,
    )
    bundle_b = adapter.from_inspection_surface(
        replay_id="replay:structural",
        semantic_activation_records=[sem],
        pattern_record=patterns_b,
    )

    diff = diff_learning_bundles(bundle_a, bundle_b)

    structural = diff.summary["structural"]
    assert len(structural.added_signatures) == 1
    assert len(structural.removed_signatures) == 1
