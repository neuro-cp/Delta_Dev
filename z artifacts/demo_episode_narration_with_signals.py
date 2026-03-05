from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay
from memory.episodic.episode_narrator import EpisodeNarrator
from memory.episodic.signal_snapshot import SignalSnapshot


def main():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    # --------------------------------------------------
    # Simulated runtime behavior
    # --------------------------------------------------
    tracker.start_episode(step=0, reason="initial")

    # Decision happens later
    tracker.mark_decision(step=50, winner="D1", confidence=0.72)
    tracker.close_episode(step=60, reason="decision_event")

    # --------------------------------------------------
    # Offline signal snapshots (context, not events)
    # --------------------------------------------------
    signals = [
        SignalSnapshot(step=10, salience=0.30),
        SignalSnapshot(step=25, salience=0.42),
        SignalSnapshot(step=35, value=0.60),
        SignalSnapshot(step=45, urgency=0.28),
    ]

    replay = EpisodeReplay(
        episodes=tracker.all_episodes(),
        trace=trace,
    )

    narrator = EpisodeNarrator()
    narrative = narrator.narrate(replay, signals=signals)

    # --------------------------------------------------
    # Print narrative
    # --------------------------------------------------
    print("\n=== EPISODIC NARRATIVE (WITH SIGNALS) ===\n")

    for event in narrative:
        print(f"[step {event.step:>4}] {event.message}")

    print("\n=======================================\n")


if __name__ == "__main__":
    main()
