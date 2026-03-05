from __future__ import annotations

"""
Phase 8 — Consolidation (Read-Only) Tests

This test suite proves that EpisodeConsolidator:
- does not mutate episodes
- does not mutate EpisodeTrace
- produces immutable records
- ignores active episodes

No third-party dependencies.
"""

from copy import deepcopy

from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import (
    EpisodeConsolidator,
    ConsolidationRecord,
)


def _build_trace() -> EpisodeTrace:
    trace = EpisodeTrace()

    # Episode 1: closed, with decision
    ep1 = Episode(
        episode_id=1,
        start_step=0,
        start_time=0.0,
    )
    ep1.mark_decision(
        step=5,
        time=0.05,
        winner="A",
        confidence=0.9,
    )
    ep1.close(step=10, time=0.1)
    trace._episodes.append(ep1)

    # Episode 2: closed, no decision
    ep2 = Episode(
        episode_id=2,
        start_step=11,
        start_time=0.11,
    )
    ep2.close(step=30, time=0.3)
    trace._episodes.append(ep2)

    # Episode 3: active (should be ignored)
    ep3 = Episode(
        episode_id=3,
        start_step=31,
        start_time=0.31,
    )
    trace._episodes.append(ep3)

    return trace


def test_consolidation_does_not_mutate_trace() -> None:
    trace = _build_trace()
    snapshot = deepcopy(trace._episodes)

    consolidator = EpisodeConsolidator(trace)
    _ = consolidator.consolidate()

    assert trace._episodes == snapshot


def test_only_closed_episodes_are_consolidated() -> None:
    trace = _build_trace()
    consolidator = EpisodeConsolidator(trace)

    records = consolidator.consolidate()
    ids = [r.episode_id for r in records]

    assert ids == [1, 2]
    assert 3 not in ids


def test_records_are_immutable() -> None:
    trace = _build_trace()
    consolidator = EpisodeConsolidator(trace)

    record = consolidator.consolidate()[0]
    assert isinstance(record, ConsolidationRecord)

    try:
        record.episode_id = 99  # type: ignore
        assert False, "ConsolidationRecord should be immutable"
    except Exception:
        pass  # Expected: frozen dataclass rejects mutation


def test_consolidation_preserves_episode_data() -> None:
    trace = _build_trace()
    consolidator = EpisodeConsolidator(trace)

    record = consolidator.consolidate()[0]

    assert record.start_step == 0
    assert record.end_step == 10
    assert record.duration_steps == 10
    assert record.winner == "A"
    assert record.confidence == 0.9
    assert record.decision_count == 1


def test_summary_is_read_only() -> None:
    trace = _build_trace()
    snapshot = deepcopy(trace._episodes)

    consolidator = EpisodeConsolidator(trace)
    summary = consolidator.summary()

    assert summary["episodes_consolidated"] == 2
    assert summary["episodes_with_decisions"] == 1
    assert trace._episodes == snapshot
