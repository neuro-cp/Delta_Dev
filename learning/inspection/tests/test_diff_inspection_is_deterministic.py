from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from learning.diffing.learning_bundle_diff import diff_learning_bundles
from learning.inspection.diff_inspection_builder import build_diff_inspection_view

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_diff_inspection_is_deterministic():
    adapter = LearningPipelineInputAdapter()

    sem1 = SemanticActivationRecord(
        activations={"sem:a": 0.1},
        snapshot_index=1,
    )
    sem2 = SemanticActivationRecord(
        activations={"sem:a": 0.3},
        snapshot_index=2,
    )

    sig = EpisodeSignature(
        length_steps=3,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"TRN"}),
        transition_counts=(),
    )
    patterns = PatternRecord(pattern_counts={sig: 1})

    bundle_a = adapter.from_inspection_surface(
        replay_id="replay:inspect",
        semantic_activation_records=[sem1],
        pattern_record=patterns,
    )
    bundle_b = adapter.from_inspection_surface(
        replay_id="replay:inspect",
        semantic_activation_records=[sem2],
        pattern_record=patterns,
    )

    diff = diff_learning_bundles(bundle_a, bundle_b)

    view1 = build_diff_inspection_view(diff)
    view2 = build_diff_inspection_view(diff)

    assert view1 == view2
