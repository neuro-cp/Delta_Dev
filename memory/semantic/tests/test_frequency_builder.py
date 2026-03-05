from __future__ import annotations

import copy

from memory.semantic.frequency_builder import FrequencySemanticBuilder
from memory.consolidation.episode_consolidator import ConsolidationRecord


def _make_record(
    *,
    episode_id: int,
    decision_count: int,
    ended_by_decision: bool,
    start_step: int = 0,
    end_step: int = 10,
) -> ConsolidationRecord:
    return ConsolidationRecord(
        episode_id=episode_id,
        start_step=start_step,
        end_step=end_step,
        duration_steps=end_step - start_step,
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


def test_frequency_builder_basic_counts() -> None:
    records = [
        _make_record(episode_id=1, decision_count=1, ended_by_decision=True),
        _make_record(episode_id=2, decision_count=0, ended_by_decision=False),
        _make_record(episode_id=3, decision_count=2, ended_by_decision=True),
        _make_record(episode_id=4, decision_count=0, ended_by_decision=False),
    ]

    builder = FrequencySemanticBuilder()
    semantics = builder.build(records)

    by_name = {s.pattern_descriptor: s for s in semantics}

    assert by_name["ended_by_decision"].statistics.count == 2
    assert by_name["ended_by_decision"].statistics.frequency == 0.5

    assert by_name["silent_episode"].statistics.count == 2
    assert by_name["silent_episode"].statistics.frequency == 0.5

    assert by_name["multi_decision_episode"].statistics.count == 1
    assert by_name["multi_decision_episode"].statistics.frequency == 0.25


def test_frequency_builder_deterministic() -> None:
    records = [
        _make_record(episode_id=i, decision_count=i % 2, ended_by_decision=(i % 2 == 1))
        for i in range(10)
    ]

    builder = FrequencySemanticBuilder()

    first = builder.build(records)
    second = builder.build(records)

    assert first == second


def test_frequency_builder_does_not_mutate_inputs() -> None:
    records = [
        _make_record(episode_id=1, decision_count=1, ended_by_decision=True),
        _make_record(episode_id=2, decision_count=0, ended_by_decision=False),
    ]

    records_copy = copy.deepcopy(records)

    builder = FrequencySemanticBuilder()
    _ = builder.build(records)

    assert records == records_copy


def test_frequency_builder_empty_input() -> None:
    builder = FrequencySemanticBuilder()
    semantics = builder.build([])

    assert semantics == []
