from orchestration.runtime.cognitive_evaluator_qualification import evaluate_stale_pass_observation
from orchestration.runtime.cognitive_sandbox_execution import (
    AMENDMENT_DIGEST,
    AMENDMENT_ID,
    FINAL_STATUS_CANDIDATE_BLOCKED,
    FINAL_STATUS_NO_IMPROVEMENT,
    FINAL_STATUS_PASSED,
    FOCUSED_TEST_PATH,
    IMPLEMENTATION_PATH,
    PROPOSAL_ID,
    REPLACEMENT_DIGEST,
    REPLACEMENT_ENTRY_POINT,
    REPLACEMENT_EVALUATOR,
    baseline_observation,
    build_negative_controls,
    candidate_artifact_from_patch,
    candidate_generation_block,
    compare_behavior,
    evaluator_freeze_record,
    fallback_candidate_patch,
    final_status_for_comparison,
    fresh_authorization_record,
    observed_after_candidate,
    patch_targets,
    sandbox_manifest,
    validate_candidate,
    verify_execution_identity,
)


def proposal():
    return {
        "proposal_id": PROPOSAL_ID,
        "implementation_path": IMPLEMENTATION_PATH,
        "focused_test_path": FOCUSED_TEST_PATH,
        "independent_evaluator_path": FOCUSED_TEST_PATH,
        "required_authority": ("bounded_local_sandbox",),
        "prohibited_authority": ("provider", "network", "deployment", "credentials", "primary_source_mutation", "source_mutation"),
    }


def amendment_status():
    return {
        "amendment_id": AMENDMENT_ID,
        "amendment_digest": AMENDMENT_DIGEST,
        "replacement_evaluator_digest": REPLACEMENT_DIGEST,
        "effective_binding_status": "evaluator_amended_pending_sandbox_candidate_authorization",
    }


def test_identity_verification_requires_exact_proposal_amendment_and_authorization():
    prop = proposal()
    auth = fresh_authorization_record()
    result = verify_execution_identity(
        proposal=prop,
        amendment_status=amendment_status(),
        authorization=auth,
        proposal_digest="d1",
        expected_proposal_digest="d1",
    )
    bad = verify_execution_identity(
        proposal={**prop, "proposal_id": "wrong"},
        amendment_status={**amendment_status(), "amendment_id": "wrong"},
        authorization={**auth, "permitted_actions": ()},
        proposal_digest="d1",
        expected_proposal_digest="d2",
    )

    assert result["accepted"] is True
    assert bad["accepted"] is False
    assert "wrong_proposal_id" in bad["reasons"]
    assert "wrong_amendment_id" in bad["reasons"]
    assert "wrong_proposal_digest" in bad["reasons"]
    assert "candidate_generation_not_authorized" in bad["reasons"]


def test_evaluator_freeze_and_sandbox_manifest_record_boundaries(tmp_path):
    evaluator = tmp_path / "evaluator.py"
    evaluator.write_bytes(b"evaluator")
    freeze = evaluator_freeze_record(evaluator)
    workspace = tmp_path / "workspace"
    (workspace / "orchestration/runtime").mkdir(parents=True)
    (workspace / IMPLEMENTATION_PATH).write_text("x", encoding="utf-8")
    manifest = sandbox_manifest(workspace, root=tmp_path)

    assert freeze["entry_point"] == REPLACEMENT_ENTRY_POINT
    assert freeze["path"] == REPLACEMENT_EVALUATOR
    assert freeze["uses_candidate_id"] is False
    assert manifest["writable_paths"] == (IMPLEMENTATION_PATH,)
    assert FOCUSED_TEST_PATH in manifest["read_only_paths"]


def test_baseline_and_amended_evaluator_sensitivity():
    baseline = evaluate_stale_pass_observation(baseline_observation())
    after = evaluate_stale_pass_observation(observed_after_candidate(application_success=True))

    assert baseline["accepted"] is False
    assert baseline["classification"] == "stale_pass_detected"
    assert after["accepted"] is True
    assert after["classification"] == "valid_blocked_behavior"


def test_candidate_scope_validation_accepts_exact_single_file_patch():
    candidate = candidate_artifact_from_patch(fallback_candidate_patch())
    result = validate_candidate(candidate)

    assert result["accepted"] is True
    assert result["patch_targets"] == (IMPLEMENTATION_PATH,)
    assert patch_targets(candidate["patch"]) == (IMPLEMENTATION_PATH,)


def test_candidate_scope_validation_rejects_bad_boundaries():
    candidate = candidate_artifact_from_patch(fallback_candidate_patch())
    controls = build_negative_controls(candidate)

    for name, result in controls.items():
        if name in {"strategy_label_dependence", "fixture_name_dependence"}:
            continue
        if isinstance(result, dict) and "accepted" in result:
            assert result["accepted"] is False, name


def test_behavioral_comparison_requires_evaluator_improvement_not_test_alone():
    baseline = evaluate_stale_pass_observation(baseline_observation())
    improved = evaluate_stale_pass_observation(observed_after_candidate(application_success=True))
    unchanged = evaluate_stale_pass_observation(observed_after_candidate(application_success=False))

    good = compare_behavior(
        baseline_result=baseline,
        after_result=improved,
        application_success=True,
        focused_test_passed=True,
        evaluator_unchanged=True,
    )
    no_change = compare_behavior(
        baseline_result=baseline,
        after_result=unchanged,
        application_success=True,
        focused_test_passed=True,
        evaluator_unchanged=True,
    )

    assert good["classification"] == "measurable_improvement"
    assert no_change["classification"] == "no_material_change"
    assert final_status_for_comparison(good, candidate_valid=True) == FINAL_STATUS_PASSED
    assert final_status_for_comparison(no_change, candidate_valid=True) == FINAL_STATUS_NO_IMPROVEMENT
    assert final_status_for_comparison(good, candidate_valid=False) == FINAL_STATUS_CANDIDATE_BLOCKED


def test_candidate_generation_block_record_keeps_copyback_forbidden():
    record = candidate_generation_block({
        "amended_binding_disposition": "evaluator_amended_pending_sandbox_candidate_authorization",
    })

    assert record["blocked"] is True
    assert record["candidate_generated"] is False
    assert record["candidate_applied"] is False
