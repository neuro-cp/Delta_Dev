from __future__ import annotations

from memory.episodic.episode_structure import Episode
from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.episode_signature import EpisodeSignature
from memory.proto_structural.pattern_record import PatternRecord

from learning.inputs.learning_input_builder import LearningInputBuilder


def test_learning_input_bundle_idempotent():
    builder = LearningInputBuilder()

    ep1 = Episode(episode_id=2, start_step=0, start_time=0.0)
    ep1.close(step=10, time=1.0)

    ep2 = Episode(episode_id=1, start_step=0, start_time=0.0)
    ep2.close(step=12, time=1.2)

    sem1 = SemanticActivationRecord(
        activations={"sem:alpha": 0.5, "sem:beta": 0.2},
        snapshot_index=2,
    )
    sem2 = SemanticActivationRecord(
        activations={"sem:alpha": 0.7},
        snapshot_index=1,
    )

    sig = EpisodeSignature(
        length_steps=10,
        event_count=3,
        event_types=frozenset({"start", "decision", "close"}),
        region_ids=frozenset({"TRN", "GPi"}),
        transition_counts=(("start", "decision", 1), ("decision", "close", 1)),
    )
    pattern = PatternRecord(pattern_counts={sig: 4})

    bundle_a = builder.build(
        replay_id="r1",
        episodes=[ep1, ep2],
        semantic_records=[sem1, sem2],
        pattern_record=pattern,
        semantic_episode_pairs=[("sem:alpha", 2), ("sem:alpha", 1)],
    )

    bundle_b = builder.build(
        replay_id="r1",
        episodes=[ep1, ep2],
        semantic_records=[sem1, sem2],
        pattern_record=pattern,
        semantic_episode_pairs=[("sem:alpha", 2), ("sem:alpha", 1)],
    )

    assert bundle_a == bundle_b
