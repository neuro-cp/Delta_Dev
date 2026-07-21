from __future__ import annotations

from orchestration.runtime.continuous_runtime_controller import (
    archive_failed_governed_learning_strategy_discovered_source_retrieval,
    claim_governed_learning_strategy_narrow_source_discovery,
    claim_governed_learning_strategy_discovered_source_retrieval,
    compile_governed_learning_strategy_discovered_source_retrieval_authority,
    compile_replacement_governed_learning_strategy_discovered_source_retrieval_authority,
    consume_continuous_operator_interaction_response,
    execute_claimed_governed_learning_strategy_discovered_source_retrieval,
    export_continuous_mission_restart_state,
    record_governed_learning_strategy_metadata_source_discovery,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.governed_learning_strategy_source_discovery import validate_discovered_source_retrieval_authority_request
from orchestration.runtime.governed_pdf_extraction import extract_governed_pdf_text
from tests.runtime_gsr.test_governed_pdf_extraction import _pdf
from tests.runtime_gsr.test_governed_learning_strategy_source_discovery import _candidate, _discovery_ready_controller


def _discovery_completed_controller():
    claimed = claim_governed_learning_strategy_narrow_source_discovery(_discovery_ready_controller())
    unresolved = tuple(claimed.continuous_learning_state["governed_learning_strategy_resource_revision"]["unresolved_question_ids"])
    return record_governed_learning_strategy_metadata_source_discovery(
        claimed,
        metadata_candidates=(_candidate("https://university.example/selected", unresolved, title="Selected"),),
    )


def test_discovery_result_compiles_one_bound_retrieval_authority_without_retrieval():
    completed = _discovery_completed_controller()
    pending = compile_governed_learning_strategy_discovered_source_retrieval_authority(completed)
    request = pending.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"]
    revision = pending.continuous_learning_state["governed_learning_strategy_resource_revision"]
    result = pending.continuous_learning_state["governed_learning_strategy_source_discovery"]["result"]
    assert request["status"] == "pending"
    assert request["candidate_id"] == result["recommended_candidate_id"]
    assert request["discovery_result_id"] == result["discovery_result_id"]
    assert request["discovery_result_digest"] == result["result_digest"]
    assert request["prior_acquisition_result_digest"] == revision["acquisition_result_digest"]
    assert tuple(request["question_ids"]) == tuple(revision["unresolved_question_ids"])
    assert request["maximum_retrieval_count"] == 1
    assert request["permitted_responses"][0] == "approve_learning_strategy_discovered_source_retrieval_authority"
    assert "retrieval_result" not in pending.continuous_learning_state
    assert compile_governed_learning_strategy_discovered_source_retrieval_authority(pending).continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"] == request


def test_discovered_retrieval_authority_fails_closed_on_binding_tampering_and_restores_once():
    pending = compile_governed_learning_strategy_discovered_source_retrieval_authority(_discovery_completed_controller())
    request = dict(pending.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"])
    strategy = pending.continuous_learning_state["governed_learning_strategy"]
    revision = pending.continuous_learning_state["governed_learning_strategy_resource_revision"]
    result = pending.continuous_learning_state["governed_learning_strategy_source_discovery"]["result"]
    request["canonical_locator"] = "https://substituted.example/source"
    request["question_ids"] = ()
    request["permitted_responses"] = ("wrong",)
    validation = validate_discovered_source_retrieval_authority_request(request, strategy=strategy, revision=revision, discovery_result=result)
    assert not validation["accepted"]
    assert {"candidate_substitution_or_locator_mismatch", "question_set_mismatch", "request_token_mismatch"}.issubset(validation["errors"])
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=pending.session_id), export_continuous_mission_restart_state(pending),
    )
    restored_request = restored.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"]
    assert restored_request["request_id"] == pending.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"]["request_id"]
    assert len([item for item in restored.continuous_developmental_insight_requests if item.get("request_id") == restored_request["request_id"]]) == 1


def test_discovered_retrieval_approval_claim_and_execution_are_exact_once():
    pending = compile_governed_learning_strategy_discovered_source_retrieval_authority(_discovery_completed_controller())
    request = pending.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"]
    approved = consume_continuous_operator_interaction_response(
        pending, request_id=request["request_id"], response_kind=request["request_kind"],
        selected_option="approve_learning_strategy_discovered_source_retrieval_authority", approved_scope=request["authority_scope"], operator_text="",
    )
    claimed = claim_governed_learning_strategy_discovered_source_retrieval(approved)
    claim = claimed.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["claim"]
    assert claim["execution_attempt_count"] == 0
    completed = execute_claimed_governed_learning_strategy_discovered_source_retrieval(
        claimed,
        retrieval_adapter=lambda locator: {
            "canonical_locator": f"{locator}/", "retrieved_at": "2026-07-21T00:00:00+00:00", "retrieval_method": "fixture",
            "content_digest": "fixture-digest", "content_text": "Apply the relationship within the defined scope.",
        },
    )
    result = completed.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["result"]
    assert result["retrieval_count"] == 1
    assert completed.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["claim"]["execution_attempt_count"] == 1
    assert execute_claimed_governed_learning_strategy_discovered_source_retrieval(completed).continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["result"] == result


def test_discovered_retrieval_accepts_governed_pdf_adapter_output():
    pending = compile_governed_learning_strategy_discovered_source_retrieval_authority(_discovery_completed_controller())
    request = pending.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"]
    approved = consume_continuous_operator_interaction_response(
        pending, request_id=request["request_id"], response_kind=request["request_kind"],
        selected_option="approve_learning_strategy_discovered_source_retrieval_authority", approved_scope=request["authority_scope"], operator_text="",
    )
    claimed = claim_governed_learning_strategy_discovered_source_retrieval(approved)
    pdf = _pdf(("Apply the relationship within the defined scope.",))

    def pdf_adapter(locator: str):
        import hashlib

        extraction = extract_governed_pdf_text(
            pdf_bytes=pdf, source_locator=locator, source_digest=hashlib.sha256(pdf).hexdigest(), retrieval_claim_id="fixture-pdf-claim",
        )
        return {
            "canonical_locator": f"{locator}/", "retrieved_at": "2026-07-21T00:00:00+00:00", "retrieval_method": "fixture_pdf",
            "content_digest": hashlib.sha256(pdf).hexdigest(), "content_text": extraction["text"],
        }

    completed = execute_claimed_governed_learning_strategy_discovered_source_retrieval(claimed, retrieval_adapter=pdf_adapter)
    assert completed.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["status"] == "completed"


def test_terminal_failed_retrieval_is_archived_before_distinct_replacement_authority():
    pending = compile_governed_learning_strategy_discovered_source_retrieval_authority(_discovery_completed_controller())
    request = pending.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"]
    approved = consume_continuous_operator_interaction_response(
        pending, request_id=request["request_id"], response_kind=request["request_kind"],
        selected_option="approve_learning_strategy_discovered_source_retrieval_authority", approved_scope=request["authority_scope"], operator_text="",
    )
    claimed = claim_governed_learning_strategy_discovered_source_retrieval(approved)
    failed = execute_claimed_governed_learning_strategy_discovered_source_retrieval(
        claimed, retrieval_adapter=lambda _: (_ for _ in ()).throw(ValueError("fixture_parser_missing")),
    )
    archived = archive_failed_governed_learning_strategy_discovered_source_retrieval(failed)
    replacement = compile_replacement_governed_learning_strategy_discovered_source_retrieval_authority(archived)
    new_request = replacement.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_authority_request"]
    assert archived.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval_history"][-1]["claim"]["claim_id"] == claimed.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["claim"]["claim_id"]
    assert new_request["request_id"] != request["request_id"]
    assert new_request["replacement_for_claim_id"] == claimed.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["claim"]["claim_id"]
    assert new_request["status"] == "pending"
