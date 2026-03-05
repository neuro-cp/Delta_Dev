from __future__ import annotations

from learning.execution.learning_execution_observer import observe_learning_execution
from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_learning_execution_observer_is_read_only():
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

    bundle_before = adapter.from_inspection_surface(
        replay_id="replay:exec",
        semantic_activation_records=[sem],
        pattern_record=patterns,
    )

    bundle_after = bundle_before

    before_snapshot = bundle_before.semantic_activation_snapshots

    _ = observe_learning_execution(
        input_bundle_before=bundle_before,
        input_bundle_after=bundle_after,
    )

    after_snapshot = bundle_before.semantic_activation_snapshots
    assert before_snapshot == after_snapshot
