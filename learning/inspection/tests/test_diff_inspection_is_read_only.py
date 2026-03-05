from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from learning.diffing.learning_bundle_diff import diff_learning_bundles
from learning.inspection.diff_inspection_builder import build_diff_inspection_view

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_diff_inspection_is_read_only():
    adapter = LearningPipelineInputAdapter()

    sem = SemanticActivationRecord(
        activations={"sem:a": 0.2},
        snapshot_index=1,
    )

    sig = EpisodeSignature(
        length_steps=2,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"GPi"}),
        transition_counts=(),
    )
    patterns = PatternRecord(pattern_counts={sig: 1})

    bundle = adapter.from_inspection_surface(
        replay_id="replay:inspect",
        semantic_activation_records=[sem],
        pattern_record=patterns,
    )

    diff = diff_learning_bundles(bundle, bundle)
    before = bundle.semantic_activation_snapshots

    _ = build_diff_inspection_view(diff)

    after = bundle.semantic_activation_snapshots
    assert before == after
