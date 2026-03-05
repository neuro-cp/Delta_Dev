from __future__ import annotations

"""
Phase 7 — Episodic Replay (Read-Only) Tests

This test suite verifies that EpisodeReplay:
- does not mutate episodes
- does not reorder history
- does not create or close episodes
- does not inject decisions
"""

from copy import deepcopy

from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_replay import EpisodeReplay


def _build_trace() -> EpisodeTrace:
    trace = EpisodeTrace()

    # Episode 1 (closed, with decision)
    ep1 = Episode(
        episode_id=1,
        start_step=0,
        start_time=0.0,
    )
    ep1.mark_decision(
        step=10,
        time=0.1,
        winner="A",
        confidence=0.8,
    )
    ep1.close(step=20, time=0.2)
    trace._episodes.append(ep1)

    # Episode 2 (closed, no decision)
    ep2 = Episode(
        episode_id=2,
        start_step=21,
        start_time=0.21,
    )
    ep2.close(step=40, time=0.4)
    trace._episodes.append(ep2)

    # Episode 3 (active)
    ep3 = Episode(
        episode_id=3,
        start_step=41,
        start_time=0.41,
    )
    trace._episodes.append(ep3)

    return trace


def test_replay_does_not_mutate_trace() -> None:
    trace = _build_trace()
    snapshot = deepcopy(trace._episodes)

    replay = EpisodeReplay(trace)

    # Access everything
    _ = replay.episodes()
    _ = replay.closed_episodes()
    _ = replay.active_episode()
    _ = list(replay.iter_episodes())
    _ = list(replay.iter_closed())
    _ = replay.episodes_with_decisions()
    _ = list(replay.iter_decision_events())
    _ = replay.summary()

    # Assert nothing changed
    assert trace._episodes == snapshot


def test_replay_projection_is_read_only() -> None:
    trace = _build_trace()
    snapshot = deepcopy(trace._episodes)

    replay = EpisodeReplay(trace)

    lengths = replay.project(
        lambda ep: ep.duration_steps,
        closed_only=True,
    )

    assert lengths == [20, 19]  # (20-0), (40-21)
    assert trace._episodes == snapshot


def test_replay_preserves_order() -> None:
    trace = _build_trace()
    replay = EpisodeReplay(trace)

    ids = [ep.episode_id for ep in replay.iter_episodes()]
    assert ids == [1, 2, 3]


def test_replay_handles_no_decisions() -> None:
    trace = EpisodeTrace()

    ep = Episode(
        episode_id=1,
        start_step=0,
        start_time=0.0,
    )
    ep.close(step=10, time=0.1)
    trace._episodes.append(ep)

    replay = EpisodeReplay(trace)

    assert replay.episodes_with_decisions() == []
    assert list(replay.iter_decision_events()) == []
