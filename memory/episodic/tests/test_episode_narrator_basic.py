from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay
from memory.episodic.episode_narrator import EpisodeNarrator


def test_episode_narrator_basic_flow():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    # Simulate a simple episode
    tracker.start_episode(step=10, reason="initial")
    tracker.mark_decision(step=42, winner="D2", confidence=0.61)
    tracker.close_episode(step=50, reason="decision_event")

    replay = EpisodeReplay(
        episodes=tracker.all_episodes(),
        trace=trace,
    )

    narrator = EpisodeNarrator()
    narrative = narrator.narrate(replay)

    # Basic sanity checks
    assert len(narrative) >= 3

    messages = [e.message for e in narrative]

    assert any("started at step 10" in m for m in messages)
    assert any("winner=D2" in m for m in messages)
    assert any("closed at step 50" in m for m in messages)
    assert any("ended with 1 decision" in m for m in messages)
