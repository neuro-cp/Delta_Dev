from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_learning_strategy_for_mission,
    compile_replacement_governed_learning_strategy_authority_request,
    consume_continuous_operator_interaction_response,
    execute_governed_learning_strategy_exact_source_acquisition,
    start_continuous_runtime_controller,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
)
from tests.runtime_gsr.test_governed_learning_strategy import _state
from orchestration.runtime.governed_learning_strategy_acquisition import (
    compile_strategy_acquisition_result,
    compile_strategy_acquisition_evidence_linkage_reassessment,
    source_text_matches_question_term,
    is_same_exact_resource_chain,
)


def test_pdf_normalization_matches_ligature_and_line_break_hyphenation_without_rewriting_source_text():
    source = "For a \ufb01nite dimen- sional inner product space."
    assert source_text_matches_question_term(term="finite-dimensional", source_text=source)
    assert source == "For a \ufb01nite dimen- sional inner product space."


def test_historical_reassessment_adds_contextual_link_without_promoting_sufficiency():
    strategy = {
        "strategy_id": "strategy", "learning_questions": ({
            "question_id": "finite", "question": "What does finite-dimensional mean?",
        },),
    }
    result = {
        "acquisition_result_id": "acquisition", "result_digest": "digest",
        "question_sufficiency": ({"question_id": "finite", "status": "unanswered"},),
        "claims": ({
            "claim_id": "claim", "claim_text": "For a \ufb01nite dimen- sional inner product space.", "source_excerpt_reference": "page:2/sentence:1",
        },),
    }
    reassessment = compile_strategy_acquisition_evidence_linkage_reassessment(strategy=strategy, acquisition_result=result)
    assert reassessment["outcome"] == "evidence_linked_but_sufficiency_unchanged"
    assert reassessment["links"][0]["source_excerpt_reference"] == "page:2/sentence:1"
    assert reassessment["links"][0]["sufficiency_status"] == "linked_but_not_sufficient"
    assert reassessment["historical_acquisition_immutable"]


def _approved_controller():
    controller = compile_governed_learning_strategy_for_mission(
        replace(start_continuous_runtime_controller(session_id="strategy-acquisition"), continuous_learning_state=_state())
    )
    request = controller.continuous_learning_state["governed_learning_strategy_authority_request"]
    return consume_continuous_operator_interaction_response(
        controller, request_id=request["request_id"], response_kind=request["request_kind"], operator_text="",
        selected_option="approve_learning_strategy_authority", approved_scope=request["authority_scope"],
    )


def _source(locator: str):
    return {
        "canonical_locator": locator,
        "retrieved_at": "2026-07-21T00:00:00+00:00",
        "retrieval_method": "fixture",
        "content_digest": "fixture-source-digest",
        "content_text": (
            "A finite-dimensional normal transformation has a bounded spectral representation. "
            "A proof can use an orthogonal decomposition. A self-adjoint transformation is a specialization."
        ),
    }


def test_exact_source_acquisition_is_one_use_and_keeps_evaluator_material_out():
    approved = _approved_controller()
    locator = approved.continuous_learning_state["governed_learning_strategy_authority_request"]["source_locator"]
    completed = execute_governed_learning_strategy_exact_source_acquisition(approved, retrieval_adapter=_source)
    acquisition = completed.continuous_learning_state["governed_learning_strategy_acquisition"]
    result = acquisition["result"]
    assert acquisition["claim"]["execution_attempt_count"] == 1
    assert result["retrieval_count"] == 1
    assert result["source_locator"] == locator
    assert "answer_key" not in str(result)
    assert result["internal_verification"]["capability_promotion_prohibited"]
    replay = execute_governed_learning_strategy_exact_source_acquisition(completed, retrieval_adapter=lambda _: (_ for _ in ()).throw(AssertionError("replayed")))
    assert replay.continuous_learning_state["governed_learning_strategy_acquisition"] == acquisition


def test_exact_source_acquisition_fails_closed_when_adapter_changes_locator():
    approved = _approved_controller()
    failed = execute_governed_learning_strategy_exact_source_acquisition(
        approved,
        retrieval_adapter=lambda locator: {**_source(locator), "canonical_locator": "https://other.example/resource"},
    )
    assert failed.continuous_mission_state == "learning_strategy_source_insufficient"
    assert failed.continuous_learning_state["governed_learning_strategy_acquisition"]["status"] == "failed"


def test_exact_source_acquisition_allows_only_trailing_slash_canonicalization():
    approved = _approved_controller()
    locator = approved.continuous_learning_state["governed_learning_strategy_authority_request"]["source_locator"]
    completed = execute_governed_learning_strategy_exact_source_acquisition(
        approved,
        retrieval_adapter=lambda source: {**_source(source), "canonical_locator": f"{source}/"},
    )
    assert completed.continuous_learning_state["governed_learning_strategy_acquisition"]["status"] == "completed"

    rejected = execute_governed_learning_strategy_exact_source_acquisition(
        _approved_controller(),
        retrieval_adapter=lambda source: {**_source(source), "canonical_locator": f"{source}/different"},
    )
    assert rejected.continuous_learning_state["governed_learning_strategy_acquisition"]["status"] == "failed"


def test_terminal_attempt_compiles_one_distinct_restart_safe_replacement_request():
    approved = _approved_controller()
    failed = execute_governed_learning_strategy_exact_source_acquisition(
        approved,
        retrieval_adapter=lambda source: {**_source(source), "canonical_locator": f"{source}/different"},
    )
    old_request = failed.continuous_learning_state["governed_learning_strategy_authority_request"]
    old_claim = failed.continuous_learning_state["governed_learning_strategy_acquisition"]["claim"]
    replacement = compile_replacement_governed_learning_strategy_authority_request(failed)
    request = replacement.continuous_learning_state["governed_learning_strategy_authority_request"]
    assert request["request_id"] != old_request["request_id"]
    assert request["replacement_for_claim_id"] == old_claim["claim_id"]
    assert request["claim_nonce"]
    assert request["source_locator"] == old_request["source_locator"]
    assert request["question_ids"] == old_request["question_ids"]
    assert request["maximum_calls_or_retrievals"] == 1
    acquisition_history = replacement.continuous_learning_state["governed_learning_strategy_acquisition_history"]
    assert acquisition_history[-1]["claim"] == old_claim
    assert replacement.continuous_learning_state["governed_learning_strategy_acquisition"] == {}
    assert replacement.continuous_mission_state == "learning_strategy_awaiting_authority"
    assert compile_replacement_governed_learning_strategy_authority_request(replacement).continuous_learning_state["governed_learning_strategy_authority_request"] == request
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=replacement.session_id),
        export_continuous_mission_restart_state(replacement),
    )
    assert restored.continuous_learning_state["governed_learning_strategy_authority_request"]["request_id"] == request["request_id"]
    assert len([item for item in restored.continuous_developmental_insight_requests if item["request_id"] == request["request_id"]]) == 1


def test_exact_resource_chain_rejects_every_noncanonical_component_change():
    approved = "https://example.test/resource"
    assert is_same_exact_resource_chain(approved, "https://example.test/resource/")
    for changed in (
        "http://example.test/resource",
        "https://other.test/resource",
        "https://example.test:444/resource",
        "https://example.test/other",
        "https://example.test/resource?version=2",
        "https://example.test/resource#section",
    ):
        assert not is_same_exact_resource_chain(approved, changed)


def test_generic_adapter_extracts_only_unrelated_strategy_question_evidence():
    strategy = {
        "strategy_id": "strategy-unrelated", "evidence_digest": "evidence-unrelated",
        "learning_questions": ({"question_id": "question-humidity", "question": "What does humidity mean, how does it relate to climate, and what conditions bound that relationship?", "prerequisite_ids": ("prerequisite-humidity",)},),
        "prerequisite_hypotheses": ({"prerequisite_id": "prerequisite-humidity"},),
    }
    request = {"request_id": "authority-unrelated", "source_identity": "source-unrelated"}
    retrieval = {
        "canonical_locator": "https://example.test/climate", "retrieved_at": "2026-07-21T00:00:00+00:00",
        "retrieval_method": "fixture", "content_digest": "climate-digest",
        "content_text": "Humidity is the amount of water vapor in air.",
    }
    result = compile_strategy_acquisition_result(strategy=strategy, authority_request=request, retrieval=retrieval)
    assert result["outcome"] == "learning_strategy_source_sufficient"
    assert result["claims"][0]["learning_question_ids"] == ("question-humidity",)
    assert "spectral" not in str(result).lower()
