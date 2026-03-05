from __future__ import annotations

from typing import Any, Iterable, List

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.consolidation.episode_consolidator import ConsolidationRecord


def _snapshot(obj: Any) -> Any:
    if hasattr(obj, "__dict__"):
        return {
            k: _snapshot(v)
            for k, v in obj.__dict__.items()
        }
    if isinstance(obj, dict):
        return {k: _snapshot(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_snapshot(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_snapshot(v) for v in obj)
    return obj


def _canonical(records: Iterable[ConsolidationRecord]) -> List[Any]:
    return [
        _snapshot(r)
        for r in sorted(records, key=lambda r: r.episode_id)
    ]


class _ReplaySource:
    def __init__(self, replay: EpisodeReplay):
        self._replay = replay

    @property
    def episodes(self):
        return self._replay.episodes()


def test_sleep_replay_idempotence() -> None:
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    tracker.start_episode(step=0)
    trace.record_decision(
        episode_id=0,
        step=2,
        winner="A",
        confidence=0.8,
    )
    tracker.close_episode(step=3)

    tracker.start_episode(step=4)
    trace.record_decision(
        episode_id=1,
        step=6,
        winner="B",
        confidence=0.7,
    )
    tracker.close_episode(step=7)

    episodes = tracker.episodes
    assert len(episodes) == 2

    replay_1 = EpisodeReplay(
        episodes=episodes,
        episode_trace=trace,
    )
    records_1 = EpisodeConsolidator(
        source=_ReplaySource(replay_1)
    ).consolidate()

    replay_2 = EpisodeReplay(
        episodes=episodes,
        episode_trace=trace,
    )
    records_2 = EpisodeConsolidator(
        source=_ReplaySource(replay_2)
    ).consolidate()

    replay_3 = EpisodeReplay(
        episodes=list(reversed(episodes)),
        episode_trace=trace,
    )
    records_3 = EpisodeConsolidator(
        source=_ReplaySource(replay_3)
    ).consolidate()

    assert _canonical(records_1) == _canonical(records_2)
    assert _canonical(records_1) == _canonical(records_3)
#validated##