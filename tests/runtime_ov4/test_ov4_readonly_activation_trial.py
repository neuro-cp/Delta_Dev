from orchestration.runtime.ov4_readonly_activation_trial import (
    CAPABILITY,
    SAFETY,
    answer_ov4_question,
    failure_mode_matrix,
    is_ov4_question,
    run_ov4_trial,
    validate_transition,
    write_ov4_reports,
)


def test_ov4_transitions_only_with_approval_and_safe_configuration():
    allowed = validate_transition("admin_review", "read_only_trial", approval=True, safe=True)
    assert allowed.valid is True
    assert validate_transition("disabled", "read_only_trial", approval=True, safe=True).valid is False
    assert validate_transition("admin_review", "read_only_trial", approval=False, safe=True).valid is False
    assert validate_transition("admin_review", "read_only_trial", approval=True, safe=False).valid is False


def test_ov4_activates_only_evaluation_regression_loop_readonly():
    payload = run_ov4_trial()
    assert payload["activated_capability"] == CAPABILITY
    assert payload["activation_state"] == "read_only_trial"
    assert payload["capability_states"][CAPABILITY] == "read_only_trial"
    assert payload["capability_states"]["all_other_capabilities"] == "disabled_or_blocked"


def test_ov4_readonly_execution_observes_without_mutation():
    payload = run_ov4_trial()
    execution = payload["execution"]
    assert execution["execution_mode"] == "read_only_trial"
    assert execution["mutation_performed"] is False
    assert "OV3 controlled reasoning vertical slice" in execution["inputs_observed"]


def test_ov4_audit_contains_request_review_trace_evaluation_and_rollback():
    payload = run_ov4_trial()
    audit = payload["audit"]
    assert audit["request"]["requested_by"]
    assert audit["eligibility"]["eligible"] is True
    assert audit["safety_review"]["safe"] is True
    assert audit["operator_review"]["approval_simulated"] is True
    assert audit["execution_trace"]
    assert audit["evaluation"]["mutation_performed"] is False
    assert audit["rollback_plan"]["rollback_available"] is True


def test_ov4_failure_modes_are_deterministic_and_handled():
    failures = failure_mode_matrix()
    assert len(failures) == 8
    assert all(item["deterministic"] for item in failures)
    assert all(item["handled"] for item in failures)


def test_ov4_scores_are_justified_and_safety_preserved():
    payload = run_ov4_trial()
    scores = payload["scores"]
    assert scores["activation_confidence"]["score"] > 0.6
    assert scores["governance_confidence"]["score"] >= 0.9
    assert scores["safety_confidence"]["score"] == 1.0
    assert payload["safety"]["provider_call_performed"] is False
    assert payload["safety"]["training_performed"] is False
    assert payload["safety"]["canonical_write_performed"] is False
    assert payload["safety"]["hyb1_promoted"] is False


def test_ov4_local_answer_routes_activation_questions():
    assert is_ov4_question("What capability is active?")
    answer = answer_ov4_question("Show activation audit.")
    assert answer["phase"] == "OV4 Operator-Reviewed Read-Only Activation Trial"
    assert "audit" in answer["answer_text"].lower()
    assert answer["safety"]["provider_call_performed"] is False


def test_ov4_reports_are_written():
    payload = write_ov4_reports()
    assert payload["final_recommendation"] == "PROCEED_OV5_READONLY_RETRIEVAL_SYNTHESIS_TRIAL"
