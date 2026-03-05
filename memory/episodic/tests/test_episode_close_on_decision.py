from __future__ import annotations

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_boundary_policy import EpisodeBoundaryPolicy
from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook


def main() -> None:
    """
    Test: an episode closes when a decision event occurs.

    Verifies:
    - Episode is started implicitly
    - Decision event closes the episode
    - A new episode opens immediately after closure
    """

    # --------------------------------------------------
    # Wiring (explicit)
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    policy = EpisodeBoundaryPolicy(
        close_on_decision=True,
        close_on_working_release=False,
        max_episode_steps=None,
    )

    hook = EpisodeRuntimeHook(
        tracker=tracker,
        boundary_policy=policy,
    )

    # --------------------------------------------------
    # Step 0: runtime begins, no decision
    # --------------------------------------------------
    hook.step(
        step=0,
        time=0.0,
        decision_event=False,
        working_state_active=True,
    )

    assert tracker.has_active_episode()
    first_episode = tracker.active_episode
    first_episode_id = first_episode.episode_id

    # --------------------------------------------------
    # Steps 1–4: episode continues
    # --------------------------------------------------
    for step in range(1, 5):
        hook.step(
            step=step,
            time=step * 0.01,
            decision_event=False,
            working_state_active=True,
        )

        assert tracker.has_active_episode()
        assert tracker.active_episode.episode_id == first_episode_id
        assert not tracker.active_episode.closed

    # --------------------------------------------------
    # Step 5: decision occurs → boundary
    # --------------------------------------------------
    hook.step(
        step=5,
        time=0.05,
        decision_event=True,
        working_state_active=True,
    )

    # --------------------------------------------------
    # Assertions: episode closed
    # --------------------------------------------------
    closed_episode = tracker.last_closed_episode()
    assert closed_episode is not None
    assert closed_episode.episode_id == first_episode_id
    assert closed_episode.closed
    assert closed_episode.end_step == 5

    # --------------------------------------------------
    # Assertions: new episode opened
    # --------------------------------------------------
    assert tracker.has_active_episode()
    assert tracker.active_episode.episode_id != first_episode_id
    assert tracker.active_episode.start_step == 5

    print("PASS: test_episode_close_on_decision")


if __name__ == "__main__":
    main()
