from orchestration.runtime.cognitive_sandbox_revision2 import (
    classify_revision_behavior,
    legal_symbols_for_request_bounded_advice,
    negative_controls,
    validate_identifier_scope,
    validate_revision_shape,
)


SOURCE = '''def request_bounded_advice(output_root):
    existing = _read_json(output_root / "advisory_output.json")
    if existing:
        request = _read_json(output_root / "advisory_request.json") or {}
        audit = _read_json(output_root / "grounding_audit.json") or {}
        report = _read_json(output_root / "report.json") or {}
        if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
            return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"}
    return {"status": "new"}
'''

MARKER = 'if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:'


def test_legal_symbol_extraction_records_missing_failed_helpers():
    legal = legal_symbols_for_request_bounded_advice(SOURCE, marker=MARKER)

    assert legal["accepted"] is True
    assert "report" in legal["local_variables"]
    assert legal["validate_artifact_freshness_available"] is False
    assert legal["has_rejection_history_available"] is False


def test_identifier_scope_rejects_undefined_failed_helper():
    legal = legal_symbols_for_request_bounded_advice(SOURCE, marker=MARKER)
    code = MARKER + "\n        if validate_artifact_freshness(audit):\n            return {'status': 'x'}"

    result = validate_identifier_scope(code, legal=legal)

    assert result["accepted"] is False
    assert "validate_artifact_freshness" in result["prohibited_identifiers_used"]


def test_identifier_scope_accepts_in_scope_report_audit_existing_request():
    legal = legal_symbols_for_request_bounded_advice(SOURCE, marker=MARKER)
    code = MARKER + "\n        if report.get('rejected_outputs'):\n            return {'status': 'blocked', 'request': request, 'advisory_output': existing, 'grounding_audit': audit}"

    assert validate_identifier_scope(code, legal=legal)["accepted"] is True
    assert validate_revision_shape(code)["accepted"] is True


def test_revision_behavior_classification_pass_and_regression():
    passed = classify_revision_behavior(
        baseline_classification="stale_pass_detected",
        first_attempt_classification="unrelated_failure",
        revised_classification="valid_blocked_behavior",
        focused_exit_code=0,
        prior_name_error_resolved=True,
        evaluator_unchanged=True,
    )
    regression = classify_revision_behavior(
        baseline_classification="stale_pass_detected",
        first_attempt_classification="unrelated_failure",
        revised_classification="unrelated_failure",
        focused_exit_code=0,
        prior_name_error_resolved=False,
        evaluator_unchanged=True,
    )

    assert passed["classification"] == "measurable_improvement"
    assert regression["classification"] == "regression"


def test_negative_controls_reject_third_attempt_and_bad_cases():
    controls = negative_controls()

    assert controls["third_attempt_request"]["accepted"] is False
    for name, result in controls.items():
        assert result["accepted"] is False, name
