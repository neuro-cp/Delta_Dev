from __future__ import annotations

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_policy import EpisodePolicy
from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook


def test_episode_close_on_boundary():
    """
    An episode should NOT close on decision alone.
    It should close ONLY when an explicit boundary signal occurs.
    """

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodePolicy()
    hook = EpisodeRuntimeHook(
        policy=policy,
        tracker=tracker,
    )

    # ------------------------------------------------------------
    # Step 10: decision occurs → implicit episode starts
    # ------------------------------------------------------------
    hook.step(
        step=10,
        decision_event=True,
        context_shift=False,
    )

    ep = tracker.active_episode()
    assert ep is not None
    assert ep.start_step == 10
    assert ep.has_decision()
    assert ep.decision_step == 10

    # Episode must remain open
    assert tracker.episode_count() == 1

    # ------------------------------------------------------------
    # Step 15: no boundary, no decision → episode remains active
    # ------------------------------------------------------------
    hook.step(
        step=15,
        decision_event=False,
        context_shift=False,
    )

    assert tracker.active_episode() is not None
    assert tracker.episode_count() == 1

    # ------------------------------------------------------------
    # Step 20: explicit boundary → episode closes
    # ------------------------------------------------------------
    hook.step(
        step=20,
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
        "close",
    ]

    assert records[0].step == 10
    assert records[1].step == 10
    assert records[2].step == 20
