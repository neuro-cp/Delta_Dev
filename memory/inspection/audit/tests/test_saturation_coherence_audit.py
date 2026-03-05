from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_structure import Episode
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry

from memory.inspection.audit.saturation_coherence_audit import SaturationCoherenceAudit


# ==================================================
# A5.1 Semantic saturation
# ==================================================

def test_semantic_saturation_detected():
    tracker = EpisodeTracker(trace=None)
    tracker._episodes.extend(
        Episode(i, 0, 0.0) for i in range(5)
    )

    semantic = type(
        "FakeSemantic",
        (),
        {"semantic_id": "S1"},
    )

    semantic_registry = SemanticRegistry(
        _records=[semantic(), semantic(), semantic(), semantic()]
    )

    consolidator = EpisodeConsolidator(tracker)

    audit = SaturationCoherenceAudit(
        episode_tracker=tracker,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
        max_semantic_ratio=0.5,
    )

    findings = audit.run()

    assert any(
        f.layer == "semantic"
        and f.severity == "WARNING"
        and "disproportionately" in f.description.lower()
        for f in findings
    )


# ==================================================
# A5.2 Drift runaway
# ==================================================

def test_drift_monotonic_runaway_detected():
    tracker = EpisodeTracker(trace=None)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    drift_records = [
        type("FakeDrift", (), {"semantic_id": "S1", "delta": d})()
        for d in [0.1, 0.2, 0.3, 0.4]
    ]

    audit = SaturationCoherenceAudit(
        episode_tracker=tracker,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=drift_records,
        max_monotonic_drift_steps=3,
    )

    findings = audit.run()

    assert any(
        f.layer == "drift"
        and f.severity == "WARNING"
        and "monotonically" in f.description.lower()
        for f in findings
    )


# ==================================================
# A5.3 Replay loop
# ==================================================

def test_episode_replay_loop_detected():
    tracker = EpisodeTracker(trace=None)
    tracker._episodes.extend(
        Episode(i, 0, 0.0) for i in range(3)
    )

    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    consolidator.consolidate = lambda: [
        type("FakeConsolidated", (), {"episode_id": 1})(),
        type("FakeConsolidated", (), {"episode_id": 1})(),
        type("FakeConsolidated", (), {"episode_id": 1})(),
        type("FakeConsolidated", (), {"episode_id": 2})(),
    ]

    audit = SaturationCoherenceAudit(
        episode_tracker=tracker,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
        max_replay_ratio=0.5,
    )

    findings = audit.run()

    assert any(
        f.layer == "consolidation"
        and f.severity == "WARNING"
        and "replay loop" in f.description.lower()
        for f in findings
    )
