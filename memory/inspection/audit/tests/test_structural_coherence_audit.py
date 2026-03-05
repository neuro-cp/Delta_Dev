from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace
from memory.consolidation.episode_consolidator import EpisodeConsolidator
from memory.semantic.registry import SemanticRegistry
from memory.inspection.audit.structural_coherence_audit import StructuralCoherenceAudit


def test_closed_episode_without_trace_is_detected():
    """
    Audit A1 must detect a closed Episode that does not have
    a corresponding 'close' record in the EpisodeTrace.
    """

    # --------------------------------------------------
    # Lawful construction (all invariants satisfied)
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    semantic_registry = SemanticRegistry(_records=[])
    consolidator = EpisodeConsolidator(tracker)

    # --------------------------------------------------
    # Introduce exactly one illegal relationship
    # --------------------------------------------------
    # Create a valid Episode that was never routed
    # through EpisodeTracker lifecycle methods.
    episode = Episode(
        episode_id=0,
        start_step=0,
        start_time=0.0,
    )
    episode.close(step=10, time=1.0)

    # Bypass tracker lifecycle intentionally:
    # - no record_start
    # - no record_close
    tracker._episodes.append(episode)

    # --------------------------------------------------
    # Run audit
    # --------------------------------------------------
    audit = StructuralCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    # --------------------------------------------------
    # Assert: missing trace closure is detected
    # --------------------------------------------------
    assert any(
        f.severity == "ERROR"
        and f.layer == "episodic"
        and f.finding_id.startswith("missing_trace")
        for f in findings
    )

def test_consolidation_count_mismatch_detected():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    registry = SemanticRegistry(_records=[])
    consolidator = EpisodeConsolidator(tracker)

    # Create a closed episode
    ep = Episode(episode_id=1, start_step=0, start_time=0.0)
    ep.close(step=5, time=0.5)
    tracker._episodes.append(ep)

    # Monkey-patch consolidation result to be wrong
    consolidator.consolidate = lambda: []  # should be 1, returns 0

    audit = StructuralCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=registry,
        drift_records=[],
    )

    findings = audit.run()

    assert any(
        f.severity == "ERROR"
        and f.layer == "consolidation"
        and f.finding_id == "consolidation_count_mismatch"
        for f in findings
    )

def test_orphan_semantic_record_detected():
    """
    Audit A1 must detect a SemanticRecord that references
    an episode_id not present in EpisodeTracker.
    """

    # --------------------------------------------------
    # Lawful construction
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)

    # Create a semantic record that references a missing episode
    semantic_registry = SemanticRegistry(
        _records=[
            # Minimal valid semantic record with bad episode_id
            type(
                "FakeSemanticRecord",
                (),
                {
                    "record_id": "S1",
                    "episode_id": 999,  # does not exist
                },
            )()
        ]
    )

    # --------------------------------------------------
    # Run audit
    # --------------------------------------------------
    audit = StructuralCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    # --------------------------------------------------
    # Assert: orphan semantic is detected
    # --------------------------------------------------
    assert any(
        f.severity == "ERROR"
        and f.layer == "semantic"
        and f.finding_id.startswith("orphan_semantic")
        for f in findings
    )
def test_orphan_drift_record_detected():
    """
    Audit A1 must detect a DriftRecord that references
    a semantic_id not present in SemanticRegistry.
    """

    # --------------------------------------------------
    # Lawful construction
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)

    # Empty semantic registry (no valid semantic IDs)
    semantic_registry = SemanticRegistry(_records=[])

    # Create a drift record pointing to a missing semantic
    drift_records = [
        type(
            "FakeDriftRecord",
            (),
            {
                "semantic_id": "S_MISSING",
            },
        )()
    ]

    # --------------------------------------------------
    # Run audit
    # --------------------------------------------------
    audit = StructuralCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=drift_records,
    )

    findings = audit.run()

    # --------------------------------------------------
    # Assert: orphan drift record is detected
    # --------------------------------------------------
    assert any(
        f.severity == "ERROR"
        and f.layer == "drift"
        and f.finding_id.startswith("orphan_drift")
        for f in findings
    )
def test_inspection_episode_count_mismatch_detected():
    """
    Audit A1 must detect when an InspectionReport's
    episode count does not match EpisodeTracker.
    """

    # --------------------------------------------------
    # Lawful construction
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    # Create one episode
    ep = Episode(episode_id=0, start_step=0, start_time=0.0)
    tracker._episodes.append(ep)

    # Fake inspection report with wrong count
    inspection_report = type(
        "FakeInspectionReport",
        (),
        {
            "episode_count": 999,  # incorrect
        },
    )()

    # --------------------------------------------------
    # Run audit
    # --------------------------------------------------
    audit = StructuralCoherenceAudit(
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
        inspection_report=inspection_report,
    )

    findings = audit.run()

    # --------------------------------------------------
    # Assert: inspection mismatch detected
    # --------------------------------------------------
    assert any(
        f.severity == "ERROR"
        and f.layer == "inspection"
        and f.finding_id == "inspection_episode_count_mismatch"
        for f in findings
    )
    
def test_episode_end_time_before_start_time_detected():
    """
    Audit A2 must detect an Episode whose end_time
    precedes its start_time.
    """

    # --------------------------------------------------
    # Lawful construction
    # --------------------------------------------------
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    consolidator = EpisodeConsolidator(tracker)
    semantic_registry = SemanticRegistry(_records=[])

    # --------------------------------------------------
    # Introduce temporal violation
    # --------------------------------------------------
    ep = Episode(
        episode_id=0,
        start_step=10,
        start_time=5.0,
    )

    # Close with illegal earlier time
    ep.close(step=20, time=2.0)

    tracker._episodes.append(ep)

    # --------------------------------------------------
    # Run audit
    # --------------------------------------------------
    audit = StructuralCoherenceAudit(  # temporary reuse
        episode_tracker=tracker,
        episode_trace=trace,
        consolidator=consolidator,
        semantic_registry=semantic_registry,
        drift_records=[],
    )

    findings = audit.run()

    # --------------------------------------------------
    # Assert: temporal violation detected
    # --------------------------------------------------
    assert any(
        f.severity == "ERROR"
        and "time" in f.description.lower()
        for f in findings
    )

