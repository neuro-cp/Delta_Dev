from __future__ import annotations

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_policy import EpisodePolicy
from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook


def test_multiple_decisions_single_episode():
    """
    Multiple decisions occurring before an explicit boundary
    must be recorded inside a single episode.

    Decisions must NOT implicitly close or split episodes.
    """

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodePolicy()
    hook = EpisodeRuntimeHook(
        policy=policy,
        tracker=tracker,
    )

    # ------------------------------------------------------------
    # Step 10: first decision → implicit episode start
    # ------------------------------------------------------------
    hook.step(
        step=10,
        decision_event=True,
        context_shift=False,
    )

    ep = tracker.active_episode()
    assert ep is not None
    assert ep.start_step == 10
    assert ep.decision_count() == 1
    assert tracker.episode_count() == 1

    # ------------------------------------------------------------
    # Step 20: second decision → same episode
    # ------------------------------------------------------------
    hook.step(
        step=20,
        decision_event=True,
        context_shift=False,
    )

    ep = tracker.active_episode()
    assert ep is not None
    assert ep.start_step == 10
    assert ep.decision_count() == 2
    assert tracker.episode_count() == 1

    # ------------------------------------------------------------
    # Step 30: explicit boundary → episode closes
    # ------------------------------------------------------------
    hook.step(
        step=30,
        decision_event=False,
        context_shift=True,
    )

    assert tracker.active_episode() is None
    assert tracker.episode_count() == 1

    # ------------------------------------------------------------
    # Trace integrity
    # ------------------------------------------------------------
    records = trace.records()
    assert [r.event for r in records] == [
        "start",
        "decision",
        "decision",
        "close",
    ]

    assert records[0].step == 10
    assert records[1].step == 10
    assert records[2].step == 20
    assert records[3].step == 30
