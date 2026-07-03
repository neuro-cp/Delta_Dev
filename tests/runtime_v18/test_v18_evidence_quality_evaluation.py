from __future__ import annotations

from orchestration.runtime.v17_controlled_answer_synthesis import synthesize_controlled_answer
from orchestration.runtime.v18_evidence_quality_evaluation import evaluate_custom_evidence_payload, run_evidence_quality_evaluation, validate_evidence_quality_evaluation_safe
from orchestration.runtime.v18_evidence_quality_evaluation_report import write_evidence_quality_evaluation_report


def test_scorecard_generated():
    data = run_evidence_quality_evaluation()
    assert data["report_entry"]["case_count"] == 3
    assert data["report_entry"]["average_score"] > 0
    assert validate_evidence_quality_evaluation_safe(data)


def test_weak_provenance_penalized():
    payload = synthesize_controlled_answer("What is HYB1?")
    payload["trace"]["draft"]["provenance_summary"] = []
    scorecard = evaluate_custom_evidence_payload(payload)
    assert scorecard.score < 1.0


def test_authoritative_provider_misuse_penalized():
    payload = synthesize_controlled_answer("What is a question DELTA cannot answer locally?")
    payload["trace"]["evidence_bundle"]["items"][0]["authoritative"] = True
    scorecard = evaluate_custom_evidence_payload(payload)
    assert scorecard.score < 1.0


def test_unsupported_unknown_handled():
    data = run_evidence_quality_evaluation()
    scores = [scorecard["score"] for scorecard in data["evaluation_run"]["scorecards"]]
    assert min(scores) > 0.7


def test_no_promotion_memory_provider_training_or_hyb1_change():
    data = run_evidence_quality_evaluation()
    flags = data["invariant_flags"]
    assert flags["promotion_performed"] is False
    assert flags["memory_write_performed"] is False
    assert flags["provider_call_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_evidence_quality_evaluation_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_PROMOTION_READINESS_SCORECARD"
