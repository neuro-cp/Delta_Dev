from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from learning.diffing.learning_bundle_diff import diff_learning_bundles

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_learning_bundle_diff_semantic_changes_detected():
    adapter = LearningPipelineInputAdapter()

    sem_a = SemanticActivationRecord(
        activations={"sem:a": 0.1},
        snapshot_index=1,
    )
    sem_b = SemanticActivationRecord(
        activations={"sem:b": 0.3},
        snapshot_index=1,
    )

    sig = EpisodeSignature(
        length_steps=2,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"TRN"}),
        transition_counts=(),
    )
    patterns = PatternRecord(pattern_counts={sig: 1})

    bundle_a = adapter.from_inspection_surface(
        replay_id="replay:semantic",
        semantic_activation_records=[sem_a],
        pattern_record=patterns,
    )
    bundle_b = adapter.from_inspection_surface(
        replay_id="replay:semantic",
        semantic_activation_records=[sem_b],
        pattern_record=patterns,
    )

    diff = diff_learning_bundles(bundle_a, bundle_b)

    semantic = diff.summary["semantic"]
    assert "sem:b" in semantic.added_terms
    assert "sem:a" in semantic.removed_terms
