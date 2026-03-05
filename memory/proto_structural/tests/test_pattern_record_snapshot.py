# memory/proto_structural/tests/test_pattern_record_snapshot.py

from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_pattern_record_is_immutable_snapshot():
    sig = EpisodeSignature(
        length_steps=1,
        event_count=1,
        event_types=frozenset({"E"}),
        region_ids=frozenset({"R"}),
        transition_counts=(),
    )

    record = PatternRecord(pattern_counts={sig: 1})

    # Snapshot integrity
    assert record.pattern_counts[sig] == 1

    # Ensure no mutation through replacement
    new_counts = dict(record.pattern_counts)
    new_counts[sig] = 2
    assert record.pattern_counts[sig] == 1
