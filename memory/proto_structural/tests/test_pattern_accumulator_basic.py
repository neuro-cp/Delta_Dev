# memory/proto_structural/tests/test_pattern_accumulator_basic.py

from memory.proto_structural.pattern_accumulator import PatternAccumulator
from memory.proto_structural.episode_signature import EpisodeSignature


def test_pattern_accumulator_counts_recurrence():
    sig = EpisodeSignature(
        length_steps=4,
        event_count=2,
        event_types=frozenset({"A"}),
        region_ids=frozenset({"R"}),
        transition_counts=(),
    )

    acc = PatternAccumulator()
    acc.ingest([sig, sig, sig])

    record = acc.snapshot()

    assert record.pattern_counts[sig] == 3
