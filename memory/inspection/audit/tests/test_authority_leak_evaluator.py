from memory.inspection.audit.authority_leak_evaluator import AuthorityLeakEvaluator
from memory.inspection.inspection_report import InspectionReport


def test_authority_leak_evaluator_detects_normative_language():
    """
    Verifies that the AuthorityLeakEvaluator emits an IntegrityFinding
    when inspection text contains normative / prescriptive language.

    This test asserts:
    - IntegrityAudit.run() interface
    - offline execution
    - canonical IntegrityFinding schema
    """

    report = InspectionReport(
        report_id="test-report",
        generated_step=None,
        generated_time=None,
        inspected_components=[],
        episode_count=0,
        semantic_record_count=0,
        drift_record_count=0,
        promotion_candidate_count=0,
        summaries={},
        semantic_activation=None,
        promotion_summary=None,
        anomalies=[],
        warnings=["This should be reviewed carefully"],
        policy_versions={},
        schema_versions={},
        notes=None,
    )

    audit = AuthorityLeakEvaluator(report=report)
    findings = audit.run()

    assert len(findings) == 1

    finding = findings[0]

    assert finding.audit_id == "authority_leak_evaluator"
    assert finding.finding_id == "inspection_normative_language"
    assert finding.severity == "WARNING"
    assert finding.layer == "inspection"

    assert "normative" in finding.description.lower()
    assert isinstance(finding.evidence, dict)
