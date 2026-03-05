from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from learning.diffing.learning_bundle_diff import diff_learning_bundles

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_learning_bundle_diff_no_difference_when_equal():
    adapter = LearningPipelineInputAdapter()

    sem = SemanticActivationRecord(
        activations={"sem:a": 0.5},
        snapshot_index=1,
    )

    sig = EpisodeSignature(
        length_steps=3,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"GPi"}),
        transition_counts=(),
    )
    patterns = PatternRecord(pattern_counts={sig: 1})

    bundle = adapter.from_inspection_surface(
        replay_id="replay:same",
        semantic_activation_records=[sem],
        pattern_record=patterns,
    )

    diff = diff_learning_bundles(bundle, bundle)

    assert diff.has_difference is False
