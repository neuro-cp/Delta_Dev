from __future__ import annotations

from typing import List

from memory.inspection.inspection_runner import InspectionRunner
from memory.inspection.inspection_report import InspectionReport
from memory.inspection.audit.integrity_audit_base import IntegrityAudit
from memory.inspection.audit.integrity_finding import IntegrityFinding
from memory.semantic_activation.multiscale_record import (
    MultiscaleActivationRecord,
)


# --------------------------------------------------
# Dummy audit (pure, deterministic)
# --------------------------------------------------

class _NoOpAudit(IntegrityAudit):
    audit_id = "noop"

    def run(self) -> List[IntegrityFinding]:
        return []


# --------------------------------------------------
# Tests
# --------------------------------------------------

def _base_report() -> InspectionReport:
    return InspectionReport(
        report_id="test",
        generated_step=10,
        generated_time=1.23,
        inspected_components=["episodes", "semantics"],
        episode_count=1,
        semantic_record_count=0,
        drift_record_count=0,
        promotion_candidate_count=0,
    )


def test_inspection_runner_unchanged_without_semantic_activation() -> None:
    base = _base_report()

    runner = InspectionRunner(
        base_report=base,
        audits=[_NoOpAudit()],
        semantic_activation_record=None,
    )

    report = runner.run()

    assert report.semantic_activation is None
    assert report.report_id == base.report_id
    assert report.episode_count == base.episode_count


def test_semantic_activation_attached_read_only() -> None:
    base = _base_report()

    record = MultiscaleActivationRecord(
        activations_by_scale={
            "fast": {"a": 1.0},
            "slow": {"a": 0.5},
        },
        snapshot_index=42,
    )

    runner = InspectionRunner(
        base_report=base,
        audits=[_NoOpAudit()],
        semantic_activation_record=record,
    )

    report = runner.run()

    assert report.semantic_activation is not None
    assert report.semantic_activation.snapshot_index == 42
    assert report.semantic_activation.term_counts_by_scale["fast"] == 1
    assert report.semantic_activation.term_counts_by_scale["slow"] == 1
##passed audit##