from __future__ import annotations

from memory.inspection.inspection_runner import InspectionRunner
from memory.inspection.inspection_report import InspectionReport
from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.episode_signature import EpisodeSignature
from memory.proto_structural.pattern_record import PatternRecord

from learning.inputs.learning_pipeline_input_adapter import (
    LearningPipelineInputAdapter,
)
from learning.session.learning_session import LearningSession


# ==================================================
# Fake audit (reuse inspection harness semantics)
# ==================================================

class FakeAudit(IntegrityAudit):
    audit_id = "FAKE_AUDIT"

    def __init__(self, findings):
        self._findings = findings

    def run(self):
        return self._findings


# ==================================================
# Continuity test
# ==================================================

def test_inspection_to_learning_continuity():
    """
    Verifies that artifacts already aggregated at the
    inspection surface can be consumed by learning
    without mutation, inference, or authority.

    Pipeline:
      inspection artifacts
        → learning adapter
        → learning session
        → proposals
    """

    # ----------------------------------------------
    # Base inspection report (as usual)
    # ----------------------------------------------
    base_report = InspectionReport(
        report_id="R_CONTINUITY",
        generated_step=123,
        generated_time=12.3,
        inspected_components=["episodic", "semantic", "proto_structural"],
        episode_count=1,
        semantic_record_count=2,
        drift_record_count=0,
        promotion_candidate_count=0,
    )

    runner = InspectionRunner(
        base_report=base_report,
        audits=[FakeAudit([])],
    )

    report = runner.run()

    # ----------------------------------------------
    # Real offline artifacts (already inspection-safe)
    # ----------------------------------------------
    semantic_records = [
        SemanticActivationRecord(
            activations={"sem:alpha": 0.5},
            snapshot_index=1,
        ),
        SemanticActivationRecord(
            activations={"sem:alpha": 0.7, "sem:beta": 0.2},
            snapshot_index=2,
        ),
    ]

    sig = EpisodeSignature(
        length_steps=8,
        event_count=2,
        event_types=frozenset({"start", "close"}),
        region_ids=frozenset({"PFC"}),
        transition_counts=(("start", "close", 1),),
    )

    pattern_record = PatternRecord(pattern_counts={sig: 3})

    # ----------------------------------------------
    # Learning bridge (inspection → learning)
    # ----------------------------------------------
    adapter = LearningPipelineInputAdapter()

    bundle = adapter.from_inspection_surface(
        replay_id="replay:R_CONTINUITY",
        semantic_activation_records=semantic_records,
        pattern_record=pattern_record,
    )

    # ----------------------------------------------
    # Learning session (offline, deterministic)
    # ----------------------------------------------
    session = LearningSession(replay_id="replay:R_CONTINUITY")

    proposals = session.run(inputs=bundle.semantic_ids)

    # ----------------------------------------------
    # Assertions (continuity + safety)
    # ----------------------------------------------
    assert report.report_id == "R_CONTINUITY"
    assert bundle.replay_id == "replay:R_CONTINUITY"

    # Learning observed something real
    assert len(bundle.semantic_ids) > 0

    # Learning produced bounded, audited proposals
    assert isinstance(proposals, list)
    for p in proposals:
        assert p.bounded
        assert p.replay_consistent
