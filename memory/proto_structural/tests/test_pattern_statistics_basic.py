from __future__ import annotations

from memory.proto_structural.pattern_statistics import PatternStatisticsBuilder
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_pattern_statistics_basic() -> None:
    sig_a = EpisodeSignature(
        length_steps=10,
        event_count=2,
        event_types=frozenset({"A"}),
        region_ids=frozenset({"R1"}),
        transition_counts=(("A", "A", 1),),
    )

    sig_b = EpisodeSignature(
        length_steps=12,
        event_count=3,
        event_types=frozenset({"B"}),
        region_ids=frozenset({"R2"}),
        transition_counts=(("B", "B", 2),),
    )

    record = PatternRecord(
        pattern_counts={
            sig_a: 3,
            sig_b: 1,
        }
    )

    builder = PatternStatisticsBuilder()
    stats = builder.build(record=record)

    assert stats.total_signatures == 2
    assert stats.total_occurrences == 4

    assert stats.counts[sig_a] == 3
    assert stats.counts[sig_b] == 1

    assert abs(stats.relative_frequency[sig_a] - 0.75) < 1e-9
    assert abs(stats.relative_frequency[sig_b] - 0.25) < 1e-9

    assert stats.ordered_signatures[0] == sig_a
    assert stats.ordered_signatures[1] == sig_b