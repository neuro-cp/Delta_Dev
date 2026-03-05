from __future__ import annotations

from learning.execution.learning_execution_observer import observe_learning_execution
from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_learning_execution_observer_is_deterministic():
    adapter = LearningPipelineInputAdapter()

    sem1 = SemanticActivationRecord(
        activations={"sem:a": 0.1},
        snapshot_index=1,
    )
    sem2 = SemanticActivationRecord(
        activations={"sem:b": 0.3},
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

    bundle_before = adapter.from_inspection_surface(
        replay_id="replay:exec",
        semantic_activation_records=[sem1],
        pattern_record=patterns,
    )

    bundle_after = adapter.from_inspection_surface(
        replay_id="replay:exec",
        semantic_activation_records=[sem2],
        pattern_record=patterns,
    )

    result_a = observe_learning_execution(
        input_bundle_before=bundle_before,
        input_bundle_after=bundle_after,
    )

    result_b = observe_learning_execution(
        input_bundle_before=bundle_before,
        input_bundle_after=bundle_after,
    )

    assert result_a == result_b
