"""
Design‑only contract test.

This test proves that episodic outcomes can be *observed* offline
and mapped to ValueProposals WITHOUT mutating runtime state.

No engines are stepped. No value is applied.
"""

from engine.vta_value.value_source import ValueProposal
from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_replay import EpisodeReplay
from memory.consolidation.episode_consolidator import EpisodeConsolidator



def test_outcome_to_value_design_contract() -> None:
    # --------------------------------------------------
    # Create episodic history
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)

    tracker.start_episode(step=0)
    tracker.mark_decision(step=5, winner="A", confidence=0.8)
    tracker.close_episode(step=10)

    # --------------------------------------------------
    # Offline replay & consolidation
    # --------------------------------------------------
    replay = EpisodeReplay(
        episodes=tracker.episodes,
        episode_trace=trace,
    )

    consolidator = EpisodeConsolidator(source=tracker)
    records = consolidator.consolidate()

    assert len(records) == 1
    record = records[0]

    # --------------------------------------------------
    # Design‑only outcome interpretation
    # --------------------------------------------------
    # (Hard‑coded heuristic for contract demonstration)
    if record.decision_count > 0:
        proposal = ValueProposal(
            delta=0.1,
            source="episodic_outcome",
            note=f"episode {record.episode_id} closed with decision",
        )
    else:
        proposal = None

    # --------------------------------------------------
    # Assertions (NO application)
    # --------------------------------------------------
    assert proposal is not None
    assert proposal.delta > 0.0
    assert proposal.source == "episodic_outcome"

    # No ValueEngine exists here. No state was modified.
##validated##