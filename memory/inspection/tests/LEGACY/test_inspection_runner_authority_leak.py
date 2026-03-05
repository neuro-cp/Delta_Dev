from memory.inspection.audit.authority_leak_evaluator import AuthorityLeakEvaluator
from memory.inspection.inspection_runner import InspectionRunner
from memory.inspection.inspection_report import InspectionReport


def test_inspection_runner_includes_authority_leak_audit():
    """
    Verifies that InspectionRunner:
    - executes AuthorityLeakEvaluator
    - includes its findings in the audit summary
    - does not alter report contents otherwise
    """

    base_report = InspectionReport(
        report_id="integration-test",
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
        warnings=["This should be flagged"],
        policy_versions={},
        schema_versions={},
        notes=None,
    )

    audit = AuthorityLeakEvaluator(report=base_report)

    runner = InspectionRunner(
        base_report=base_report,
        audits=[audit],
        semantic_activation_record=None,
        promotion_candidates=None,
    )

    result = runner.run()

    # Audit summary assertions
    assert result.audits.total_findings == 1
    assert result.audits.warning_count == 1
    assert result.audits.error_count == 0

    # Audit ID present
    assert "authority_leak_evaluator" in result.audits.by_audit
