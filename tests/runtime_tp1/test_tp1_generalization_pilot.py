from __future__ import annotations

from orchestration.runtime.tp1_generalization_pilot import (
    answer_tp1_question,
    is_tp1_question,
    load_tp1_heldout_corpus,
    run_tp1_generalization_pilot,
    write_tp1_reports,
)


def test_tp1_heldout_corpus_is_distinct_and_not_consolidated():
    payload = run_tp1_generalization_pilot()
    heldout = load_tp1_heldout_corpus()

    assert len(heldout) >= 8
    assert payload["heldout_corpus_consolidated"] is False
    assert payload["training_corpus"] != payload["heldout_corpus"]
    assert all("tp1_heldout" in doc.provenance for doc in heldout)


def test_tp1_generalization_improves_on_heldout_benchmark():
    payload = run_tp1_generalization_pilot()
    benchmark = payload["heldout_benchmark"]

    assert benchmark["average_after_score"] > benchmark["average_before_score"]
    assert benchmark["generalization_delta"] > 0
    assert all(case["delta"] >= 0 for case in benchmark["cases"])


def test_tp1_negative_controls_do_not_improve_or_overconfidently_answer():
    payload = run_tp1_generalization_pilot()

    assert payload["heldout_benchmark"]["negative_controls"]
    assert all(not item["improved"] for item in payload["heldout_benchmark"]["negative_controls"])
    assert all(not item["overconfidence_detected"] for item in payload["heldout_benchmark"]["negative_controls"])
    assert all(item["refusal_preserved"] for item in payload["heldout_benchmark"]["negative_controls"])


def test_tp1_adversarial_consolidation_blocks_unsafe_candidates():
    payload = run_tp1_generalization_pilot()
    adversarial = payload["adversarial_consolidation"]

    assert adversarial["passed"] is True
    assert adversarial["operator_review_caught_conflicts"] is True
    assert adversarial["unsupported_integrations_blocked"] is True
    assert all(item["integration_blocked"] for item in adversarial["candidates"])


def test_tp1_evolution_metrics_and_rollback_are_valid():
    payload = run_tp1_generalization_pilot()

    assert payload["cognitive_evolution"]["reasoning_improvement"] > 0
    assert payload["cognitive_evolution"]["cognitive_integrity_delta"] > 0
    assert payload["rollback"]["passed"] is True
    assert payload["rollback"]["hidden_mutation_detected"] is False


def test_tp1_safety_invariants_preserved():
    payload = run_tp1_generalization_pilot()
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


def test_tp1_local_answer_route_and_reports_are_written():
    assert is_tp1_question("Did DELTA generalize?")
    answer = answer_tp1_question("What did TP1 prove?")
    payload = write_tp1_reports()

    assert answer["phase"] == "TP1 Expanded Noncanonical Generalization Pilot"
    assert answer["generalization_delta"] > 0
    assert payload["readiness_review"]["tp1_status"] == "passed"
    assert payload["final_recommendation"] == "PROCEED_TP2_MULTI_CORPUS_NONCANONICAL_GENERALIZATION"
