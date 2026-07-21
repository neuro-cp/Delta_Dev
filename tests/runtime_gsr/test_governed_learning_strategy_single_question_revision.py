from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_learning_strategy_evidence_linkage_reassessment,
    compile_governed_learning_strategy_single_question_revision,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.governed_learning_strategy_single_question_revision import (
    compile_single_question_learning_strategy_revision,
    validate_single_question_learning_strategy_revision,
)
from tests.runtime_gsr.test_governed_learning_strategy_discovered_source_retrieval_authority import _discovery_completed_controller


def _partial_controller():
    base = _discovery_completed_controller()
    question_id = "finite-dimensional-question"
    strategy = {
        "strategy_id": "single-question-strategy",
        "learning_questions": ({
            "question_id": question_id,
            "question": "What does finite-dimensional mean, how does it relate to spectral_theorem, and what conditions bound that relationship?",
            "sufficiency_condition": "A source directly explains finite-dimensional scope.",
        },),
    }
    discovery = {
        "discovery_result_id": "single-question-discovery",
        "result_digest": "single-question-discovery-digest",
        "candidates": ({
            "candidate_id": "mit-candidate", "title": "MIT notes", "canonical_locator": "https://math.mit.edu/example.pdf",
            "organization": "MIT", "source_type": "institutional_notes", "question_ids": (question_id,),
            "relevance_rationale": "Metadata identifies finite-dimensional scope.", "metadata_confidence": 0.92,
            "expected_information_gain": 0.9, "retrieval_cost": 0.2,
        }, {
            "candidate_id": "ttic-candidate", "title": "TTIC notes", "canonical_locator": "https://ttic.edu/example.pdf",
            "organization": "TTIC", "source_type": "institutional_notes", "question_ids": (question_id,),
            "relevance_rationale": "Metadata identifies finite-dimensional scope.", "metadata_confidence": 0.90,
            "expected_information_gain": 0.9, "retrieval_cost": 0.2,
        }),
    }
    result = {
        "acquisition_result_id": "single-question-acquisition", "result_digest": "single-question-acquisition-digest",
        "outcome": "learning_strategy_source_partially_sufficient",
        "question_sufficiency": ({"question_id": question_id, "status": "unanswered", "missing_information": "raw matcher missed finite-dimensional"},),
        "claims": ({"claim_id": "hyphenated-scope-claim", "claim_text": "For a \ufb01nite dimen- sional inner product space, scope is bounded.", "source_excerpt_reference": "sentence:1"},),
    }
    return replace(base, continuous_learning_state={
        **base.continuous_learning_state,
        "governed_learning_strategy": strategy,
        "governed_learning_strategy_source_discovery": {"status": "completed", "result": discovery},
        "governed_learning_strategy_discovered_source_retrieval": {"status": "completed", "result": result},
    })


def test_single_question_revision_detects_pdf_hyphenation_without_relabeling_history():
    controller = _partial_controller()
    revised = compile_governed_learning_strategy_single_question_revision(controller)
    record = revised.continuous_learning_state["governed_learning_strategy_single_question_revision"]
    result = controller.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["result"]
    assert record["outcome"] == "finite_dimensional_evidence_linkage_repair_required"
    assert record["active_question_id"] == result["question_sufficiency"][0]["question_id"]
    assert result["question_sufficiency"][0]["status"] == "unanswered"
    assert record["linkage_evidence"][0]["normalized_term_present"]
    assert not record["linkage_evidence"][0]["original_term_present"]
    assert record["retrieval_not_performed"]
    assert not record["retrieval_authority_compiled"]


def test_single_question_revision_ranks_retained_metadata_and_rejects_evaluator_leakage():
    controller = _partial_controller()
    state = controller.continuous_learning_state
    revision = compile_single_question_learning_strategy_revision(
        strategy=state["governed_learning_strategy"],
        acquisition_result=state["governed_learning_strategy_discovered_source_retrieval"]["result"],
        discovery_result=state["governed_learning_strategy_source_discovery"]["result"],
    )
    assert len(revision["existing_candidate_ranking"]) >= 1
    assert revision["recommended_candidate_id"] == ""
    revision["existing_candidate_ranking"] = ({"answer_key": "leak"},)
    validation = validate_single_question_learning_strategy_revision(
        revision, strategy=state["governed_learning_strategy"],
        acquisition_result=state["governed_learning_strategy_discovered_source_retrieval"]["result"],
        discovery_result=state["governed_learning_strategy_source_discovery"]["result"],
    )
    assert not validation["accepted"]
    assert "evaluator_only_material_present" in validation["errors"]


def test_single_question_revision_excludes_an_already_retrieved_candidate():
    controller = _partial_controller()
    state = controller.continuous_learning_state
    discovery = dict(state["governed_learning_strategy_source_discovery"]["result"])
    candidate = dict(discovery["candidates"][0])
    result = dict(state["governed_learning_strategy_discovered_source_retrieval"]["result"])
    result["source_locator"] = candidate["canonical_locator"]
    revision = compile_single_question_learning_strategy_revision(
        strategy=state["governed_learning_strategy"], acquisition_result=result, discovery_result=discovery,
    )
    assert candidate["candidate_id"] not in {item["candidate_id"] for item in revision["existing_candidate_ranking"]}


def test_single_question_revision_restores_once_without_request_or_retrieval():
    revised = compile_governed_learning_strategy_single_question_revision(_partial_controller())
    restart = export_continuous_mission_restart_state(revised)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id=revised.session_id), restart)
    record = restored.continuous_learning_state["governed_learning_strategy_single_question_revision"]
    assert record["revision_id"] == revised.continuous_learning_state["governed_learning_strategy_single_question_revision"]["revision_id"]
    assert not any(item.get("request_kind") == "governed_learning_strategy_discovered_source_retrieval_authority" and item.get("status") == "pending" for item in restored.continuous_developmental_insight_requests)
    replay = compile_governed_learning_strategy_single_question_revision(restored)
    assert replay.continuous_learning_state["governed_learning_strategy_single_question_revision"] == record


def test_evidence_linkage_reassessment_is_offline_and_does_not_change_original_sufficiency():
    revised = compile_governed_learning_strategy_single_question_revision(_partial_controller())
    reassessed = compile_governed_learning_strategy_evidence_linkage_reassessment(revised)
    result = revised.continuous_learning_state["governed_learning_strategy_discovered_source_retrieval"]["result"]
    record = reassessed.continuous_learning_state["governed_learning_strategy_evidence_linkage_reassessment"]
    assert result["question_sufficiency"][0]["status"] == "unanswered"
    assert record["retrieval_not_performed"]
    assert record["capability_promotion_prohibited"]
    assert reassessed.continuous_mission_state == "learning_strategy_evidence_linkage_reassessed"
