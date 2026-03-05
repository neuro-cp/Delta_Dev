from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry

from memory.inspection.audit.temporal_coherence_audit import TemporalCoherenceAudit


def test_episode_end_time_before_start_time_detected():
    """
    Audit A2 must detect an Episode whose end_time
    precedes its start_time.
    """

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    # Create episode with illegal temporal ordering
    ep = Episode(
        episode_id=0,
        start_step=10,
        start_time=5.0,
    )
    ep.close(step=20, time=2.0)  # end_time < start_time
    tracker._episodes.append(ep)

    audit = TemporalCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    assert any(
        f.severity == "ERROR"
        and "time" in f.description.lower()
        for f in findings
    )


def test_trace_close_before_start_time_detected():
    """
    Audit A2 must detect a trace close event whose time
    precedes the corresponding trace start event.
    """

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    # Create a valid episode
    ep = Episode(
        episode_id=1,
        start_step=0,
        start_time=5.0,
    )
    tracker._episodes.append(ep)

    # Inject illegal trace ordering (bypassing tracker lifecycle on purpose)
    trace._records.append(
        type(
            "FakeTraceRecord",
            (),
            {
                "episode_id": 1,
                "kind": "start",
                "time": 5.0,
                "step": 10,
            },
        )()
    )

    trace._records.append(
        type(
            "FakeTraceRecord",
            (),
            {
                "episode_id": 1,
                "kind": "close",
                "time": 2.0,  # earlier than start -> illegal
                "step": 20,
            },
        )()
    )

    audit = TemporalCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    assert any(
        f.severity == "ERROR"
        and f.layer == "trace"
        and "trace close precedes trace start" in f.description.lower()
        for f in findings
    )
