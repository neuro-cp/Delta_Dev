from __future__ import annotations

from memory.semantic.registry import SemanticRegistry
from memory.semantic.query_interface import SemanticQueryInterface
from memory.semantic.records import (
    SemanticRecord,
    SemanticProvenance,
    SemanticTemporalScope,
    SemanticStatistics,
    SemanticStability,
)


def _make_semantic(i: int) -> SemanticRecord:
    return SemanticRecord(
        semantic_id=f"s{i}",
        policy_version="v0",
        schema_version="v0",
        provenance=SemanticProvenance(
            episode_ids=[i],
            sample_size=1,
        ),
        temporal_scope=SemanticTemporalScope(
            first_observed_step=0,
            last_observed_step=10,
            observation_window=10,
        ),
        pattern_type="frequency",
        pattern_descriptor={"kind": "decision_frequency"},
        statistics=SemanticStatistics(
            count=i + 1,
            frequency=None,
        ),
        stability=SemanticStability(
            support=1.0,
            variance=None,
            decay_rate=None,
        ),
        tags={},
        notes=None,
    )


def test_frequency_summary_is_descriptive_only() -> None:
    records = [_make_semantic(i) for i in range(5)]
    registry = SemanticRegistry.from_records(records)
    query = SemanticQueryInterface(registry)

    result = query.frequency_summary()

    assert result.pattern_type == "frequency"
    assert result.summary["frequency"] == len(records)


def test_count_by_type() -> None:
    records = [_make_semantic(i) for i in range(3)]
    registry = SemanticRegistry.from_records(records)
    query = SemanticQueryInterface(registry)

    result = query.count_by_type("frequency")

    assert result.summary["count"] == 3


def test_presence_check_is_boolean_only() -> None:
    records = [_make_semantic(1)]
    registry = SemanticRegistry.from_records(records)
    query = SemanticQueryInterface(registry)

    assert query.has_pattern("s1") is True
    assert query.has_pattern("missing") is False


def test_query_interface_is_read_only() -> None:
    records = [_make_semantic(1)]
    registry = SemanticRegistry.from_records(records)
    query = SemanticQueryInterface(registry)

    before = registry.records
    _ = query.frequency_summary()
    _ = query.count_by_type("frequency")
    after = registry.records

    assert before == after
