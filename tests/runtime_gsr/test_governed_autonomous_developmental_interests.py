from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_developmental_interest_proposal,
    consume_continuous_operator_interaction_response,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_interest import (
    compile_developmental_goal_proposal,
    compile_developmental_interest_candidates,
    source_records_from_state,
)
from orchestration.runtime.continuous_operator_monitor import (
    ContinuousMonitorSnapshot,
    build_operator_interaction_requests,
)
from orchestration.runtime.continuous_mission_foundation import CapabilityKnowledgeRecord


INSTRUCTION = "Continue developing your capabilities. Identify one valuable thing you could learn next, explain why, and ask for approval before beginning."


def _ready_source(**overrides):
    source = {
        "source_kind": "retained_evaluation_gap",
        "domain": "mathematics",
        "topic": "mathematical_induction",
        "target_capability": "proof_structure",
        "target_behavior": "demonstrate base case, induction hypothesis, and induction step on unseen cases",
        "source_gap_ids": ("induction-proof-structure-gap",),
        "prerequisites": (),
        "evidence": ("retained-mathematical-induction-v1", "baseline-induction-structure"),
        "resource_state": "available_retained",
        "authority_state": "operator_approval_required",
        "evaluator_authorities": ({"strategy": "deterministic_predicate", "identity": "retained-induction-evaluator", "provenance": ("retained-mathematical-induction-v1",)},),
        "expected_learning_value": 0.8,
        "transfer_value": 0.7,
        "prerequisite_value": 0.72,
        "information_gain": 0.68,
        "estimated_effort": 0.3,
        "estimated_risk": 0.08,
    }
    return {**source, **overrides}


def _compiled(*sources, active=(), rejected=(), inventory=()):
    return compile_developmental_interest_candidates(
        origin_state_id="interest-state", operator_context=INSTRUCTION, sources=sources,
        capability_inventory=inventory, active_or_recent_semantics=active, rejected_semantics=rejected,
    )


def _controller(*sources):
    return replace(
        start_continuous_runtime_controller(session_id="governed-interest"),
        continuous_learning_state={"interest_sources": tuple(sources)},
    )


def _demonstrated_record(capability_id: str) -> CapabilityKnowledgeRecord:
    return CapabilityKnowledgeRecord(
        capability_id=capability_id, original_weakness="bounded retained evaluation gap",
        evidence=("sealed-held-out-pass",), first_incorrect_transition="prior bounded gap -> independently demonstrated behavior",
        strategies_attempted=("retained evaluator",), failed_approaches=(), successful_mechanism="independent sealed evaluation",
        exact_candidate="retained learning attempt", tests_added=("existing sealed case",), metrics_before_after={"target": 1.0},
        controls=("control pass",), adversarial_evidence=("adversarial pass",), held_out_evidence={"transfer": "pass"},
        reproduction_evidence="retained case", provider_contribution="none", local_repair_contribution="local learning",
        application_evidence="none", regression_evidence="sealed evaluator", reassessment="satisfied",
        residual_uncertainty="narrow requested scope demonstrated", reusable_process_rules=("independent evidence required",),
        evidence_stage="behaviorally_demonstrated", capability_acquired=True,
        behavioral_evaluation_ref="sealed-independent-evaluation",
    )


def test_interest_candidates_are_evidence_derived_bounded_and_deterministic():
    sources = tuple(_ready_source(target_capability=f"proof_structure_{index}") for index in range(7))
    first = _compiled(*sources)
    same = _compiled(*sources)
    assert len(first) == 5
    assert [item.interest_id for item in first] == [item.interest_id for item in same]
    assert all(item.current_capability_evidence for item in first)
    assert all(item.topic != "random_topic" for item in first)


def test_redundant_active_rejected_and_broad_candidates_are_retained_with_reasons():
    ready = _ready_source()
    redundant = _compiled(ready, inventory=({"capability_id": "proof_structure", "status": "functional"},))[0]
    assert redundant.status == "rejected"
    assert "capability_already_demonstrated_at_requested_scope" in redundant.rejection_reasons
    active = _compiled(ready, active=(_compiled(ready)[0].semantic_identity,))[0]
    assert "equivalent_goal_active_or_recently_completed" in active.rejection_reasons
    broad = _compiled(_ready_source(target_capability="Become better at science", target_behavior=""))[0]
    assert broad.status == "rejected"
    assert "target_behavior_undefined_or_too_broad" in broad.rejection_reasons


def test_controller_uses_authoritative_knowledge_ledger_to_reject_demonstrated_interest():
    controller = replace(
        _controller(_ready_source(target_capability="already_verified_capability")),
        continuous_knowledge_ledger=(_demonstrated_record("already_verified_capability").as_dict(),),
    )
    exhausted = compile_governed_developmental_interest_proposal(controller, INSTRUCTION)
    candidate = exhausted.continuous_learning_state["developmental_interest"]["candidate_interests"][0]
    assert exhausted.continuous_mission_state == "developmental_interest_exhausted"
    assert "capability_already_demonstrated_at_requested_scope" in candidate["rejection_reasons"]


def test_evaluator_missing_yields_only_evaluator_acquisition_interest():
    spectral = _ready_source(
        topic="spectral_theorem",
        target_capability="complex_inner_product_space_scope",
        target_behavior="apply spectral reasoning in complex inner-product spaces",
        source_gap_ids=("complex-spectral-gap",),
        evaluator_authorities=(),
        allow_evaluator_acquisition=True,
    )
    candidate = _compiled(spectral)[0]
    proposal = compile_developmental_goal_proposal(operator_context=INSTRUCTION, candidates=(candidate,))
    assert candidate.candidate_class == "acquire_evaluator_authority"
    assert candidate.evaluator_state == "evaluation_unavailable"
    assert proposal is not None
    assert proposal.proposed_goal.startswith("Acquire independently sealed evaluation material")


def test_existing_spectral_next_gap_is_compiled_as_evaluator_acquisition_not_learning():
    sources = source_records_from_state(
        learning_state={
            "next_learning_gap": {
                "gap_id": "spectral-complex-gap",
                "capability_dimension": "complex_inner_product_space_scope",
                "reason": "finite real symmetric-matrix evidence is demonstrated while complex scope remains unassessed",
                "prerequisites": ("spectral_theorem_understanding",),
                "authority": "existing_local_model_or_retained_resource_required",
            },
        },
        capability_inventory=(),
    )
    candidate = _compiled(*sources)[0]
    assert candidate.topic == "spectral_theorem"
    assert candidate.candidate_class == "acquire_evaluator_authority"
    assert candidate.status == "candidate_interest"


def test_evaluator_and_resource_readiness_outrank_novelty_only():
    ready = _ready_source(novelty=0.0)
    novelty_only = _ready_source(
        topic="unfamiliar_subject", target_capability="unverified_transfer", resource_state="unknown",
        evaluator_authorities=(), novelty=1.0, expected_learning_value=0.95, transfer_value=0.95,
    )
    ranked = _compiled(ready, novelty_only)
    assert ranked[0].target_capability == "proof_structure"
    assert ranked[1].status == "blocked"


def test_controller_stops_before_approval_then_approves_exactly_one_existing_learning_mission():
    proposed = compile_governed_developmental_interest_proposal(_controller(_ready_source()), INSTRUCTION)
    interest = proposed.continuous_learning_state["developmental_interest"]
    request = next(item for item in proposed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval")
    assert proposed.continuous_mission_state == "awaiting_operator_insight"
    assert not proposed.continuous_active_subgoal
    assert interest["proposal"]["status"] == "pending_operator_approval"
    approved = consume_continuous_operator_interaction_response(
        proposed, request_id=request["request_id"], response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal", operator_text="Proceed with the bounded induction goal.",
        approved_scope=request["authority_scope"],
    )
    assert approved.continuous_mission_state == "learning_subgoal_active"
    assert approved.continuous_active_subgoal["execution_kind"] == "developmental_learning"
    assert approved.continuous_learning_state["developmental_interest"]["proposal_status"] == "approved_developmental_goal"
    replay = consume_continuous_operator_interaction_response(
        approved, request_id=request["request_id"], response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal", operator_text="duplicate", approved_scope=request["authority_scope"],
    )
    assert len(replay.continuous_operator_interaction_responses) == 1


def test_rejection_cooldown_restart_and_no_valid_interest_are_honest():
    proposed = compile_governed_developmental_interest_proposal(_controller(_ready_source()), INSTRUCTION)
    request = next(item for item in proposed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval")
    rejected = consume_continuous_operator_interaction_response(
        proposed, request_id=request["request_id"], response_kind="developmental_goal_approval",
        selected_option="reject_developmental_goal", operator_text="Not now.", approved_scope="",
    )
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="governed-interest"), export_continuous_mission_restart_state(rejected),
    )
    replay = compile_governed_developmental_interest_proposal(restored, INSTRUCTION)
    assert replay.continuous_mission_state == "developmental_interest_exhausted"
    assert not [item for item in replay.continuous_developmental_insight_requests if item.get("status") == "pending"]
    empty = compile_governed_developmental_interest_proposal(start_continuous_runtime_controller(session_id="empty-interest"), INSTRUCTION)
    assert empty.continuous_mission_state == "developmental_interest_exhausted"
    assert not empty.continuous_developmental_insight_requests


def test_clarification_creates_one_scoped_follow_up_without_learning_activation():
    proposed = compile_governed_developmental_interest_proposal(_controller(_ready_source()), INSTRUCTION)
    request = next(item for item in proposed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval")
    clarified = consume_continuous_operator_interaction_response(
        proposed, request_id=request["request_id"], response_kind="developmental_goal_approval",
        selected_option="ask_for_clarification", operator_text="Clarify evaluator coverage.", approved_scope="",
    )
    follow_up = [item for item in clarified.continuous_developmental_insight_requests if item.get("status") == "pending"]
    assert clarified.continuous_mission_state == "awaiting_operator_insight"
    assert not clarified.continuous_active_subgoal
    assert len(follow_up) == 1
    assert follow_up[0]["clarification_round"] == 1
    assert "ask_for_clarification" not in follow_up[0]["permitted_responses"]


def test_material_evidence_change_can_version_after_rejection_while_missing_resource_blocks():
    first = _compiled(_ready_source())[0]
    blocked = _compiled(_ready_source(resource_state="unavailable"))[0]
    assert blocked.status == "blocked"
    assert "resource_path_unavailable" in blocked.rejection_reasons
    changed = _compiled(_ready_source(evidence=("retained-mathematical-induction-v2", "new-transfer-failure")), rejected=(first.semantic_identity,))[0]
    assert changed.semantic_identity != first.semantic_identity
    assert changed.status == "candidate_interest"


def test_monitor_renders_the_existing_controller_created_goal_request():
    proposed = compile_governed_developmental_interest_proposal(_controller(_ready_source()), INSTRUCTION)
    request = next(item for item in proposed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval")
    snapshot = ContinuousMonitorSnapshot(
        supervisor_root="pilot", worker_state="running", status_timestamp="2026-07-17T00:00:00+00:00",
        mission_state="awaiting_operator_insight", main_goal="development", active_subgoal="",
        completed_main_goal_ids=(), completed_main_goals=0, knowledge_records=0, pending_application_decision_id="", api_enabled=False,
        confidence=0.7, needs_additional_insight=True, developmental_gaps=(), next_candidates=(),
        operator_interaction_requests=(request,), observation_timestamp="2026-07-17T00:00:00+00:00",
    )
    rendered = build_operator_interaction_requests(snapshot)
    assert len(rendered) == 1
    assert rendered[0].request_id == request["request_id"]
    assert "approve_developmental_goal" in rendered[0].permitted_responses
