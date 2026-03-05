from __future__ import annotations

from typing import List

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_replay import EpisodeReplay
from memory.episodic.signal_snapshot import SignalSnapshot
from memory.episodic.episode_narrator import EpisodeNarrator, NarrativeEvent


def test_salience_is_narrated_within_episode_bounds() -> None:
    """
    Phase 5C certification test.

    Verifies that:
    - A salience signal occurring during an episode
    - Is narrated as a 'signal' NarrativeEvent
    - And appears only within the episode's step bounds

    This test is OFFLINE and READ-ONLY.
    """

    # --------------------------------------------------
    # 1. Create episodic structure
    # --------------------------------------------------

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    # Start episode at step 10
    tracker.start_episode(step=10, tags={"test": True})

    # Simulate a decision at step 30
    tracker.mark_decision(
        step=30,
        winner="A",
        confidence=0.85,
    )

    # Close episode at step 50
    tracker.close_episode(step=50, reason="test_end")

    episodes = tracker.episodes

    # --------------------------------------------------
    # 2. Create a salience-derived SignalSnapshot timeline
    # --------------------------------------------------

    signals: List[SignalSnapshot] = [
        # Outside episode (should NOT appear)
        SignalSnapshot(step=5, salience=0.4),

        # Inside episode (should appear)
        SignalSnapshot(step=20, salience=0.7),
        SignalSnapshot(step=40, salience=0.9),

        # After episode (should NOT appear)
        SignalSnapshot(step=60, salience=0.6),
    ]

    # --------------------------------------------------
    # 3. Replay + narrate
    # --------------------------------------------------

    replay = EpisodeReplay(
        episodes=episodes,
        episode_trace=trace,
        salience_trace=None,  # narration uses SignalSnapshot only
    )

    narrator = EpisodeNarrator()
    narrative: List[NarrativeEvent] = narrator.narrate(
        replay,
        signals=signals,
    )

    # --------------------------------------------------
    # 4. Assertions
    # --------------------------------------------------

    signal_events = [e for e in narrative if e.kind == "signal"]

    # Exactly two signal events should be narrated
    assert len(signal_events) == 2, (
        f"Expected 2 signal events inside episode, got {len(signal_events)}"
    )

    steps = {e.step for e in signal_events}

    # They must be the ones inside the episode bounds
    assert steps == {20, 40}, f"Unexpected signal steps narrated: {steps}"

    # All signal events must belong to episode 0
    assert all(e.episode_id == 0 for e in signal_events)

    # Sanity: episode bounds
    ep = episodes[0]
    for e in signal_events:
        assert ep.start_step <= e.step <= ep.end_step
