from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay
from memory.episodic.episode_narrator import EpisodeNarrator


def main():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    # --------------------------------------------------
    # Fake runtime sequence
    # --------------------------------------------------

    tracker.start_episode(step=0, reason="initial")

    # long hesitation
    for s in range(1, 120):
        pass

    tracker.mark_decision(step=120, winner="D1", confidence=0.73)

    for s in range(121, 140):
        pass

    tracker.close_episode(step=140, reason="decision_event")

    # --------------------------------------------------
    # Replay + narration
    # --------------------------------------------------

    replay = EpisodeReplay(
        episodes=tracker.all_episodes(),
        trace=trace,
    )

    narrator = EpisodeNarrator()
    narrative = narrator.narrate(replay)

    # --------------------------------------------------
    # Print it like a cognitive diary
    # --------------------------------------------------

    print("\n=== EPISODIC NARRATIVE ===\n")

    for event in narrative:
        print(f"[step {event.step:>4}] {event.message}")

    print("\n=========================\n")


if __name__ == "__main__":
    main()
