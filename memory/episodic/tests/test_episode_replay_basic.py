from __future__ import annotations

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay


def main() -> None:
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace)

    # Episode 0
    tracker.start_episode(step=0, reason="start")
    tracker.mark_decision(step=5, winner="D1")
    tracker.close_episode(step=6, reason="decision")

    # Episode 1
    tracker.start_episode(step=10, reason="start")
    tracker.mark_decision(step=12, winner="D2")
    tracker.close_episode(step=15, reason="decision")

    # --------------------------------------------------
    # Replay snapshot (STRUCTURE + TRACE, read-only)
    # --------------------------------------------------
    replay = EpisodeReplay(
        episodes=tracker.episodes,
        trace=trace,
    )

    # Structural assertions
    eps = replay.episodes()
    assert len(eps) == 2

    ep0, ep1 = eps
    assert ep0.episode_id == 0
    assert ep1.episode_id == 1

    # Trace-backed assertions
    decisions = list(replay.iter_decision_events())
    assert any(d["winner"] == "D1" for d in decisions)
    assert any(d["winner"] == "D2" for d in decisions)

    print("PASS: test_episode_replay_basic")


if __name__ == "__main__":
    main()
