from __future__ import annotations

from orchestration.runtime.v22_evaluator_assisted_memory_candidate_review import (
    EvaluatorCandidateReviewInput,
    review_memory_candidate_with_evaluator,
    validate_evaluator_candidate_review_safe,
)
from orchestration.runtime.v22_evaluator_assisted_memory_candidate_review_report import write_evaluator_candidate_review_report


def test_local_advisory_review_works():
    payload = review_memory_candidate_with_evaluator(EvaluatorCandidateReviewInput("c", "Candidate.", ("prov",)))
    assert payload["recommendation"]["advisory_only"] is True
    assert payload["recommendation"]["is_approval"] is False
    assert validate_evaluator_candidate_review_safe(payload)


def test_live_evaluator_refuses_by_default():
    payload = review_memory_candidate_with_evaluator(EvaluatorCandidateReviewInput("c", "Candidate.", ("prov",)), live_evaluator=True)
    assert "live_evaluator_refused_by_default" in payload["risk_assessment"]["risks"]


def test_risk_flags_generated():
    payload = review_memory_candidate_with_evaluator(EvaluatorCandidateReviewInput("c", "Maybe.", ("prov",), ambiguity_flag=True))
    assert "ambiguity" in payload["risk_assessment"]["risks"]


def test_no_write_delete_or_recall_mutation():
    payload = review_memory_candidate_with_evaluator(EvaluatorCandidateReviewInput("c", "Candidate.", ("prov",)))
    assert payload["decision"]["canonical_write_performed"] is False
    assert payload["decision"]["memory_deleted"] is False
    assert payload["decision"]["recall_mutated"] is False


def test_report_generation():
    data = write_evaluator_candidate_review_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_HYB1_OPT_IN_SHADOW_TRIAL_DESIGN"
