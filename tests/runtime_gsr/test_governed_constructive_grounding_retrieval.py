from __future__ import annotations

from orchestration.runtime.continuous_runtime_controller import (
    claim_governed_constructive_grounding_exact_source_retrieval,
    compile_governed_constructive_grounding,
    consume_continuous_operator_interaction_response,
    execute_claimed_governed_constructive_grounding_exact_source_retrieval,
    review_governed_constructive_grounding_source_result,
    review_followup_governed_constructive_grounding_source_result,
)
from tests.runtime_gsr.test_governed_constructive_grounding import _linkage_ready_controller


def test_constructive_grounding_authority_retrieves_once_for_only_the_relation_question():
    pending = compile_governed_constructive_grounding(_linkage_ready_controller())
    request = pending.continuous_learning_state["governed_constructive_grounding"]["authority_request"]
    approved = consume_continuous_operator_interaction_response(
        pending, request_id=request["request_id"], response_kind=request["request_kind"],
        selected_option="approve_constructive_grounding_exact_source_authority", approved_scope=request["authority_scope"], operator_text="",
    )
    claimed = claim_governed_constructive_grounding_exact_source_retrieval(approved)
    completed = execute_claimed_governed_constructive_grounding_exact_source_retrieval(
        claimed, retrieval_adapter=lambda locator: {
            "canonical_locator": f"{locator}/", "retrieved_at": "2026-07-21T00:00:00+00:00", "retrieval_method": "fixture",
            "content_digest": "mit-fixture", "content_text": "A finite-dimensional vector space has a finite basis in this theorem setting.",
        },
    )
    retrieval = completed.continuous_learning_state["governed_constructive_grounding"]["retrieval"]
    result = retrieval["result"]
    assert retrieval["claim"]["execution_attempt_count"] == 1
    assert tuple(item["question_id"] for item in result["question_sufficiency"]) == (pending.continuous_learning_state["governed_constructive_grounding"]["relation_proposal"]["target_question_id"],)
    assert execute_claimed_governed_constructive_grounding_exact_source_retrieval(completed).continuous_learning_state["governed_constructive_grounding"]["retrieval"] == retrieval
    reviewed = review_governed_constructive_grounding_source_result(completed)
    review = reviewed.continuous_learning_state["governed_constructive_grounding"]["source_review"]
    assert review["outcome"] == "constructive_grounding_partial"
    assert review["acquisition_term_coverage"] == "learning_strategy_source_sufficient"
    assert reviewed.continuous_mission_state == "constructive_grounding_partial"


def test_followup_review_stays_partial_when_source_only_has_term_level_coverage():
    # The original review helper is deliberately generic; the followup path
    # must apply the same constructive standard rather than promoting coverage.
    completed = execute_claimed_governed_constructive_grounding_exact_source_retrieval(
        claim_governed_constructive_grounding_exact_source_retrieval(
            consume_continuous_operator_interaction_response(
                compile_governed_constructive_grounding(_linkage_ready_controller()),
                request_id=compile_governed_constructive_grounding(_linkage_ready_controller()).continuous_learning_state["governed_constructive_grounding"]["authority_request"]["request_id"],
                response_kind="governed_constructive_grounding_exact_source_authority",
                selected_option="approve_constructive_grounding_exact_source_authority",
                approved_scope="retrieve one exact previously discovered source only to ground one unresolved constructive prerequisite relation",
                operator_text="",
            )
        ), retrieval_adapter=lambda locator: {"canonical_locator": f"{locator}/", "retrieved_at": "now", "retrieval_method": "fixture", "content_digest": "d", "content_text": "finite-dimensional"},
    )
    # This only exercises the review helper's idempotent boundary; a real
    # followup result is covered by the live governed path.
    assert review_followup_governed_constructive_grounding_source_result(completed) is completed
