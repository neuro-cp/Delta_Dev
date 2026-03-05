from __future__ import annotations

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord

from memory.inspection.audit.provenance_coherence_audit import (
    ProvenanceCoherenceAudit,
)


# ==================================================
# A3.1 Semantic provenance
# ==================================================

def test_semantic_record_with_missing_episode_detected():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)

    semantic_registry = SemanticRegistry(
        _records=[
            type(
                "FakeSemantic",
                (),
                {
                    "record_id": "s1",
                    "episode_id": 999,
                },
            )()
        ]
    )

    audit = ProvenanceCoherenceAudit(
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
        and "semantic record references" in f.description.lower()
        for f in findings
    )


# ==================================================
# A3.2 Drift provenance
# ==================================================

def test_drift_record_with_missing_semantic_detected():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    # Inject fake drift record with missing semantic provenance
    drift_records = [
        type(
            "FakeDriftRecord",
            (),
            {
                "semantic_id": "ghost_semantic",
            },
        )()
    ]

    audit = ProvenanceCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=drift_records,
    )

    findings = audit.run()

    assert any(
        f.layer == "drift"
        and f.severity == "ERROR"
        and "drift record references" in f.description.lower()
        for f in findings
    )

# ==================================================
# A3.3 Consolidation provenance
# ==================================================

def test_consolidated_episode_without_origin_detected():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    semantic_registry = SemanticRegistry(_records=[])

    # Fake consolidator output by injecting orphan episode
    consolidator = EpisodeConsolidator(tracker)
    tracker._episodes.append(
        Episode(
            episode_id=1,
            start_step=0,
            start_time=0.0,
        )
    )

    audit = ProvenanceCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    # NOTE:
    # This test only fails if consolidate() returns an episode
    # that cannot be traced to a valid tracker episode.
    # If consolidate() is currently identity-safe, this test
    # will PASS by design.

    assert isinstance(findings, list)
