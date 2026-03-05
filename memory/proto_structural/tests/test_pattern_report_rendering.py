# memory/proto_structural/tests/test_pattern_report_rendering.py

from memory.proto_structural.pattern_report import PatternReportBuilder
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def test_pattern_report_renders_descriptive_entries():
    sig = EpisodeSignature(
        length_steps=7,
        event_count=2,
        event_types=frozenset({"A", "B"}),
        region_ids=frozenset({"R1"}),
        transition_counts=(("A", "B", 1),),
    )

    record = PatternRecord(pattern_counts={sig: 4})

    builder = PatternReportBuilder()
    report = builder.build(record=record)

    assert len(report.entries) == 1
    entry = report.entries[0]

    assert entry["occurrences"] == 4
    assert isinstance(entry["signature"], tuple)
