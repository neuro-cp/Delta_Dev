from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_constructive_grounding,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.governed_constructive_grounding import (
    compile_constructive_grounding_assessment,
    validate_constructive_grounding_assessment,
    compile_independent_constructive_grounding_verification,
    compile_advisory_claim_verification_targets,
)


def test_advisory_packet_cannot_verify_constructive_facets_without_retained_derivation():
    assessment = {
        "relation_id": "relation",
        "relation_proposal": {"target_question_id": "question", "required_relation_facets": ("scope", "guarantee")},
        "source_review": {"source_claim_ids": ("claim-a",), "verified_relation_facets": ()},
        "followup_source_review": {"source_claim_ids": ("claim-b",), "verified_relation_facets": ()},
    }
    provider_result = {"response_digest": "raw", "sealed_advisory_packet": {"packet_digest": "packet", "facet_explanations": ({"facet": "scope", "explanation": "advisory", "assumptions": (), "uncertainty": "unknown"}, {"facet": "guarantee", "explanation": "advisory", "assumptions": (), "uncertainty": "unknown"})}}
    result = compile_independent_constructive_grounding_verification(assessment=assessment, provider_result=provider_result)
    assert result["outcome"] == "finite_dimensional_constructive_grounding_partial"
    assert {item["status"] for item in result["facet_decisions"]} == {"unsupported"}
    assert result["capability_update_prohibited"] is True


def test_generic_advisory_text_cannot_become_a_controller_authored_source_query():
    assessment = {"relation_id": "relation", "relation_proposal": {"target_question_id": "question", "target_question": "What does finite-dimensional mean, how does it relate to spectral theorem?"}}
    provider_result = {"response_digest": "raw", "sealed_advisory_packet": {"packet_digest": "packet", "facet_explanations": ({"facet": "scope", "explanation": "Scope contribution explains a concept in a broader context.", "assumptions": ()},)}}
    result = compile_advisory_claim_verification_targets(assessment=assessment, provider_result=provider_result)
    assert result["outcome"] == "atomic_verification_targets_unavailable"
    assert result["targets"] == ()
    assert result["rejected_advisory_claims"]
from tests.runtime_gsr.test_governed_learning_strategy_single_question_revision import _partial_controller
from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_learning_strategy_evidence_linkage_reassessment,
    compile_governed_learning_strategy_single_question_revision,
)


def _linkage_ready_controller():
    return compile_governed_learning_strategy_evidence_linkage_reassessment(
        compile_governed_learning_strategy_single_question_revision(_partial_controller())
    )


def test_constructive_grounding_selects_one_existing_candidate_without_retrieval():
    grounded = compile_governed_constructive_grounding(_linkage_ready_controller())
    assessment = grounded.continuous_learning_state["governed_constructive_grounding"]
    request = assessment["authority_request"]
    assert assessment["selected_path"] == "existing_metadata_candidate"
    assert assessment["sufficiency_status"] == "unresolved"
    assert not assessment["derivation_steps"]
    assert request["maximum_retrieval_count"] == 1
    assert request["status"] == "pending"
    assert grounded.continuous_mission_state.endswith("_exact_source_authority_pending")
    assert not grounded.continuous_active_subgoal


def test_constructive_grounding_rejects_leakage_and_unsupported_derivation():
    controller = _linkage_ready_controller()
    state = controller.continuous_learning_state
    assessment = compile_constructive_grounding_assessment(
        strategy=state["governed_learning_strategy"], latest_revision=state["governed_learning_strategy_resource_revision"],
        acquisition_result=state["governed_learning_strategy_discovered_source_retrieval"]["result"],
        linkage_reassessment=state["governed_learning_strategy_evidence_linkage_reassessment"],
        discovery_result=state["governed_learning_strategy_source_discovery"]["result"],
    )
    assessment["derivation_steps"] = ({"claim": "unsupported"},)
    assessment["evaluator_view"] = {"answer_key": "secret"}
    validation = validate_constructive_grounding_assessment(
        assessment, strategy=state["governed_learning_strategy"], acquisition_result=state["governed_learning_strategy_discovered_source_retrieval"]["result"],
        linkage_reassessment=state["governed_learning_strategy_evidence_linkage_reassessment"],
    )
    assert not validation["accepted"]
    assert {"unsupported_derivation_present", "evaluator_only_material_present"}.issubset(validation["errors"])


def test_constructive_grounding_is_topic_neutral_and_restart_duplicate_safe():
    controller = _linkage_ready_controller()
    state = controller.continuous_learning_state
    strategy = {"strategy_id": "synthetic", "learning_questions": ({"question_id": "evaporation", "question": "What does evaporation mean?", "prerequisite_ids": ("node",)},)}
    acquisition = {"acquisition_result_id": "synthetic-acquisition", "result_digest": "synthetic-digest", "source_locator": "https://used.example/a", "claims": ({"claim_id": "premise", "claim_text": "Evaporation is mentioned in the retained source.", "source_excerpt_reference": "page:1"},)}
    linkage = {"reassessment_id": "synthetic-link", "reassessment_digest": "synthetic-link-digest", "links": ({"question_id": "evaporation", "claim_id": "premise", "sufficiency_status": "linked_but_not_sufficient"},)}
    discovery = {"candidates": ({"candidate_id": "candidate", "title": "Institutional notes", "canonical_locator": "https://new.example/b", "organization": "Example University", "source_type": "institutional_notes", "question_ids": ("evaporation",), "relevance_rationale": "Metadata covers evaporation.", "metadata_confidence": 0.9, "expected_information_gain": 0.9, "retrieval_cost": 0.2},)}
    synthetic = compile_constructive_grounding_assessment(strategy=strategy, latest_revision={}, acquisition_result=acquisition, linkage_reassessment=linkage, discovery_result=discovery)
    assert synthetic["selected_candidate_id"] == "candidate"
    grounded = compile_governed_constructive_grounding(controller)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id=grounded.session_id), export_continuous_mission_restart_state(grounded))
    assert restored.continuous_learning_state["governed_constructive_grounding"]["assessment_id"] == grounded.continuous_learning_state["governed_constructive_grounding"]["assessment_id"]
    assert compile_governed_constructive_grounding(restored).continuous_learning_state["governed_constructive_grounding"] == restored.continuous_learning_state["governed_constructive_grounding"]
