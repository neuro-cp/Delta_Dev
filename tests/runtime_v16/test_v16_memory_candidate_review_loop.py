from __future__ import annotations

from orchestration.runtime.v16_memory_candidate_review_loop import (
    MemoryCandidateReviewDecisionValue,
    build_memory_candidate_review_request,
    defer_memory_candidate,
    mark_memory_candidate_ready_for_explicit_approval,
    propose_memory_candidate_edit,
    reject_memory_candidate,
    request_more_evidence_for_memory_candidate,
    validate_memory_candidate_review_safe,
)
from orchestration.runtime.v16_memory_candidate_review_loop_report import write_memory_candidate_review_loop_report


def _request():
    return build_memory_candidate_review_request("candidate-1", "Candidate text")


def test_edit_does_not_write():
    payload = propose_memory_candidate_edit(_request(), "Edited text")
    assert payload["decision"]["decision"] == MemoryCandidateReviewDecisionValue.EDIT_PROPOSED.value
    assert payload["edit_proposal"]["applied"] is False
    assert validate_memory_candidate_review_safe(payload)


def test_reject_does_not_delete_source():
    payload = reject_memory_candidate(_request())
    assert payload["decision"]["decision"] == MemoryCandidateReviewDecisionValue.REJECTED_FOR_REVIEW.value
    assert payload["audit"]["source_record_preserved"] is True
    assert validate_memory_candidate_review_safe(payload)


def test_defer_and_more_evidence_do_not_call_provider():
    for payload in (defer_memory_candidate(_request()), request_more_evidence_for_memory_candidate(_request())):
        assert payload["audit"]["no_provider_call"] is True
        assert validate_memory_candidate_review_safe(payload)


def test_ready_for_approval_does_not_approve():
    payload = mark_memory_candidate_ready_for_explicit_approval(_request())
    assert payload["decision"]["decision"] == MemoryCandidateReviewDecisionValue.READY_FOR_EXPLICIT_APPROVAL.value
    assert payload["decision"]["approved"] is False
    assert validate_memory_candidate_review_safe(payload)


def test_report_generation():
    data = write_memory_candidate_review_loop_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CANONICAL_MEMORY_ROLLBACK_TRIAL"
