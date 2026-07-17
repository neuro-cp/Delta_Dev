from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    compile_governed_developmental_resource_policy,
    consume_continuous_operator_interaction_response,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
    start_persistent_developmental_agenda,
)
from orchestration.runtime.developmental_resource_policy import (
    compile_developmental_resource_authority_requirement,
    compile_resource_authority_decision,
    compile_resource_policy_candidates,
    observe_developmental_resources,
)
from orchestration.runtime.developmental_interest import compile_persistent_developmental_agenda
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


INSTRUCTION = "Continue your governed developmental agenda. Propose one goal at a time and wait for approval before each mission."


def _agenda() -> dict:
    return {
        "agenda_id": "agenda-1", "status": "proposal_pending", "active_mission_id": "", "pending_proposal_id": "proposal-1",
        "cycle_count": 0, "remaining_session_budget": 3, "remaining_attempt_budget": 3,
        "remaining_proposal_budget": 3, "maximum_consecutive_failures": 2, "last_material_evidence_digest": "evidence-1",
        "mission_outcome_history": (), "cooldown_records": (),
    }


def _proposal() -> dict:
    return {
        "proposal_id": "proposal-1", "selected_interest_id": "interest-1", "domain": "mathematics", "topic": "spectral_theorem",
        "target_capability": "complex_inner_product_space_scope", "measurable_outcome": "apply spectral reasoning on independently sealed complex cases",
        "source_evidence": ("spectral-gap",),
    }


def _candidate(**overrides) -> dict:
    value = {
        "interest_id": "interest-1", "domain": "mathematics", "topic": "spectral_theorem",
        "target_capability": "complex_inner_product_space_scope", "target_behavior": "apply spectral reasoning on independently sealed complex cases",
        "resource_state": "available_retained", "authority_state": "operator_approval_required", "evaluator_state": "evaluation_unavailable",
    }
    return {**value, **overrides}


def _requirement(state: dict, **candidate_overrides):
    return compile_developmental_resource_authority_requirement(
        agenda=_agenda(), proposal=_proposal(), candidate=_candidate(**candidate_overrides),
        mission=state.get("mission") or {}, learning_state=state,
    )


def _source(topic: str, target: str, gap: str, value: float, *, evaluator: bool) -> dict:
    return {
        "source_kind": "retained_evaluation_gap", "domain": "mathematics", "topic": topic,
        "target_capability": target, "target_behavior": f"demonstrate {target.replace('_', ' ')} on an independent case",
        "source_gap_ids": (gap,), "prerequisites": (), "evidence": (f"retained-{topic}",),
        "resource_state": "available_retained", "authority_state": "operator_approval_required",
        "evaluator_authorities": ({"strategy": "deterministic_predicate", "identity": f"{topic}-evaluator", "provenance": (f"retained-{topic}",)},) if evaluator else (),
        "allow_evaluator_acquisition": not evaluator, "expected_learning_value": value, "transfer_value": value - 0.05,
        "prerequisite_value": value - 0.1, "information_gain": value - 0.1, "estimated_effort": 0.3, "estimated_risk": 0.08,
    }


def _policy_request(controller):
    return next(item for item in controller.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_resource_authority" and item.get("status") == "pending")


def test_requirement_identity_inventory_and_policy_ranking_are_deterministic():
    state = {
        "retained_bundle": {"resource_bundle_id": "retained-spectral", "topic": "spectral_theorem", "study_resources": ({"resource_id": "study", "topic": "spectral_theorem"},), "resource_provenance": ("retained-source",)},
        "evaluation_strategy": {"selected_plan": {"plan_id": "sealed-evaluator", "status": "evaluation_plan_ready", "selected_strategy": "deterministic_predicate"}},
    }
    first = _requirement(state)
    second = _requirement(state)
    assert first.requirement_id == second.requirement_id
    observations = observe_developmental_resources(first, learning_state=state)
    candidates = compile_resource_policy_candidates(first, observations, has_alternative=False)
    decision = compile_resource_authority_decision(first, candidates)
    assert observations[0].source_type == "validated_retained_resource"
    assert decision.action_type == "reuse_validated_retained_resource"
    assert len(candidates) <= 11


def test_provisional_and_completed_local_model_results_are_reused_without_promotion():
    provisional_state = {
        "provisional_resource_bundle": {"resource_bundle_id": "provisional-spectral", "topic": "spectral_theorem", "study_resources": ({"resource_id": "study", "topic": "spectral_theorem"},), "provenance": ("advisory-result",)},
        "evaluation_strategy": {"selected_plan": {"plan_id": "sealed", "status": "evaluation_plan_ready", "selected_strategy": "deterministic_predicate"}},
    }
    requirement = _requirement(provisional_state)
    provisional = compile_resource_authority_decision(requirement, compile_resource_policy_candidates(requirement, observe_developmental_resources(requirement, learning_state=provisional_state), has_alternative=False))
    assert provisional.action_type == "reuse_provisional_resource"
    assert provisional_state.get("capability_update") is None

    result_state = {
        "local_model_request": {"request_id": "model-request", "lifecycle_state": "completed", "request_digest": "need-1"},
        "local_model_result_reference": {"result_id": "model-result", "response_digest": "response-1"},
        "evaluation_strategy": {"selected_plan": {"plan_id": "sealed", "status": "evaluation_plan_ready", "selected_strategy": "deterministic_predicate"}},
    }
    requirement = _requirement(result_state)
    decision = compile_resource_authority_decision(requirement, compile_resource_policy_candidates(requirement, observe_developmental_resources(requirement, learning_state=result_state), has_alternative=False))
    assert decision.action_type == "reuse_existing_local_model_result"


def test_policy_compiles_all_governed_authority_paths_without_external_execution():
    requirement = _requirement({})
    candidates = compile_resource_policy_candidates(requirement, observe_developmental_resources(requirement, learning_state={}), has_alternative=True)
    actions = {item.action_type for item in candidates}
    assert {
        "request_local_model_resource", "request_operator_teaching_resource", "request_operator_sealed_evaluator",
        "request_external_research_authority", "request_execution_authority", "defer_until_state_change",
        "return_to_agenda_alternative", "abandon_goal",
    }.issubset(actions)
    external = next(item for item in candidates if item.action_type == "request_external_research_authority")
    assert external.expected_outcome == "awaiting_operator_authority"
    assert external.permission_state == "operator_authority_required"


def test_agenda_evaluator_blocker_creates_one_scoped_request_and_rejection_selects_alternative():
    spectral = _source("spectral_theorem", "complex_inner_product_space_scope", "spectral-gap", 0.95, evaluator=False)
    induction = _source("mathematical_induction", "proof_structure", "induction-gap", 0.7, evaluator=True)
    controller = replace(start_continuous_runtime_controller(session_id="policy-agenda"), continuous_learning_state={"interest_sources": (spectral, induction)})
    proposed = start_persistent_developmental_agenda(controller, INSTRUCTION)
    goal = next(item for item in proposed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval" and item.get("status") == "pending")
    policy = consume_continuous_operator_interaction_response(
        proposed, request_id=goal["request_id"], response_kind="developmental_goal_approval",
        selected_option="approve_developmental_goal", operator_text="Assess this blocked goal.", approved_scope=goal["authority_scope"],
    )
    request = _policy_request(policy)
    assert request["action_type"] == "request_operator_sealed_evaluator"
    assert len([item for item in policy.continuous_developmental_insight_requests if item.get("status") == "pending"]) == 1
    rejected = consume_continuous_operator_interaction_response(
        policy, request_id=request["request_id"], response_kind="developmental_resource_authority",
        selected_option="reject_scoped_authority", operator_text="Use another eligible goal.", approved_scope="",
    )
    next_goal = next(item for item in rejected.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval" and item.get("status") == "pending")
    assert next_goal["proposal_id"] != goal["proposal_id"]
    assert rejected.continuous_learning_state["developmental_resource_policy"]["status"] == "rejected"


def test_authority_approval_is_scoped_and_restart_does_not_duplicate_request():
    spectral = _source("spectral_theorem", "complex_inner_product_space_scope", "spectral-gap", 0.95, evaluator=False)
    controller = replace(start_continuous_runtime_controller(session_id="policy-restart"), continuous_learning_state={"interest_sources": (spectral,)})
    proposed = start_persistent_developmental_agenda(controller, INSTRUCTION)
    goal = next(item for item in proposed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval")
    policy = consume_continuous_operator_interaction_response(proposed, request_id=goal["request_id"], response_kind="developmental_goal_approval", selected_option="approve_developmental_goal", operator_text="Assess.", approved_scope=goal["authority_scope"])
    request = _policy_request(policy)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="policy-restart"), export_continuous_mission_restart_state(policy))
    replay = compile_governed_developmental_resource_policy(restored)
    assert _policy_request(replay)["request_id"] == request["request_id"]
    approved = consume_continuous_operator_interaction_response(
        replay, request_id=request["request_id"], response_kind="developmental_resource_authority",
        selected_option="approve_scoped_authority", operator_text="Supply sealed cases only.", approved_scope=request["authority_scope"],
    )
    authority = approved.continuous_learning_state["resource_policy_authorities"]["sealed_evaluator"]
    assert authority["scope"] == request["authority_scope"]
    assert approved.continuous_mission_state == "developmental_resource_authority_granted_pending_material"
    assert not approved.continuous_active_subgoal


def test_policy_clarification_creates_one_scoped_follow_up_without_authority():
    spectral = _source("spectral_theorem", "complex_inner_product_space_scope", "spectral-gap", 0.95, evaluator=False)
    controller = replace(start_continuous_runtime_controller(session_id="policy-clarification"), continuous_learning_state={"interest_sources": (spectral,)})
    proposed = start_persistent_developmental_agenda(controller, INSTRUCTION)
    goal = next(item for item in proposed.continuous_developmental_insight_requests if item.get("request_kind") == "developmental_goal_approval")
    policy = consume_continuous_operator_interaction_response(proposed, request_id=goal["request_id"], response_kind="developmental_goal_approval", selected_option="approve_developmental_goal", operator_text="Assess.", approved_scope=goal["authority_scope"])
    request = _policy_request(policy)
    clarified = consume_continuous_operator_interaction_response(
        policy, request_id=request["request_id"], response_kind="developmental_resource_authority",
        selected_option="ask_for_clarification", operator_text="Specify the sealed coverage.", approved_scope="",
    )
    pending = [item for item in clarified.continuous_developmental_insight_requests if item.get("status") == "pending"]
    assert len(pending) == 1
    assert pending[0]["request_id"] != request["request_id"]
    assert clarified.continuous_operator_interaction_responses[-1]["authority_granted"] is False


def test_local_model_policy_approval_creates_one_shared_unexecuted_request(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "shared-ledger"))
    agenda = compile_persistent_developmental_agenda(operator_scope=INSTRUCTION, material_digest="policy-local-model").as_dict()
    state = {
        "developmental_agenda": agenda,
        "developmental_interest": {"proposal": _proposal(), "candidate_interests": (_candidate(),)},
        "evaluation_strategy": {"selected_plan": {"plan_id": "ready-evaluator", "status": "evaluation_plan_ready", "selected_strategy": "deterministic_predicate"}},
    }
    controller = replace(start_continuous_runtime_controller(session_id="policy-local-model"), continuous_learning_state=state)
    proposed = compile_governed_developmental_resource_policy(controller)
    request = _policy_request(proposed)
    assert request["action_type"] == "request_local_model_resource"
    approved = consume_continuous_operator_interaction_response(
        proposed, request_id=request["request_id"], response_kind="developmental_resource_authority",
        selected_option="approve_scoped_authority", operator_text="One advisory request only.", approved_scope=request["authority_scope"],
    )
    model_request = approved.continuous_learning_state["local_model_request"]
    assert model_request["lifecycle_state"] == "pending_operator_approval"
    assert model_request["execution_attempt_count"] == 0
    assert LocalModelRequestResultLedger().observe_request(model_request["request_id"])["execution_attempt_count"] == 0
    replay = compile_governed_developmental_resource_policy(approved)
    assert replay.continuous_learning_state["local_model_request"]["request_id"] == model_request["request_id"]


def test_corrupt_policy_restart_fails_closed():
    controller = replace(start_continuous_runtime_controller(session_id="policy-corrupt"), continuous_learning_state={"developmental_resource_policy": {"requirement": {"requirement_id": "bad"}, "status": "authority_pending"}})
    restart = export_continuous_mission_restart_state(controller)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="policy-corrupt"), restart)
    assert restored.continuous_mission_state == "developmental_resource_policy_blocked"
    assert restored.continuous_learning_state["developmental_resource_policy"]["status"] == "unavailable"


def test_no_valid_policy_is_explicit_and_creates_no_authority_request_loop():
    requirement = _requirement({})
    requirement = replace(
        requirement,
        resource_budget=0,
        request_budget=0,
        authority_request_budget=0,
        blockers=("authority_permanently_unavailable",),
    )
    candidates = compile_resource_policy_candidates(requirement, (), has_alternative=False)
    decision = compile_resource_authority_decision(requirement, candidates)
    assert decision.action_type == "resource_policy_unavailable"
    assert not decision.target_authority_request_id
    assert all(not item.availability for item in candidates)


def test_execution_defer_abandon_and_alternative_actions_are_governed_candidates():
    execution_requirement = _requirement({}, execution_required=True)
    candidates = compile_resource_policy_candidates(execution_requirement, (), has_alternative=False)
    execution = next(item for item in candidates if item.action_type == "request_execution_authority")
    assert execution.availability is True

    redundant = replace(_requirement({}), resource_budget=0, request_budget=0, authority_request_budget=0, blockers=("goal_redundant",))
    abandoned = compile_resource_authority_decision(redundant, compile_resource_policy_candidates(redundant, (), has_alternative=False))
    assert abandoned.action_type == "abandon_goal"

    alternate = replace(_requirement({}), resource_budget=0, request_budget=0, authority_request_budget=0, blockers=("authority_permanently_unavailable",))
    alternative = compile_resource_authority_decision(alternate, compile_resource_policy_candidates(alternate, (), has_alternative=True))
    assert alternative.action_type == "return_to_agenda_alternative"
