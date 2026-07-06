from __future__ import annotations

from orchestration.runtime.tp0_controlled_training_pilot import (
    CONTROLLER_STATES,
    answer_tp0_question,
    is_tp0_question,
    run_tp0_controlled_training_pilot,
    write_tp0_reports,
)


def test_tp0_controller_states_are_complete_and_not_autonomous():
    payload = run_tp0_controlled_training_pilot()

    assert tuple(payload["controller_states"]) == CONTROLLER_STATES
    assert payload["autonomous_transition_performed"] is False
    assert payload["state_trace"][0] == "disabled"
    assert payload["state_trace"][-1] == "rolled_back"


def test_tp0_creates_only_noncanonical_consolidated_records():
    payload = run_tp0_controlled_training_pilot()

    assert payload["consolidated_noncanonical_records"]
    assert all(record["canonical"] is False for record in payload["consolidated_noncanonical_records"])
    assert all(decision["canonical_write_allowed"] is False for decision in payload["consolidation_decisions"])
    assert payload["safety"]["canonical_write_performed"] is False


def test_tp0_before_after_improves_without_confidence_inflation():
    payload = run_tp0_controlled_training_pilot()
    evaluation = payload["before_after_evaluation"]

    assert evaluation["after"]["cognitive_integrity"] >= evaluation["before"]["cognitive_integrity"]
    assert evaluation["delta"]["retrieval_quality_delta"] > 0
    assert evaluation["delta"]["confidence_inflation_detected"] is False
    assert "not repeated evidence inflation" in evaluation["delta"]["improvement_source"]


def test_tp0_learned_query_is_noncanonical_and_preserves_uncertainty():
    payload = run_tp0_controlled_training_pilot()
    learned = payload["learned_query_answer"]

    assert learned["substrate_status"] == "noncanonical"
    assert learned["model_training_occurred"] is False
    assert learned["consolidated_patterns"]
    assert learned["contradictions_preserved"]
    assert learned["unknown"]
    assert learned["unsupported_refusals"]


def test_tp0_rollback_drill_restores_baseline_and_preserves_audit():
    payload = run_tp0_controlled_training_pilot()
    rollback = payload["rollback_result"]

    assert rollback["passed"] is True
    assert rollback["pre_consolidation_retrieval_restored"] is True
    assert rollback["hidden_mutation_detected"] is False
    assert rollback["audit_preserved"] is True


def test_tp0_operator_review_and_tp1_recommendation():
    payload = run_tp0_controlled_training_pilot()
    review = payload["operator_review"]

    assert review["tp1_justified"] is True
    assert review["regressed"] == {}
    assert review["final_recommendation"] == "PROCEED_TP1_EXPANDED_NONCANONICAL_PILOT"


def test_tp0_safety_invariants_preserved():
    payload = run_tp0_controlled_training_pilot()
    safety = payload["safety"]

    assert safety["model_weight_training_performed"] is False
    assert safety["training_performed"] is False
    assert safety["fine_tuning_performed"] is False
    assert safety["model_update_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["action_execution_performed"] is False
    assert safety["hyb1_promoted"] is False
    assert safety["model_b_default"] == "unchanged"


def test_tp0_local_answer_route_and_reports_are_written():
    assert is_tp0_question("Did DELTA train?")
    answer = answer_tp0_question("What did DELTA learn?")
    payload = write_tp0_reports()

    assert answer["phase"] == "TP0 Controlled Noncanonical Training Pilot"
    assert answer["safety"]["model_weight_training_performed"] is False
    assert payload["training_readiness_review"]["tp0_status"] == "passed"
    assert payload["final_recommendation"] == "PROCEED_TP1_EXPANDED_NONCANONICAL_PILOT"
