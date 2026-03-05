from __future__ import annotations

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.consolidation.episode_consolidator import EpisodeConsolidator


def test_consolidation_derives_intervals_correctly() -> None:
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace)

    # Start a new episode
    tracker.start_episode(step=0, reason="test_start")

    # Three decisions at known steps
    tracker.mark_decision(step=5, winner="A", confidence=0.9)
    tracker.mark_decision(step=12, winner="A", confidence=0.85)
    tracker.mark_decision(step=20, winner="A", confidence=0.8)

    # Close episode
    tracker.close_episode(step=25, reason="test_close")

    consolidator = EpisodeConsolidator(tracker)
    records = consolidator.consolidate()

    assert len(records) == 1
    record = records[0]

    # Raw decision data
    assert record.decision_steps == [5, 12, 20]

    # Derived temporal intervals
    assert record.inter_decision_intervals_steps == [7, 8]

    # Termination classification
    assert record.ended_by_decision is True
    assert record.ended_by_timeout is False
