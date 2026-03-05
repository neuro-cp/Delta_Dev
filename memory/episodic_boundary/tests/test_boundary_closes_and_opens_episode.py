from __future__ import annotations

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook
from memory.episodic_boundary.boundary_event import BoundaryEvent


def test_boundary_event_closes_and_opens_episode() -> None:
    """
    Invariant:
    One close BoundaryEvent must:
    - close the current episode
    - immediately open a new episode
    - record both actions in the EpisodeTrace
    """

    # --------------------------------------------------
    # Setup episodic core
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    hook = EpisodeRuntimeHook(tracker=tracker)

    # --------------------------------------------------
    # Step 0: runtime starts, episode must exist
    # --------------------------------------------------
    hook.step(step=0, boundary_events=[])

    assert tracker.has_active_episode()
    first_episode_start = tracker.active_start_step
    assert first_episode_start == 0

    # --------------------------------------------------
    # Step 1: boundary declares close
    # --------------------------------------------------
    close_event = BoundaryEvent(
        step=1,
        reason="test_boundary",
    )

    hook.step(
        step=1,
        boundary_events=[close_event],
    )

    # --------------------------------------------------
    # Assertions: lifecycle state
    # --------------------------------------------------
    assert tracker.has_active_episode()
    second_episode_start = tracker.active_start_step

    # New episode must start at the same step the old one closed
    assert second_episode_start == 1
    assert second_episode_start != first_episode_start

    # --------------------------------------------------
    # Trace invariants (authoritative)
    # --------------------------------------------------
    records = trace.records()
    events = [r.event for r in records]

    # One implicit start at step 0
    # One close at step 1
    # One start at step 1
    assert events.count("start") == 2
    assert events.count("close") == 1

    # Optional but strong: ordering check
    assert events == ["start", "close", "start"]