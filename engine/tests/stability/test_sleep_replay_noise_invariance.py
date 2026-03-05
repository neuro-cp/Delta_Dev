from __future__ import annotations

from typing import Any, List

from memory.episodic.episode_trace import EpisodeTrace, EpisodeTraceRecord
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.episodic.episode_structure import Episode


class _ReplaySource:
    def __init__(self, episodes: List[Episode]) -> None:
        self._episodes = list(episodes)

    @property
    def episodes(self) -> List[Episode]:
        return list(self._episodes)


def _canonical(records: List[Any]) -> List[Any]:
    return sorted(
        [r.__dict__ for r in records],
        key=lambda r: r["episode_id"],
    )


def test_sleep_replay_noise_invariance() -> None:
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    # Episode 1
    tracker.start_episode(step=0)
    trace._records.append(
        EpisodeTraceRecord(
            event="noise",
            episode_id=0,
            step=1,
            payload={"junk": True},
        )
    )
    trace.record_decision(
        episode_id=0,
        step=2,
        winner="A",
        confidence=0.9,
    )
    tracker.close_episode(step=3)

    # Episode 2
    tracker.start_episode(step=4)
    trace.record_decision(
        episode_id=1,
        step=6,
        winner="B",
        confidence=0.7,
    )
    trace._records.insert(
        0,
        EpisodeTraceRecord(
            event="noise",
            episode_id=1,
            step=5,
            payload={"junk": True},
        ),
    )
    tracker.close_episode(step=7)

    episodes = tracker.episodes
    assert len(episodes) == 2

    replay_1 = EpisodeReplay(
        episodes=episodes,
        episode_trace=trace,
    )
    records_1 = EpisodeConsolidator(
        source=_ReplaySource(replay_1.episodes())
    ).consolidate()
    canon_1 = _canonical(records_1)

    replay_2 = EpisodeReplay(
        episodes=list(reversed(episodes)),
        episode_trace=trace,
    )
    records_2 = EpisodeConsolidator(
        source=_ReplaySource(replay_2.episodes())
    ).consolidate()
    canon_2 = _canonical(records_2)

    assert canon_1 == canon_2
#validated##