from memory.inspection.inspection_runner import InspectionRunner
from memory.inspection.inspection_report import InspectionReport
from memory.inspection.audit.integrity_finding import IntegrityFinding
from memory.inspection.audit.integrity_audit_base import IntegrityAudit


# ==================================================
# Fake audit for testing
# ==================================================

class FakeAudit(IntegrityAudit):
    audit_id = "FAKE_AUDIT"

    def __init__(self, findings):
        self._findings = findings

    def run(self):
        return self._findings


# ==================================================
# Tests
# ==================================================

def test_inspection_runner_aggregates_findings():
    base_report = InspectionReport(
        report_id="R1",
        generated_step=100,
        generated_time=10.0,
        inspected_components=["episodic", "semantic"],
        episode_count=2,
        semantic_record_count=3,
        drift_record_count=1,
        promotion_candidate_count=0,
    )

    findings = [
        IntegrityFinding(
            audit_id="A1",
            finding_id="f1",
            severity="ERROR",
            layer="episodic",
            description="test error",
            evidence={},
        ),
        IntegrityFinding(
            audit_id="A2",
            finding_id="f2",
            severity="WARNING",
            layer="semantic",
            description="test warning",
            evidence={},
        ),
    ]

    runner = InspectionRunner(
        base_report=base_report,
        audits=[FakeAudit(findings)],
    )

    report = runner.run()

    assert report.audits.total_findings == 2
    assert report.audits.error_count == 1
    assert report.audits.warning_count == 1

    assert "A1" in report.audits.by_audit
    assert "episodic" in report.audits.by_layer
    assert "ERROR" in report.audits.by_severity


def test_inspection_runner_with_no_findings():
    base_report = InspectionReport(
        report_id="R2",
        generated_step=None,
        generated_time=None,
        inspected_components=[],
        episode_count=0,
        semantic_record_count=0,
        drift_record_count=0,
        promotion_candidate_count=0,
    )

    runner = InspectionRunner(
        base_report=base_report,
        audits=[FakeAudit([])],
    )

    report = runner.run()

    assert report.audits.total_findings == 0
    assert report.audits.error_count == 0
    assert report.audits.warning_count == 0
    assert report.audits.by_audit == {}
