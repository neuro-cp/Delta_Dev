from __future__ import annotations

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_learning_input_bundle_fuzzing_is_deterministic_and_safe():
    adapter = LearningPipelineInputAdapter()

    sem1 = SemanticActivationRecord(
        activations={"sem:a": 0.2, "sem:b": 0.1},
        snapshot_index=2,
    )
    sem2 = SemanticActivationRecord(
        activations={"sem:a": 0.5},
        snapshot_index=1,
    )

    # Same multiset, different order
    semantic_order_a = [sem1, sem2]
    semantic_order_b = [sem2, sem1]

    # Duplicate amplification (intentional)
    semantic_with_dupes = [sem1, sem2, sem1]

    sig = EpisodeSignature(
        length_steps=3,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"TRN"}),
        transition_counts=(),
    )
    patterns = PatternRecord(pattern_counts={sig: 2})

    bundle_a = adapter.from_inspection_surface(
        replay_id="replay:fuzz",
        semantic_activation_records=semantic_order_a,
        pattern_record=patterns,
    )

    bundle_b = adapter.from_inspection_surface(
        replay_id="replay:fuzz",
        semantic_activation_records=semantic_order_b,
        pattern_record=patterns,
    )

    bundle_c = adapter.from_inspection_surface(
        replay_id="replay:fuzz",
        semantic_activation_records=semantic_with_dupes,
        pattern_record=patterns,
    )

    # Order invariance (same multiset)
    assert bundle_a == bundle_b
    assert hash(bundle_a) == hash(bundle_b)

    # Duplicate amplification is preserved, not collapsed
    assert bundle_c != bundle_a
    assert len(bundle_c.semantic_ids) > len(bundle_a.semantic_ids)

    # Empty input remains safe
    empty_bundle = adapter.from_inspection_surface(
        replay_id="replay:fuzz",
        semantic_activation_records=None,
        pattern_record=patterns,
    )

    assert empty_bundle.semantic_ids == ()
    assert empty_bundle.semantic_activation_snapshots == ()
##validated##
