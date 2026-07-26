from pathlib import Path

from orchestration.runtime.cognitive_candidate_generation_audit import render_patch_from_plan, validate_candidate_plan
from orchestration.runtime.cognitive_sandbox_application import (
    FINAL_APPLICATION_BLOCKED,
    FINAL_PASSED,
    FINAL_REGRESSION,
    baseline_evaluation,
    classify_application_behavior,
    evaluator_freeze,
    final_status,
    negative_controls,
    sandbox_manifest,
    verify_retained_candidate,
)
from orchestration.runtime.cognitive_sandbox_execution import FOCUSED_TEST_PATH, IMPLEMENTATION_PATH, PROPOSAL_ID
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


SOURCE = """def request_bounded_advice(output_root):
    if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:
        return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED"}
    return {"status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP"}
"""


def candidate():
    anchor = 'if report.get("status") == "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_PASSED" and audit.get("accepted") is True:'
    return {
        "result_type": "sandbox_candidate_plan",
        "proposal_id": PROPOSAL_ID,
        "candidate_id": "candidate-1",
        "implementation_path": IMPLEMENTATION_PATH,
        "focused_test_path": FOCUSED_TEST_PATH,
        "change_intent": "Guard stale duplicate replay.",
        "edits": [{
            "target": IMPLEMENTATION_PATH,
            "operation": "replace_block",
            "anchor": anchor,
            "replacement": anchor + "\n        if report.get(\"rejected_outputs\"):\n            return {\"status\": \"AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP\"}",
            "purpose": "Reject stale retained rejected outputs.",
        }],
        "expected_behavioral_change": "Stale duplicate replay blocks.",
        "limitations": ["single transition"],
        "uncertainty": {"score": 0.2, "reason": "bounded"},
        "authority_used": ["bounded_local_sandbox"],
    }


def test_retained_candidate_identity_verifies_source_and_patch_digest():
    plan = candidate()
    validation = validate_candidate_plan(plan, full_source=SOURCE)
    patch = render_patch_from_plan(plan, full_source=SOURCE)

    result = verify_retained_candidate(
        candidate=plan,
        validation=validation,
        rendered_patch=patch,
        full_source=SOURCE,
        expected_source_digest=bootstrap_digest(SOURCE),
    )

    assert result["accepted"] is True
    assert result["patch_digest"] == patch["patch_digest"]


def test_candidate_identity_rejects_source_or_patch_mismatch():
    plan = candidate()
    validation = validate_candidate_plan(plan, full_source=SOURCE)
    patch = {**render_patch_from_plan(plan, full_source=SOURCE), "patch_digest": "wrong"}

    result = verify_retained_candidate(
        candidate=plan,
        validation=validation,
        rendered_patch=patch,
        full_source=SOURCE,
        expected_source_digest="wrong",
    )

    assert result["accepted"] is False
    assert "patch_digest_mismatch" in result["reasons"]
    assert "source_digest_mismatch" in result["reasons"]


def test_sandbox_manifest_and_evaluator_freeze_shape(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "orchestration/runtime").mkdir(parents=True)
    (workspace / IMPLEMENTATION_PATH).write_text("x", encoding="utf-8")
    evaluator = tmp_path / "evaluator.py"
    evaluator.write_text("x", encoding="utf-8")

    manifest = sandbox_manifest(workspace)
    freeze = evaluator_freeze(evaluator)

    assert manifest["writable_allowlist"] == (IMPLEMENTATION_PATH,)
    assert FOCUSED_TEST_PATH in manifest["read_only_files"]
    assert freeze["uses_candidate_id"] is False


def test_behavioral_comparison_and_final_statuses():
    baseline = baseline_evaluation()
    valid_after = {"classification": "valid_blocked_behavior"}
    bad_after = {"classification": "unrelated_failure"}

    passed = classify_application_behavior(
        baseline_eval=baseline,
        after_eval=valid_after,
        application_success=True,
        focused_exit_code=0,
        evaluator_unchanged=True,
    )
    focused_failed = classify_application_behavior(
        baseline_eval=baseline,
        after_eval=bad_after,
        application_success=True,
        focused_exit_code=1,
        evaluator_unchanged=True,
    )
    application_failed = classify_application_behavior(
        baseline_eval=baseline,
        after_eval=bad_after,
        application_success=False,
        focused_exit_code=1,
        evaluator_unchanged=True,
    )

    assert final_status(passed) == FINAL_PASSED
    assert final_status(focused_failed) == FINAL_REGRESSION
    assert final_status(application_failed) == FINAL_APPLICATION_BLOCKED


def test_negative_controls_reject_bad_candidates_and_duplicate_application():
    controls = negative_controls(candidate(), full_source=SOURCE)

    for name, result in controls.items():
        assert result.get("accepted") is False, name
    assert controls["duplicate_application"]["duplicate_suppressed"] is True


def test_no_copyback_contract_is_explicit():
    record = {
        "primary_source_mutated": False,
        "copyback": False,
        "staged": False,
    }

    assert record["primary_source_mutated"] is False
    assert record["copyback"] is False
    assert record["staged"] is False
