from copy import deepcopy

from orchestration.runtime.cognitive_evaluator_binding_amendment import (
    EFFECTIVE_BINDING_STATUS,
    OLD_EVALUATOR,
    PROPOSAL_ID,
    REPLACEMENT_DIGEST,
    REPLACEMENT_ENTRY_POINT,
    REPLACEMENT_EVALUATOR,
    baseline_sensitivity_recheck,
    candidate_generation_block,
    create_amendment_record,
    default_authorization_record,
    duplicate_amendment_result,
    evaluator_boundary_audit,
    evaluator_self_certification_audit,
    replacement_evaluator_callable,
    unchanged_semantic_fields,
    validate_amendment_record,
    verify_operator_authorization,
)
from orchestration.runtime.cognitive_evaluator_qualification import (
    STALE_PASS_STATUS,
    diagnosed_behavior_contract,
    evaluate_stale_pass_observation,
)
from orchestration.runtime.developmental_bootstrap import bootstrap_digest


def proposal():
    return {
        "proposal_id": PROPOSAL_ID,
        "problem_id": "ck-proposal-minimal-a18-replay",
        "bounded_objective": "prevent stale rejected advisory artifacts from being treated as passed",
        "diagnosis": "stale rejected advisory artifacts are treated as passed",
        "first_incorrect_transition": "report.status == PASSED without freshness validation",
        "implementation_path": "orchestration/runtime/autonomy_advisory_assistance.py",
        "focused_test_path": OLD_EVALUATOR,
        "independent_evaluator_path": OLD_EVALUATOR,
        "bounded_strategy": ({"order": 1, "target_path": "orchestration/runtime/autonomy_advisory_assistance.py"},),
        "expected_behavioral_change": "stale rejected advisory artifacts are not treated as passed",
        "limitations": ("single replay transition",),
        "uncertainty": {"score": 0.0, "reason": "bounded fixture"},
        "required_authority": ("bounded_local_sandbox",),
        "prohibited_authority": ("provider", "network", "deployment", "credentials", "primary_source_mutation", "source_mutation"),
        "evidence_references": ({"source_id": "ck-adapter-fixture", "excerpt_id": "duplicate-replay"},),
    }


def stale_pass(**extra):
    payload = {"status": STALE_PASS_STATUS, "duplicate_suppressed": True, "reason": None}
    payload.update(extra)
    return payload


def valid_blocked():
    return {
        "status": "AUTONOMY_18_BOUNDED_ADVISORY_ASSISTANCE_INTEGRITY_STOP",
        "duplicate_suppressed": False,
        "reason": "existing_advisory_not_grounded",
    }


def amendment_inputs():
    prop = proposal()
    auth = default_authorization_record()
    return {
        "proposal": prop,
        "proposal_digest": bootstrap_digest(prop),
        "previous_evaluator_digest": "old-digest",
        "replacement_behavior_contract_digest": bootstrap_digest(diagnosed_behavior_contract()),
        "qualification_report_digest": "qualification-digest",
        "operator_authorization_record": auth,
        "created_at": "2026-07-25T00:00:00Z",
    }


def amendment_record(**overrides):
    inputs = amendment_inputs()
    inputs.update(overrides)
    return create_amendment_record(**inputs)


def test_evaluator_entry_point_is_independent_and_behavior_only():
    entry = replacement_evaluator_callable()
    boundary = evaluator_boundary_audit(entry)
    self_certification = evaluator_self_certification_audit(entry)

    assert entry is evaluate_stale_pass_observation
    assert boundary["entry_point"] == REPLACEMENT_ENTRY_POINT
    assert boundary["independently_usable"] is True
    assert boundary["reads_qualification_result_files"] is False
    assert boundary["reads_candidate_ids"] is False
    assert boundary["reads_strategy_names"] is False
    assert boundary["reads_fixture_filenames"] is False
    assert boundary["contains_default_passing_result"] is False
    assert self_certification["accepted"] is True


def test_authorization_binds_exact_proposal_and_replacement_digest():
    result = verify_operator_authorization(default_authorization_record())

    assert result["accepted"] is True

    wrong = default_authorization_record()
    wrong["replacement_evaluator_digest"] = "wrong"
    rejected = verify_operator_authorization(wrong)

    assert rejected["accepted"] is False
    assert "wrong_replacement_evaluator_digest" in rejected["reasons"]


def test_amendment_preserves_original_proposal_semantics_and_identity():
    prop = proposal()
    record = amendment_record(proposal=prop, proposal_digest=bootstrap_digest(prop))
    semantic = unchanged_semantic_fields(prop, deepcopy(prop))

    assert record["proposal_id"] == PROPOSAL_ID
    assert record["previous_evaluator_path"] == OLD_EVALUATOR
    assert record["replacement_evaluator_path"] == REPLACEMENT_EVALUATOR
    assert record["replacement_evaluator_digest"] == REPLACEMENT_DIGEST
    assert record["amended_binding_disposition"] == EFFECTIVE_BINDING_STATUS
    assert semantic["accepted"] is True
    assert prop["independent_evaluator_path"] == OLD_EVALUATOR


def test_semantic_mutation_is_rejected():
    before = proposal()
    after = deepcopy(before)
    after["diagnosis"] = "changed"

    result = unchanged_semantic_fields(before, after)

    assert result["accepted"] is False
    assert "diagnosis" in result["changed_fields"]


def test_validate_amendment_record_rejects_wrong_proposal_digest_and_missing_authorization():
    prop = proposal()
    auth = verify_operator_authorization(default_authorization_record())
    boundary = evaluator_boundary_audit(replacement_evaluator_callable())
    self_cert = evaluator_self_certification_audit(replacement_evaluator_callable())
    semantic = unchanged_semantic_fields(prop, prop)
    record = amendment_record(proposal=prop, proposal_digest=bootstrap_digest(prop))

    accepted = validate_amendment_record(
        record,
        proposal=prop,
        proposal_digest=bootstrap_digest(prop),
        replacement_evaluator_digest=REPLACEMENT_DIGEST,
        qualification_report_digest="qualification-digest",
        authorization_validation=auth,
        boundary_audit=boundary,
        self_certification=self_cert,
        semantic_check=semantic,
    )
    rejected = validate_amendment_record(
        {**record, "proposal_digest": "wrong"},
        proposal=prop,
        proposal_digest=bootstrap_digest(prop),
        replacement_evaluator_digest=REPLACEMENT_DIGEST,
        qualification_report_digest="qualification-digest",
        authorization_validation={"accepted": False},
        boundary_audit=boundary,
        self_certification=self_cert,
        semantic_check=semantic,
    )

    assert accepted["accepted"] is True
    assert rejected["accepted"] is False
    assert "wrong_proposal_digest" in rejected["reasons"]
    assert "operator_authorization_rejected" in rejected["reasons"]


def test_baseline_sensitivity_recheck_keeps_candidate_generation_blocked():
    cases = {
        "case_a_current_baseline": evaluate_stale_pass_observation(stale_pass()),
        "case_b_valid_behavior": evaluate_stale_pass_observation(valid_blocked()),
        "case_c_false_pass": evaluate_stale_pass_observation(stale_pass()),
        "case_d_unrelated_failure": evaluate_stale_pass_observation({"parse_error": True}),
        "case_e_strategy_label": evaluate_stale_pass_observation(stale_pass(strategy_label="x")),
        "case_f_fixture_name": evaluate_stale_pass_observation(stale_pass(fixture_name="y")),
        "case_g_hardcoded_output": evaluate_stale_pass_observation(stale_pass(candidate_id="constant")),
    }
    sensitivity = baseline_sensitivity_recheck(cases, evaluator_digest_before=REPLACEMENT_DIGEST, evaluator_digest_after=REPLACEMENT_DIGEST)
    block = candidate_generation_block(amendment_record())

    assert sensitivity["accepted"] is True
    assert block["blocked"] is True
    assert block["fresh_authorization_required"] is True
    assert block["candidate_generated"] is False


def test_negative_controls_reject_identity_label_fixture_hardcoded_and_unqualified_evaluators():
    base = evaluate_stale_pass_observation(stale_pass())

    assert evaluate_stale_pass_observation(stale_pass(candidate_id="different")) == base
    assert evaluate_stale_pass_observation(stale_pass(strategy_label="different")) == base
    assert evaluate_stale_pass_observation(stale_pass(fixture_name="renamed")) == base
    assert evaluate_stale_pass_observation(stale_pass(hardcoded_output=True))["accepted"] is False

    boundary = {"independently_usable": False}
    record = amendment_record()
    rejected = validate_amendment_record(
        record,
        proposal=proposal(),
        proposal_digest=record["proposal_digest"],
        replacement_evaluator_digest=REPLACEMENT_DIGEST,
        qualification_report_digest="qualification-digest",
        authorization_validation={"accepted": True},
        boundary_audit=boundary,
        self_certification={"accepted": True},
        semantic_check={"accepted": True},
    )

    assert rejected["accepted"] is False
    assert "evaluator_boundary_rejected" in rejected["reasons"]


def test_duplicate_amendment_is_deterministic_and_suppressed():
    first = amendment_record()
    second = amendment_record()
    duplicate = duplicate_amendment_result(first, second)

    assert first["amendment_id"] == second["amendment_id"]
    assert duplicate["suppressed"] is True
