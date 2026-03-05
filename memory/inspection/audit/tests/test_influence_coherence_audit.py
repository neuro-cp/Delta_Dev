from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry

from memory.inspection.audit.influence_coherence_audit import InfluenceCoherenceAudit


# ==================================================
# A4.1 Semantic influences an episode that is not closed
# ==================================================

def test_semantic_references_unclosed_episode_detected():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)

    # Episode exists but is NOT closed
    ep = Episode(episode_id=1, start_step=0, start_time=0.0)
    tracker._episodes.append(ep)

    # Minimal fake semantic record
    semantic = type(
        "FakeSemanticRecord",
        (),
        {
            "record_id": "S1",
            "episode_id": 1,
        },
    )()

    semantic_registry = SemanticRegistry(_records=[semantic])

    audit = InfluenceCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    assert any(
        f.layer == "semantic"
        and f.severity == "ERROR"
        and "not closed" in f.description.lower()
        for f in findings
    )


# ==================================================
# A4.2 Drift references missing semantic
# ==================================================

def test_drift_without_semantic_detected():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    drift = type(
        "FakeDriftRecord",
        (),
        {
            "semantic_id": "ghost_semantic",
            "timestamp": 2.0,
        },
    )()

    audit = InfluenceCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[drift],
    )

    findings = audit.run()

    assert any(
        f.layer == "drift"
        and f.severity == "ERROR"
        and "does not exist" in f.description.lower()
        for f in findings
    )


# ==================================================
# A4.3 Consolidation invents episode origin
# ==================================================

def test_consolidated_episode_without_origin_detected():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    # Fake consolidated artifact
    consolidator.consolidate = lambda: [
        type("FakeConsolidated", (), {"episode_id": 999})()
    ]

    audit = InfluenceCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    assert any(
        f.layer == "consolidation"
        and f.severity == "ERROR"
        and "does not exist" in f.description.lower()
        for f in findings
    )
