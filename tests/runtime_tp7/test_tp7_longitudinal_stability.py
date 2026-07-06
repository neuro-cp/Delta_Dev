from __future__ import annotations

from orchestration.runtime.tp7_longitudinal_stability import (
    answer_tp7_question,
    is_tp7_question,
    run_tp7_longitudinal_evaluation,
    write_tp7_reports,
)


def test_tp7_repeated_runs_are_stable(tmp_path):
    payload = run_tp7_longitudinal_evaluation(base_store=tmp_path)
    assert len(payload["runs"]) == 3
    assert payload["stability"]["deterministic_outputs"] is True
    assert payload["stability"]["behavioral_drift_detected"] is False
    assert payload["drift_analysis"]["passed"] is True


def test_tp7_human_evaluation_and_scorecard(tmp_path):
    payload = run_tp7_longitudinal_evaluation(base_store=tmp_path)
    assert payload["human_evaluation"]["evaluator_agreement"] >= 0.8
    assert payload["human_evaluation"]["operator_judgment_authoritative"] is True
    assert payload["scorecard"]["passed"] is True
    assert payload["scorecard"]["overall_score"] >= 0.95


def test_tp7_safety_and_recommendation(tmp_path):
    payload = run_tp7_longitudinal_evaluation(base_store=tmp_path)
    safety = payload["safety"]
    assert payload["final_recommendation"] == "READY_FOR_CANONICAL_PROMOTION_POLICY_VALIDATION"
    assert safety["model_training_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["live_knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False


def test_tp7_reports_and_answer_route(tmp_path):
    payload = write_tp7_reports(base_store=tmp_path)
    answer = answer_tp7_question("Has DELTA remained stable over time?")
    assert payload["passed"] is True
    assert is_tp7_question("Has behavioral drift been observed?")
    assert answer["phase"] == "TP7 Longitudinal Stability and Human Evaluation"
