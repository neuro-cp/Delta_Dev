from __future__ import annotations

import copy

from memory.semantic.frequency_builder import FrequencySemanticBuilder
from memory.semantic.registry import SemanticRegistry
from memory.consolidation.episode_consolidator import ConsolidationRecord


def _make_record(
    *,
    episode_id: int,
    decision_count: int,
    ended_by_decision: bool,
) -> ConsolidationRecord:
    return ConsolidationRecord(
        episode_id=episode_id,
        start_step=0,
        end_step=10,
        duration_steps=10,
        start_time=0.0,
        end_time=0.0,
        duration_time=0.0,
        decision_count=decision_count,
        winner=None,
        confidence=None,
        decision_steps=[],
        decision_times=[],
        inter_decision_intervals_steps=[],
        inter_decision_intervals_time=[],
        ended_by_decision=ended_by_decision,
        ended_by_timeout=not ended_by_decision,
        tags={},
    )


def test_registry_is_immutable() -> None:
    builder = FrequencySemanticBuilder()

    records = [
        _make_record(episode_id=1, decision_count=1, ended_by_decision=True),
        _make_record(episode_id=2, decision_count=0, ended_by_decision=False),
    ]

    semantics = builder.build(records)
    registry = SemanticRegistry.from_records(semantics)

    # Defensive copy on access
    fetched = registry.records
    fetched.append("corruption")

    # Original registry remains unchanged
    assert len(registry.records) == len(semantics)


def test_builder_registry_integration_is_lossless() -> None:
    builder = FrequencySemanticBuilder()

    records = [
        _make_record(episode_id=i, decision_count=i % 2, ended_by_decision=(i % 2 == 1))
        for i in range(10)
    ]

    semantics = builder.build(records)
    registry = SemanticRegistry.from_records(semantics)

    # Registry contains exactly what builder produced
    assert registry.records == semantics

    # Summary counts are correct
    summary = registry.summary()
    assert summary["frequency"] == len(semantics)


def test_semantic_layer_is_discardable() -> None:
    """
    Semantic memory must be safe to discard and rebuild
    without affecting consolidation records.
    """
    builder = FrequencySemanticBuilder()

    records = [
        _make_record(episode_id=1, decision_count=1, ended_by_decision=True),
        _make_record(episode_id=2, decision_count=0, ended_by_decision=False),
    ]

    records_copy = copy.deepcopy(records)

    # Build semantics
    semantics = builder.build(records)
    registry = SemanticRegistry.from_records(semantics)

    # Discard everything semantic
    del semantics
    del registry

    # Rebuild from same inputs
    semantics_again = builder.build(records)

    # Consolidation records unchanged
    assert records == records_copy
    assert semantics_again == builder.build(records)
