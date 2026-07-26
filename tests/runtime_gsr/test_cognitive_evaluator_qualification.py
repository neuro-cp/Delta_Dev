from orchestration.runtime.cognitive_evaluator_qualification import (
    STALE_PASS_STATUS,
    diagnosed_behavior_contract,
    evaluate_stale_pass_observation,
    evaluator_candidate_audit,
    qualification_result,
    stable_case_digest,
)


def stale_pass(**extra):
    payload = {"status": STALE_PASS_STATUS, "duplicate_suppressed": True, "reason": None}
    payload.update(extra)
    return payload


def valid_blocked(**extra):
    payload = {
        "status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP",
        "duplicate_suppressed": False,
        "reason": "existing_advisory_not_grounded",
    }
    payload.update(extra)
    return payload


def test_diagnosed_behavior_contract_is_observable_and_strategy_agnostic():
    contract = diagnosed_behavior_contract()

    assert contract["actual_stale_pass_behavior"] == STALE_PASS_STATUS
    assert "status" in contract["observable_output_fields"]
    assert contract["repair_strategy_coupling"] is False


def test_stale_pass_fails_and_valid_blocked_behavior_passes():
    stale = evaluate_stale_pass_observation(stale_pass())
    valid = evaluate_stale_pass_observation(valid_blocked())

    assert stale["accepted"] is False
    assert stale["classification"] == "stale_pass_detected"
    assert "stale_pass_rejected" in stale["reasons"]
    assert valid["accepted"] is True
    assert valid["classification"] == "valid_blocked_behavior"


def test_unrelated_failure_is_not_misclassified_as_improvement():
    result = evaluate_stale_pass_observation({"runtime_error": "boom"})

    assert result["accepted"] is False
    assert result["classification"] == "unrelated_failure"
    assert "unrelated_runtime_or_parse_failure" in result["reasons"]


def test_strategy_label_and_fixture_name_do_not_change_result():
    base = evaluate_stale_pass_observation(stale_pass())
    strategy = evaluate_stale_pass_observation(stale_pass(strategy_label="different"))
    fixture = evaluate_stale_pass_observation(stale_pass(fixture_name="renamed"))

    assert strategy == base
    assert fixture == base


def test_hardcoded_pass_output_is_rejected():
    result = evaluate_stale_pass_observation(stale_pass(candidate_id="hardcoded"))

    assert result["accepted"] is False
    assert result["classification"] == "stale_pass_detected"


def test_candidate_audit_marks_original_blind_spot_and_new_evaluator_suitable():
    original = evaluator_candidate_audit(
        path="tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        baseline_observation=valid_blocked(),
        original=True,
    )
    candidate = evaluator_candidate_audit(
        path="orchestration/runtime/cognitive_evaluator_qualification.py",
        baseline_observation=stale_pass(),
    )

    assert original["suitable_to_freeze"] is False
    assert candidate["baseline_currently_fails"] is True
    assert candidate["suitable_to_freeze"] is True


def test_qualification_result_requires_expected_controls_and_digest_freeze():
    cases = {
        "case_a_current_baseline": evaluate_stale_pass_observation(stale_pass()),
        "case_b_valid_behavior": evaluate_stale_pass_observation(valid_blocked()),
        "case_c_false_pass": evaluate_stale_pass_observation(stale_pass()),
        "case_d_unrelated_failure": evaluate_stale_pass_observation({"parse_error": True}),
        "case_e_strategy_label": evaluate_stale_pass_observation(stale_pass(strategy_label="x")),
        "case_f_fixture_name": evaluate_stale_pass_observation(stale_pass(fixture_name="y")),
        "case_g_hardcoded_output": evaluate_stale_pass_observation(stale_pass(candidate_id="constant")),
    }
    result = qualification_result(cases, evaluator_digest_before="d1", evaluator_digest_after="d1")

    assert result["accepted"] is True
    assert result["implementation_source_mutation"] is False
    assert result["proposal_mutation"] is False


def test_qualification_rejects_digest_change_and_is_repeatable():
    case = evaluate_stale_pass_observation(stale_pass())
    repeat = evaluate_stale_pass_observation(stale_pass())
    bad = qualification_result({"case_a_current_baseline": case}, evaluator_digest_before="d1", evaluator_digest_after="d2")

    assert case == repeat
    assert stable_case_digest(case) == stable_case_digest(repeat)
    assert bad["accepted"] is False
    assert "evaluator_digest_changed" in bad["reasons"]
