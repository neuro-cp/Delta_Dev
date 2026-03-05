from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay
from memory.episodic.episode_narrator import EpisodeNarrator
from memory.episodic.signal_snapshot import SignalSnapshot


def test_episode_narrator_with_signals():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    # --------------------------------------------------
    # Simulate episode
    # --------------------------------------------------
    tracker.start_episode(step=0, reason="initial")

    tracker.mark_decision(step=50, winner="D1", confidence=0.72)
    tracker.close_episode(step=60, reason="decision_event")

    replay = EpisodeReplay(
        episodes=tracker.all_episodes(),
        trace=trace,
    )

    # --------------------------------------------------
    # Inject offline signal snapshots
    # --------------------------------------------------
    signals = [
        SignalSnapshot(step=10, salience=0.35),
        SignalSnapshot(step=30, value=0.60),
        SignalSnapshot(step=49, urgency=0.28),
    ]

    narrator = EpisodeNarrator()
    narrative = narrator.narrate(replay, signals=signals)

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    kinds = [e.kind for e in narrative]
    messages = [e.message for e in narrative]

    # Signal events must appear
    assert "signal" in kinds
    assert any("salience" in m for m in messages)
    assert any("value" in m for m in messages)
    assert any("urgency" in m for m in messages)

    # Decision must still appear
    assert any("Decision at step 50" in m for m in messages)

    # Summary must still appear
    assert any("ended with 1 decision" in m for m in messages)
