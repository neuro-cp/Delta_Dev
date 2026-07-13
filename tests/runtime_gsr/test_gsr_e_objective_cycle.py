from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path
from dataclasses import replace
import json
from pathlib import Path
import shutil as py_shutil

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _objective() -> gsr.DevelopmentObjective:
    return gsr.make_development_objective(
        "Coordinate a governed multi-step objective without execution.",
        scope=("observation", "diagnosis", "proposal", "sandbox_planning"),
        success_criteria=("operator_review_ready",),
        sequence=40,
    )


def _cycle() -> gsr.GovernedObjectiveCycle:
    return gsr.make_governed_objective_cycle(_objective(), sequence=41)


def _request(cycle: gsr.GovernedObjectiveCycle | None = None) -> gsr.ObjectiveCycleTransitionRequest:
    cycle = cycle or _cycle()
    return gsr.make_cycle_transition_request(
        cycle,
        requested_stage="observation_requested",
        requested_substage="awaiting_operator_observation_review",
        artifact_type="observation_ledger",
        artifact_id="ledger-reference-only",
        eligibility_claims=("objective_authorized",),
        required_evidence_refs=("operator-objective",),
        required_authorization_scope=("objective_cycle_transition",),
        forbidden_scope=("sandbox_execution", "source_mutation", "provider_call"),
    )


def _authorization(request: gsr.ObjectiveCycleTransitionRequest | None = None) -> gsr.ObjectiveCycleTransitionAuthorization:
    request = request or _request()
    return gsr.make_cycle_transition_authorization(
        request,
        allowed_scope=("objective_cycle_transition",),
        forbidden_scope=("sandbox_execution", "source_mutation", "provider_call"),
        expires_after_sequence=request.requested_sequence + 3,
    )


def test_e1a_lifecycle_constants_exclude_execution_states():
    assert "objective_authorized" in gsr.GSR_E1_LIFECYCLE_STATES
    assert "future_sandbox_execution_eligible" in gsr.GSR_E1_LIFECYCLE_STATES
    assert "sandbox_executing" not in gsr.GSR_E1_LIFECYCLE_STATES
    assert "applying" not in gsr.GSR_E1_LIFECYCLE_STATES
    assert set(gsr.GSR_E1_UNREACHABLE_EXECUTION_STATES).isdisjoint(gsr.GSR_E1_LIFECYCLE_STATES)


def test_e1a_cycle_contract_requires_operator_attention_and_blocks_autonomy():
    objective = _objective()
    cycle = gsr.make_governed_objective_cycle(objective, sequence=41)

    assert cycle.objective_id == objective.objective_id
    assert cycle.objective_snapshot["objective_id"] == objective.objective_id
    assert cycle.current_stage == "objective_authorized"
    assert cycle.current_substage == "awaiting_transition_request"
    assert cycle.active_artifact_type == "development_objective"
    assert cycle.active_artifact_id == objective.objective_id
    assert gsr.cycle_requires_operator_attention(cycle) is True
    assert gsr.cycle_can_continue_automatically(cycle) is False
    assert cycle.autonomous_continuation_prohibited is True
    assert cycle.background_execution_prohibited is True
    assert cycle.persistence_prohibited is True


def test_e1a_transition_request_and_authorization_are_inert_contracts():
    cycle = _cycle()
    request = _request(cycle)
    authorization = _authorization(request)

    assert request.cycle_id == cycle.cycle_id
    assert request.from_stage == cycle.current_stage
    assert request.requested_stage == "observation_requested"
    assert request.creates_execution is False
    assert request.creates_background_work is False
    assert request.creates_persistence is False
    assert gsr.cycle_transition_executes_stage(request) is False

    assert authorization.request_id == request.request_id
    assert authorization.operator_authority == gsr.OPERATOR_CONTROLLED_AUTHORITY
    assert authorization.allowed_from_stage == request.from_stage
    assert authorization.allowed_to_stage == request.requested_stage
    assert authorization.allowed_substage == request.requested_substage
    assert authorization.one_shot is True
    assert authorization.consumed is False


def test_e1a_transition_record_is_a_reviewable_record_not_application():
    request = _request()
    authorization = _authorization(request)
    record = gsr.make_objective_cycle_transition_record(
        request,
        authorization,
        result="authorized_for_future_transition_review",
    )

    assert record.cycle_id == request.cycle_id
    assert record.request_id == request.request_id
    assert record.authorization_id == authorization.authorization_id
    assert record.to_stage == request.requested_stage
    assert record.operator_controlled is True
    assert record.execution_performed is False
    assert record.automatic_continuation is False
    assert gsr.cycle_transition_executes_stage(record) is False


def test_e1a_result_flags_do_not_execute_or_authorize_application():
    cycle = _cycle()
    request = _request(cycle)
    authorization = _authorization(request)
    record = gsr.make_objective_cycle_transition_record(request, authorization)
    result = gsr.ObjectiveCycleTransitionResult(
        accepted=True,
        reason="contract accepted without applying transition",
        previous_cycle=cycle,
        next_cycle=cycle,
        request=request,
        authorization=authorization,
        transition_record=record,
    )

    assert result.operator_attention_required is True
    assert result.execution_performed is False
    assert result.sandbox_started is False
    assert result.command_executed is False
    assert result.tool_invoked is False
    assert result.patch_created is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert gsr.cycle_transition_executes_stage(result) is False


def test_e1a_state_bundle_serializes_without_live_coupling_or_persistence():
    objective = _objective()
    cycle = gsr.make_governed_objective_cycle(objective, sequence=41)
    ledger_state = gsr.make_observation_ledger(objective.objective_id, sequence=41)
    diagnosis_state = gsr.make_diagnosis_proposal_state()
    sandbox_state = gsr.make_sandbox_planning_state()
    request = _request(cycle)
    authorization = _authorization(request)
    record = gsr.make_objective_cycle_transition_record(request, authorization)

    bundle = gsr.make_objective_cycle_state_bundle(
        cycle,
        observation_ledger_state=ledger_state,
        diagnosis_proposal_state=diagnosis_state,
        sandbox_planning_state=sandbox_state,
        transition_requests=(request,),
        transition_authorizations=(authorization,),
        transition_records=(record,),
    )
    payload = json.loads(json.dumps(gsr.serialize(bundle)))
    restored = gsr.deserialize(gsr.ObjectiveCycleStateBundle, payload)

    assert restored.cycle["cycle_id"] == cycle.cycle_id
    assert restored.observation_ledger_state["objective_id"] == objective.objective_id
    assert restored.diagnosis_proposal_state["state_version"] == diagnosis_state.state_version
    assert restored.sandbox_planning_state["state_version"] == sandbox_state.state_version
    assert restored.transition_requests[0]["request_id"] == request.request_id
    assert restored.transition_authorizations[0]["authorization_id"] == authorization.authorization_id
    assert restored.transition_records[0]["transition_id"] == record.transition_id
    assert restored.persistence_performed is False
    assert all(value is False for value in restored.safety.values())


def _eligible_review_result() -> tuple[
    gsr.GovernedObjectiveCycle,
    gsr.ObjectiveCycleTransitionRequest,
    gsr.ObjectiveCycleTransitionAuthorization,
    gsr.ObjectiveCycleTransitionEligibilityResult,
]:
    cycle = _cycle()
    request = _request(cycle)
    authorization = _authorization(request)
    result = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        authorization,
        sequence=request.requested_sequence,
    )
    return cycle, request, authorization, result


def test_e1b_valid_request_and_authorization_are_eligible_for_operator_review_only():
    cycle, request, authorization, result = _eligible_review_result()

    assert result.accepted is True
    assert result.reason == "eligible_for_operator_review"
    assert result.eligible_for_operator_review is True
    assert result.cycle.current_stage == cycle.current_stage
    assert result.cycle.current_substage == cycle.current_substage
    assert request.requested_stage != cycle.current_stage
    assert authorization.consumed is False
    assert result.transition_applied is False
    assert result.cycle_mutated is False


def test_e1b_unknown_and_forbidden_targets_fail_closed():
    cycle = _cycle()
    unknown_request = gsr.make_cycle_transition_request(
        cycle,
        requested_stage="unrecognized_stage",
        requested_substage="awaiting_review",
        required_authorization_scope=("objective_cycle_transition",),
    )
    unknown_authorization = _authorization(unknown_request)
    unknown = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        unknown_request,
        unknown_authorization,
        sequence=unknown_request.requested_sequence,
    )

    forbidden_request = gsr.make_cycle_transition_request(
        cycle,
        requested_stage="sandbox_executing",
        requested_substage="not_allowed",
        required_authorization_scope=("objective_cycle_transition",),
    )
    forbidden_authorization = _authorization(forbidden_request)
    forbidden = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        forbidden_request,
        forbidden_authorization,
        sequence=forbidden_request.requested_sequence,
    )

    assert unknown.accepted is False
    assert unknown.reason == "unknown_lifecycle_state"
    assert unknown.eligible_for_operator_review is False
    assert forbidden.accepted is False
    assert forbidden.reason == "forbidden_execution_state"
    assert forbidden.eligible_for_operator_review is False


def test_e1b_wrong_request_cycle_or_stage_is_denied():
    cycle, request, authorization, _ = _eligible_review_result()
    other_cycle = gsr.make_governed_objective_cycle(
        gsr.make_development_objective("Different objective.", sequence=99),
        sequence=99,
    )
    wrong_request_auth = replace(authorization, request_id="other-request")
    wrong_cycle_auth = replace(authorization, cycle_id=other_cycle.cycle_id)
    wrong_stage_auth = replace(authorization, allowed_from_stage="proposal_review_pending")

    wrong_request = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        wrong_request_auth,
        sequence=request.requested_sequence,
    )
    wrong_cycle = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        wrong_cycle_auth,
        sequence=request.requested_sequence,
    )
    wrong_stage = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        wrong_stage_auth,
        sequence=request.requested_sequence,
    )

    assert wrong_request.accepted is False
    assert wrong_request.reason == "wrong_request"
    assert wrong_cycle.accepted is False
    assert wrong_cycle.reason == "wrong_cycle"
    assert wrong_stage.accepted is False
    assert wrong_stage.reason == "wrong_stage"


def test_e1b_consumed_expired_and_non_operator_authorizations_are_denied():
    cycle, request, authorization, _ = _eligible_review_result()
    consumed = replace(authorization, consumed=True)
    expired = replace(authorization, expires_after_sequence=request.requested_sequence)
    non_operator = replace(authorization, operator_authority="DELTA_GENERATED")

    consumed_result = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        consumed,
        sequence=request.requested_sequence,
    )
    expired_result = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        expired,
        sequence=request.requested_sequence + 1,
    )
    non_operator_result = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        request,
        non_operator,
        sequence=request.requested_sequence,
    )

    assert consumed_result.accepted is False
    assert consumed_result.reason == "authorization_consumed"
    assert expired_result.accepted is False
    assert expired_result.reason == "authorization_expired"
    assert non_operator_result.accepted is False
    assert non_operator_result.reason == "authorization_unavailable"


def test_e1b_scope_mismatch_and_forbidden_scope_overlap_are_denied():
    cycle = _cycle()
    missing_scope_request = gsr.make_cycle_transition_request(
        cycle,
        requested_stage="diagnosis_authorization_pending",
        requested_substage="awaiting_operator_diagnosis_authorization",
        required_authorization_scope=("diagnosis_authorization",),
    )
    missing_scope_authorization = gsr.make_cycle_transition_authorization(
        missing_scope_request,
        allowed_scope=("objective_cycle_transition",),
    )
    forbidden_scope_request = gsr.make_cycle_transition_request(
        cycle,
        requested_stage="proposal_review_pending",
        requested_substage="awaiting_operator_proposal_review",
        required_authorization_scope=("source_mutation",),
    )
    forbidden_scope_authorization = gsr.make_cycle_transition_authorization(
        forbidden_scope_request,
        allowed_scope=("source_mutation",),
    )
    overlap_request = gsr.make_cycle_transition_request(
        cycle,
        requested_stage="sandbox_planning_authorization_pending",
        requested_substage="awaiting_operator_planning_authorization",
        required_authorization_scope=("objective_cycle_transition",),
        forbidden_scope=("provider_call",),
    )
    overlap_authorization = gsr.make_cycle_transition_authorization(
        overlap_request,
        allowed_scope=("objective_cycle_transition", "provider_call"),
    )

    missing = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        missing_scope_request,
        missing_scope_authorization,
        sequence=missing_scope_request.requested_sequence,
    )
    forbidden = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        forbidden_scope_request,
        forbidden_scope_authorization,
        sequence=forbidden_scope_request.requested_sequence,
    )
    overlap = gsr.evaluate_objective_cycle_transition_eligibility(
        cycle,
        overlap_request,
        overlap_authorization,
        sequence=overlap_request.requested_sequence,
    )

    assert missing.accepted is False
    assert missing.reason == "scope_mismatch_or_forbidden"
    assert forbidden.accepted is False
    assert forbidden.reason == "scope_mismatch_or_forbidden"
    assert overlap.accepted is False
    assert overlap.reason == "scope_mismatch_or_forbidden"


def test_e1b_eligibility_result_never_creates_execution_or_future_sandbox_eligibility():
    _, _, _, result = _eligible_review_result()

    assert result.execution_performed is False
    assert result.sandbox_started is False
    assert result.command_executed is False
    assert result.tool_invoked is False
    assert result.patch_created is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert "future_sandbox_execution_eligible" not in result.cycle.completed_stage_markers
    assert all(value is False for value in result.safety.values())


def _applied_transition() -> tuple[
    gsr.GovernedObjectiveCycle,
    gsr.ObjectiveCycleTransitionRequest,
    gsr.ObjectiveCycleTransitionAuthorization,
    gsr.ObjectiveCycleTransitionResult,
]:
    cycle = _cycle()
    request = _request(cycle)
    authorization = _authorization(request)
    result = gsr.apply_objective_cycle_transition(
        cycle,
        request,
        authorization,
        sequence=request.requested_sequence,
    )
    return cycle, request, authorization, result


def test_e1c_valid_transition_applies_exactly_one_metadata_update():
    cycle, request, authorization, result = _applied_transition()

    assert result.accepted is True
    assert result.reason == "metadata_transition_applied"
    assert result.transition_applied is True
    assert result.cycle_mutated is False
    assert result.replacement_cycle_produced is True
    assert result.previous_cycle is cycle
    assert result.next_cycle is not cycle
    assert cycle.current_stage == "objective_authorized"
    assert cycle.current_substage == "awaiting_transition_request"
    assert result.next_cycle.current_stage == request.requested_stage
    assert result.next_cycle.current_substage == request.requested_substage
    assert result.next_cycle.cycle_id == cycle.cycle_id
    assert result.next_cycle.last_successful_transition == result.transition_record.transition_id
    assert request.from_stage in result.next_cycle.completed_stage_markers
    assert authorization.authorization_id in result.next_cycle.consumed_transition_authorization_ids


def test_e1c_consumes_exactly_one_authorization_and_preserves_original_value():
    _, _, authorization, result = _applied_transition()

    assert authorization.consumed is False
    assert result.authorization is authorization
    assert result.consumed_authorization is not authorization
    assert result.consumed_authorization.authorization_id == authorization.authorization_id
    assert result.consumed_authorization.consumed is True
    assert result.authorization_consumed is True
    assert result.record_created is True


def test_e1c_creates_exactly_one_inert_transition_record():
    cycle, request, authorization, result = _applied_transition()
    record = result.transition_record

    assert record is not None
    assert record.cycle_id == cycle.cycle_id
    assert record.request_id == request.request_id
    assert record.authorization_id == authorization.authorization_id
    assert record.from_stage == cycle.current_stage
    assert record.to_stage == request.requested_stage
    assert record.from_substage == cycle.current_substage
    assert record.to_substage == request.requested_substage
    assert record.result == "metadata_transition_applied"
    assert record.operator_controlled is True
    assert record.execution_performed is False
    assert record.automatic_continuation is False


def test_e1c_stops_after_one_transition_without_next_request_or_continuation():
    _, request, _, result = _applied_transition()

    assert request.request_id not in result.next_cycle.pending_transition_request_ids
    assert result.automatic_continuation is False
    assert result.operator_attention_required is True
    assert result.next_cycle.operator_attention_required is True
    assert gsr.cycle_can_continue_automatically(result.next_cycle) is False
    assert result.next_cycle.autonomous_continuation_prohibited is True
    assert result.next_cycle.background_execution_prohibited is True
    assert result.next_cycle.persistence_prohibited is True


def test_e1c_reusing_consumed_authorization_is_denied_without_second_transition():
    _, request, _, result = _applied_transition()
    reused = gsr.apply_objective_cycle_transition(
        result.next_cycle,
        request,
        result.consumed_authorization,
        sequence=request.requested_sequence + 1,
    )

    assert reused.accepted is False
    assert reused.reason in {"wrong_stage", "authorization_consumed"}
    assert reused.next_cycle == result.next_cycle
    assert reused.consumed_authorization is None
    assert reused.transition_record is None
    assert reused.transition_applied is False
    assert reused.authorization_consumed is False
    assert reused.record_created is False


def test_e1c_failed_transition_does_not_consume_update_or_record():
    cycle = _cycle()
    request = gsr.make_cycle_transition_request(
        cycle,
        requested_stage="unknown_stage",
        requested_substage="unknown",
        required_authorization_scope=("objective_cycle_transition",),
    )
    authorization = _authorization(request)
    result = gsr.apply_objective_cycle_transition(
        cycle,
        request,
        authorization,
        sequence=request.requested_sequence,
    )

    assert result.accepted is False
    assert result.reason == "unknown_lifecycle_state"
    assert result.previous_cycle is cycle
    assert result.next_cycle is cycle
    assert authorization.consumed is False
    assert result.consumed_authorization is None
    assert result.transition_record is None
    assert result.transition_applied is False
    assert result.authorization_consumed is False
    assert result.record_created is False


def test_e1c_denies_forbidden_execution_target_without_actions():
    cycle = _cycle()
    request = gsr.make_cycle_transition_request(
        cycle,
        requested_stage="sandbox_executing",
        requested_substage="forbidden",
        required_authorization_scope=("objective_cycle_transition",),
    )
    authorization = _authorization(request)
    result = gsr.apply_objective_cycle_transition(
        cycle,
        request,
        authorization,
        sequence=request.requested_sequence,
    )

    assert result.accepted is False
    assert result.reason == "forbidden_execution_state"
    assert result.next_cycle is cycle
    assert result.consumed_authorization is None
    assert result.transition_record is None
    assert result.execution_performed is False


def test_e1c_denies_request_cycle_stage_authorization_expiration_and_scope_mismatches():
    cycle, request, authorization, _ = _eligible_review_result()
    wrong_request = replace(authorization, request_id="other-request")
    wrong_cycle = replace(authorization, cycle_id="other-cycle")
    wrong_stage = replace(authorization, allowed_from_stage="diagnosis_review_pending")
    wrong_target = replace(authorization, allowed_to_stage="proposal_review_pending")
    expired = replace(authorization, expires_after_sequence=request.requested_sequence)
    non_operator = replace(authorization, operator_authority="DELTA_GENERATED")
    missing_scope = replace(authorization, allowed_scope=("proposal_review",))
    cases = (
        (wrong_request, "wrong_request", request.requested_sequence),
        (wrong_cycle, "wrong_cycle", request.requested_sequence),
        (wrong_stage, "wrong_stage", request.requested_sequence),
        (wrong_target, "authorization_mismatch", request.requested_sequence),
        (expired, "authorization_expired", request.requested_sequence + 1),
        (non_operator, "authorization_unavailable", request.requested_sequence),
        (missing_scope, "scope_mismatch_or_forbidden", request.requested_sequence),
    )

    for auth, reason, sequence in cases:
        result = gsr.apply_objective_cycle_transition(cycle, request, auth, sequence=sequence)
        assert result.accepted is False
        assert result.reason == reason
        assert result.next_cycle is cycle
        assert result.consumed_authorization is None
        assert result.transition_record is None
        assert result.transition_applied is False
        assert result.authorization_consumed is False


def test_e1c_transition_application_has_no_execution_or_future_sandbox_side_effects():
    _, _, _, result = _applied_transition()

    assert result.execution_performed is False
    assert result.sandbox_started is False
    assert result.command_executed is False
    assert result.tool_invoked is False
    assert result.patch_created is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.next_cycle.current_stage != "future_sandbox_execution_eligible"
    assert "future_sandbox_execution_eligible" not in result.next_cycle.completed_stage_markers


E2_PROPOSAL_ID = "proposal-ready-for-e2-sandbox-execution"


def _e2_cycle() -> gsr.GovernedObjectiveCycle:
    objective = gsr.make_development_objective(
        "Review one future sandbox execution attempt.",
        scope=("sandbox_execution_authorization",),
        success_criteria=("future_execution_eligibility_reviewed",),
        sequence=80,
    )
    return gsr.make_governed_objective_cycle(
        objective,
        current_stage="future_sandbox_execution_eligible",
        current_substage="awaiting_operator_execution_authorization",
        sequence=81,
    )


def _e2_budget(**overrides) -> dict[str, int]:
    budget = {
        "max_commands": 1,
        "max_tool_calls": 1,
        "max_elapsed_units": 10,
        "max_output_bytes": 4096,
        "max_artifact_count": 2,
        "max_workspace_writes": 1,
        "max_processes": 1,
        "max_retries": 1,
    }
    budget.update(overrides)
    return budget


def _e2_workspace_policy(*extra: str) -> tuple[str, ...]:
    return (
        "disposable_workspace_required",
        "cleanup_required",
        "cleanup_verification_required",
        "no_production_path_access",
        "no_credential_access",
        "no_home_directory_access",
        "no_external_drive_access",
        "no_environment_secret_inheritance",
        *extra,
    )


def _e2_plan_result(**overrides) -> gsr.SandboxPlanCreationResult:
    proposal_state = gsr.DiagnosisProposalState(
        state_version="GSR-C-1",
        future_sandbox_planning_eligible_proposals=(E2_PROPOSAL_ID,),
    )
    planning_state = gsr.make_sandbox_planning_state()
    planning_authorization = gsr.make_sandbox_planning_authorization(
        E2_PROPOSAL_ID,
        allowed_planning_scope=("sandbox_plan_drafting",),
        decision_sequence=80,
    )
    authorized = gsr.authorize_sandbox_plan_creation(
        proposal_state,
        planning_state,
        planning_authorization,
        proposal_id=E2_PROPOSAL_ID,
        sequence=80,
    )
    assert authorized.accepted is True
    payload = {
        "proposal_id": E2_PROPOSAL_ID,
        "disposable_workspace_description": "disposable workspace metadata only",
        "repository_snapshot_description": "read-only repository snapshot metadata",
        "files_or_components_in_scope": ("orchestration/runtime/example.py",),
        "forbidden_files_or_components": ("DELTA-75", "production"),
        "allowed_tool_classes": ("read_only_inspection",),
        "forbidden_tool_classes": ("command_execution", "patch_generation", "source_mutation"),
        "allowed_command_categories": ("focused_test_runner",),
        "forbidden_command_categories": ("shell_command", "git_operation"),
        "test_selection": ("tests/runtime_gsr/test_gsr_e_objective_cycle.py",),
        "focused_test_requirements": ("E2-A inert eligibility",),
        "adjacent_test_requirements": ("GSR-D regression",),
        "live_runtime_evidence_requirements": ("none",),
        "provider_model_restrictions": ("provider calls prohibited", "model inference prohibited"),
        "network_restrictions": ("network access prohibited",),
        "memory_write_restrictions": ("memory writes prohibited",),
        "source_mutation_restrictions": ("source mutation prohibited",),
        "success_criteria": ("eligibility metadata only",),
        "failure_criteria": ("any execution flag true",),
        "rollback_proof_requirements": ("discard inert metadata",),
        "cleanup_proof_requirements": ("cleanup verification metadata required",),
        "artifact_retention_policy": "disposable evidence artifacts only",
        "execution_budget_metadata": ("bounded execution metadata only",),
        "creation_sequence": 81,
    }
    payload.update(overrides)
    result = gsr.create_inert_sandbox_plan(
        proposal_state,
        authorized.state,
        planning_authorization,
        **payload,
    )
    assert result.accepted is True
    assert result.sandbox_plan is not None
    return result


def _e2_reviewed_plan(**overrides) -> tuple[gsr.SandboxPlanningState, gsr.SandboxEvaluationPlan]:
    plan_result = _e2_plan_result(**overrides)
    assert plan_result.sandbox_plan is not None
    decision = gsr.make_sandbox_plan_review_decision(
        plan_result.sandbox_plan.plan_id,
        disposition="approve_for_future_sandbox_execution",
        rationale="operator approves future execution eligibility review only",
        allowed_execution_scope=("future_disposable_sandbox_execution_attempt",),
        forbidden_execution_scope=("source_mutation", "production_application"),
        allowed_tool_classes=("read_only_inspection",),
        forbidden_tool_classes=("command_execution", "patch_generation"),
        allowed_command_categories=("focused_test_runner",),
        forbidden_command_categories=("shell_command", "git_operation"),
        decision_sequence=82,
    )
    reviewed = gsr.review_sandbox_plan(plan_result.state, decision, sequence=82)
    assert reviewed.accepted is True
    assert reviewed.future_sandbox_execution_eligible is True
    assert reviewed.plan is not None
    return reviewed.state, reviewed.plan


def _e2_request(
    cycle: gsr.GovernedObjectiveCycle | None = None,
    plan: gsr.SandboxEvaluationPlan | None = None,
    **overrides,
) -> gsr.SandboxExecutionRequest:
    cycle = cycle or _e2_cycle()
    if plan is None:
        _, plan = _e2_reviewed_plan()
    payload = {
        "requested_scope": ("future_disposable_sandbox_execution_attempt",),
        "requested_workspace_policy": _e2_workspace_policy(),
        "requested_tool_allowlist": ("read_only_inspection",),
        "requested_command_allowlist": ("focused_test_runner",),
        "requested_network_policy": ("no_network",),
        "requested_execution_budget": _e2_budget(),
        "requested_artifact_output_policy": ("disposable_evidence_artifacts",),
        "requested_execution_sequence": 83,
    }
    payload.update(overrides)
    return gsr.make_sandbox_execution_request(cycle, plan, **payload)


def _e2_authorization(
    request: gsr.SandboxExecutionRequest,
    **overrides,
) -> gsr.SandboxExecutionAuthorization:
    payload = {
        "authorized_scope": ("future_disposable_sandbox_execution_attempt",),
        "authorized_workspace_policy": _e2_workspace_policy(),
        "authorized_tool_allowlist": ("read_only_inspection",),
        "authorized_command_allowlist": ("focused_test_runner",),
        "authorized_network_policy": ("no_network",),
        "authorized_execution_budget": _e2_budget(),
        "authorized_artifact_output_policy": ("disposable_evidence_artifacts",),
        "expires_after_sequence": request.requested_execution_sequence + 5,
    }
    payload.update(overrides)
    return gsr.make_sandbox_execution_authorization(request, **payload)


def _e2_result(**request_overrides) -> tuple[
    gsr.GovernedObjectiveCycle,
    gsr.SandboxPlanningState,
    gsr.SandboxEvaluationPlan,
    gsr.SandboxExecutionRequest,
    gsr.SandboxExecutionAuthorization,
    gsr.SandboxExecutionEligibilityResult,
]:
    cycle = _e2_cycle()
    state, plan = _e2_reviewed_plan()
    request = _e2_request(cycle, plan, **request_overrides)
    authorization = _e2_authorization(request)
    result = gsr.evaluate_sandbox_execution_eligibility(
        cycle,
        state,
        plan,
        request,
        authorization,
        sequence=request.requested_execution_sequence,
    )
    return cycle, state, plan, request, authorization, result


def test_e2a_exact_cycle_plan_request_and_authorization_become_future_execution_eligible_only():
    cycle, _, plan, request, authorization, result = _e2_result()

    assert result.accepted is True
    assert result.reason == "eligible_for_future_sandbox_execution"
    assert result.eligible_for_future_sandbox_execution is True
    assert result.cycle is cycle
    assert result.sandbox_plan is plan
    assert result.request is request
    assert result.authorization is authorization
    assert authorization.consumed is False
    assert result.authorization_consumed is False
    assert result.cycle_mutated is False
    assert result.plan_mutated is False


def test_e2a_eligibility_does_not_execute_or_create_any_operational_side_effect():
    *_, result = _e2_result()

    assert result.execution_performed is False
    assert result.execution_started is False
    assert result.workspace_created is False
    assert result.sandbox_started is False
    assert result.command_executed is False
    assert result.tool_invoked is False
    assert result.network_accessed is False
    assert result.patch_created is False
    assert result.patch_applied is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert all(value is False for value in result.safety.values())


def test_e2a_wrong_identity_version_digest_request_cycle_and_stage_fail_closed():
    cycle, state, plan, request, authorization, _ = _e2_result()
    wrong_cycle = replace(authorization, cycle_id="other-cycle")
    wrong_plan = replace(authorization, sandbox_plan_id="other-plan")
    wrong_version = replace(authorization, sandbox_plan_version="other-version")
    wrong_digest = replace(authorization, sandbox_plan_digest="other-digest")
    wrong_request = replace(authorization, request_id="other-request")
    wrong_stage = replace(authorization, authorized_source_lifecycle_stage="proposal_review_pending")

    cases = (
        (cycle, request, wrong_cycle, "wrong_cycle"),
        (cycle, request, wrong_plan, "wrong_plan"),
        (cycle, request, wrong_version, "wrong_plan_version"),
        (cycle, request, wrong_digest, "wrong_plan_digest"),
        (cycle, request, wrong_request, "wrong_request"),
        (cycle, request, wrong_stage, "wrong_stage"),
    )
    for test_cycle, test_request, test_authorization, reason in cases:
        result = gsr.evaluate_sandbox_execution_eligibility(
            test_cycle,
            state,
            plan,
            test_request,
            test_authorization,
            sequence=request.requested_execution_sequence,
        )
        assert result.accepted is False
        assert result.reason == reason
        assert result.eligible_for_future_sandbox_execution is False
        assert result.authorization_consumed is False


def test_e2a_non_operator_consumed_and_expired_authorizations_fail_closed():
    cycle, state, plan, request, authorization, _ = _e2_result()
    cases = (
        (replace(authorization, operator_authority="DELTA_GENERATED"), "non_operator_authorization", request.requested_execution_sequence),
        (replace(authorization, consumed=True), "consumed", request.requested_execution_sequence),
        (replace(authorization, expires_after_sequence=request.requested_execution_sequence), "expired", request.requested_execution_sequence + 1),
    )
    for test_authorization, reason, sequence in cases:
        result = gsr.evaluate_sandbox_execution_eligibility(
            cycle,
            state,
            plan,
            request,
            test_authorization,
            sequence=sequence,
        )
        assert result.accepted is False
        assert result.reason == reason
        assert test_authorization.consumed is (reason == "consumed")


def test_e2a_scope_budget_and_policy_mismatches_fail_closed():
    cycle, state, plan, request, authorization, _ = _e2_result()
    broader_scope_request = replace(request, requested_scope=("future_disposable_sandbox_execution_attempt", "extra_scope"))
    broader_tool_request = replace(request, requested_tool_allowlist=("read_only_inspection", "extra_tool"))
    broader_command_request = replace(request, requested_command_allowlist=("focused_test_runner", "extra_command"))
    broader_network_request = replace(request, requested_network_policy=("no_network", "limited_network"))
    broader_budget_request = replace(request, requested_execution_budget={**request.requested_execution_budget, "max_commands": 2})
    missing_workspace_request = replace(request, requested_workspace_policy=("cleanup_required",))

    cases = (
        (broader_scope_request, authorization, "scope_mismatch"),
        (broader_tool_request, authorization, "tool_policy_mismatch"),
        (broader_command_request, authorization, "command_policy_mismatch"),
        (broader_network_request, authorization, "network_policy_mismatch"),
        (broader_budget_request, authorization, "budget_mismatch"),
        (missing_workspace_request, authorization, "workspace_policy_mismatch"),
    )
    for test_request, test_authorization, reason in cases:
        result = gsr.evaluate_sandbox_execution_eligibility(
            cycle,
            state,
            plan,
            test_request,
            test_authorization,
            sequence=request.requested_execution_sequence,
        )
        assert result.accepted is False
        assert result.reason == reason


def test_e2a_unrestricted_tool_command_and_network_policies_fail_closed():
    cycle, state, plan, request, _, _ = _e2_result()
    cases = (
        (
            replace(request, requested_tool_allowlist=("unrestricted",)),
            _e2_authorization(replace(request, requested_tool_allowlist=("unrestricted",)), authorized_tool_allowlist=("unrestricted",)),
        ),
        (
            replace(request, requested_command_allowlist=("*",)),
            _e2_authorization(replace(request, requested_command_allowlist=("*",)), authorized_command_allowlist=("*",)),
        ),
        (
            replace(request, requested_network_policy=("ambient",)),
            _e2_authorization(replace(request, requested_network_policy=("ambient",)), authorized_network_policy=("ambient",)),
        ),
    )
    for test_request, test_authorization in cases:
        result = gsr.evaluate_sandbox_execution_eligibility(
            cycle,
            state,
            plan,
            test_request,
            test_authorization,
            sequence=request.requested_execution_sequence,
        )
        assert result.accepted is False
        assert result.reason == "unrestricted_policy"


def test_e2a_forbidden_operational_scopes_fail_closed():
    cycle, state, plan, request, authorization, _ = _e2_result()
    forbidden_scopes = (
        "live_source_mutation",
        "patch_application",
        "git_stage",
        "git_commit",
        "git_push",
        "merge",
        "deployment",
        "publication",
        "production_application",
        "module_activation",
        "registry_mutation",
        "canonical_memory_write",
        "provider_call",
        "model_inference",
        "scheduler",
        "thread",
        "background_loop",
        "autonomous_retry",
        "recursive_objective_continuation",
        "additional_execution_attempt",
        "unrestricted_filesystem",
        "unrestricted_network",
        "credential_access",
        "DELTA-75",
    )
    for forbidden in forbidden_scopes:
        test_request = replace(request, requested_scope=(forbidden,))
        test_authorization = replace(authorization, authorized_scope=(forbidden,))
        result = gsr.evaluate_sandbox_execution_eligibility(
            cycle,
            state,
            plan,
            test_request,
            test_authorization,
            sequence=request.requested_execution_sequence,
        )
        assert result.accepted is False
        assert result.reason == "scope_mismatch"


def test_e2a_plan_must_be_future_execution_eligible_complete_and_inert():
    cycle = _e2_cycle()
    plan_result = _e2_plan_result()
    assert plan_result.sandbox_plan is not None
    request = _e2_request(cycle, plan_result.sandbox_plan)
    authorization = _e2_authorization(request)
    not_eligible = gsr.evaluate_sandbox_execution_eligibility(
        cycle,
        plan_result.state,
        plan_result.sandbox_plan,
        request,
        authorization,
        sequence=request.requested_execution_sequence,
    )
    operational_plan = replace(plan_result.sandbox_plan, source_mutation_prohibited=False)
    operational_state = gsr.SandboxPlanningState(
        **{
            **gsr.serialize(plan_result.state),
            "sandbox_plans": (gsr.serialize(operational_plan),),
            "future_sandbox_execution_eligible_plans": (operational_plan.plan_id,),
        }
    )
    operational = gsr.evaluate_sandbox_execution_eligibility(
        cycle,
        operational_state,
        operational_plan,
        _e2_request(cycle, operational_plan),
        _e2_authorization(_e2_request(cycle, operational_plan)),
        sequence=request.requested_execution_sequence,
    )

    assert not_eligible.accepted is False
    assert not_eligible.reason == "plan_not_future_execution_eligible"
    assert operational.accepted is False
    assert operational.reason == "plan_authorizes_operation"


def _e2b_tuple(**request_overrides) -> tuple[
    gsr.GovernedObjectiveCycle,
    gsr.SandboxPlanningState,
    gsr.SandboxEvaluationPlan,
    gsr.SandboxExecutionRequest,
    gsr.SandboxExecutionAuthorization,
]:
    cycle = _e2_cycle()
    state, plan = _e2_reviewed_plan(allowed_command_categories=("python_compile",))
    command_name = request_overrides.pop("command_name", "static_scan")
    payload = {
        "requested_command_allowlist": (command_name,),
        "requested_tool_allowlist": ("compiler",),
        "requested_execution_budget": _e2_budget(max_workspace_writes=1, max_artifact_count=1),
    }
    payload.update(request_overrides)
    request = _e2_request(cycle, plan, **payload)
    authorization = _e2_authorization(
        request,
        authorized_command_allowlist=(command_name,),
        authorized_tool_allowlist=("compiler",),
        authorized_execution_budget=_e2_budget(max_workspace_writes=1, max_artifact_count=1),
    )
    return cycle, state, plan, request, authorization


def _e2b_success_result():
    cycle, state, plan, request, authorization = _e2b_tuple()
    result = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="static_scan",
        command_arguments=(),
        fixture_files={"fixture.py": "x = 1\n"},
        sequence=request.requested_execution_sequence,
    )
    return cycle, state, plan, request, authorization, result


def test_e2b_valid_tuple_performs_one_disposable_attempt_and_cleans_workspace():
    _, _, _, request, authorization, result = _e2b_success_result()

    assert result.accepted is True
    assert result.reason == "sandbox_attempt_succeeded"
    assert result.execution_performed is True
    assert result.execution_succeeded is True
    assert result.authorization_consumed is True
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.attempt is not None
    assert result.attempt.attempt_started is True
    assert result.attempt.attempt_completed is True
    assert result.attempt.authorization_consumed is True
    assert result.attempt.cleanup_verified is True
    assert result.cleanup_verified is True
    assert result.evidence.return_code == 0
    assert result.evidence.command_name == "static_scan"
    assert result.evidence.normalized_arguments == ()
    assert result.evidence.budget_observed["command_count"] == 1
    assert result.evidence.budget_observed["retry_count"] == 0
    assert result.evidence.artifact_manifest == ("fixture.py",)
    assert result.evidence.filesystem_write_manifest == ("fixture.py",)
    assert result.evidence.cleanup_result == "verified"
    assert result.evidence.execution_performed is True
    assert result.second_attempt_created is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False
    assert not Path(result.attempt.workspace_root).exists()
    assert not Path(result.attempt.workspace_root).is_relative_to(Path("G:/Delta_Dev").resolve())
    assert request.request_consumed is False


def test_e2b_disposable_workspace_excludes_git_secrets_delta75_and_unrelated_files():
    _, _, _, _, _, result = _e2b_success_result()

    manifest = set(result.evidence.filesystem_write_manifest)
    assert manifest == {"fixture.py"}
    assert ".git" not in manifest
    assert ".env" not in manifest
    assert "secrets" not in manifest
    assert "credentials" not in manifest
    assert "DELTA-75" not in manifest
    assert result.live_source_unchanged is True


def test_e2b_preflight_denial_does_not_consume_authorization_or_create_attempt():
    cycle, state, plan, request, authorization = _e2b_tuple(command_name="python_compile")
    result = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="curl",
        command_arguments=("https://example.com",),
        fixture_files={"fixture.py": "x = 1\n"},
        sequence=request.requested_execution_sequence,
    )

    assert result.accepted is False
    assert result.reason == "command_not_authorized"
    assert result.authorization_consumed is False
    assert result.consumed_authorization is None
    assert result.attempt is None
    assert result.evidence is None
    assert authorization.consumed is False


def test_e2b_command_failure_after_start_consumes_authorization_and_stops():
    cycle, state, plan, request, authorization = _e2b_tuple(command_name="python_compile")
    result = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="python_compile",
        command_arguments=("fixture.py",),
        fixture_files={"fixture.py": "def broken(:\n"},
        sequence=request.requested_execution_sequence,
    )

    assert result.accepted is False
    assert result.reason == "command_failed"
    assert result.execution_performed is True
    assert result.execution_succeeded is False
    assert result.authorization_consumed is True
    assert result.consumed_authorization.consumed is True
    assert result.evidence.return_code != 0
    assert result.evidence.stderr_summary
    assert result.cleanup_verified is True
    assert result.second_attempt_created is False
    assert result.automatic_continuation is False


def test_e2b_consumed_authorization_cannot_be_reused_for_second_attempt():
    cycle, state, plan, request, authorization = _e2b_tuple(command_name="python_compile")
    first = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="python_compile",
        command_arguments=("fixture.py",),
        fixture_files={"fixture.py": "x = 1\n"},
        sequence=request.requested_execution_sequence,
    )
    second = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        first.consumed_authorization,
        command_name="python_compile",
        command_arguments=("fixture.py",),
        fixture_files={"fixture.py": "x = 2\n"},
        sequence=request.requested_execution_sequence + 1,
    )

    assert second.accepted is False
    assert second.reason == "consumed"
    assert second.execution_performed is False
    assert second.authorization_consumed is False
    assert second.attempt is None
    assert second.evidence is None


def test_e2b_path_traversal_and_external_writes_fail_closed_before_execution():
    cycle, state, plan, request, authorization = _e2b_tuple(command_name="python_compile")
    result = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="python_compile",
        command_arguments=("..\\escape.py",),
        fixture_files={"fixture.py": "x = 1\n"},
        sequence=request.requested_execution_sequence,
    )
    outside = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="python_compile",
        command_arguments=("fixture.py",),
        fixture_files={"../escape.py": "x = 1\n"},
        sequence=request.requested_execution_sequence,
    )

    assert result.accepted is False
    assert result.reason == "path_traversal_or_forbidden_argument"
    assert outside.accepted is False
    assert outside.reason == "path_traversal_or_forbidden_fixture"
    assert result.authorization_consumed is False
    assert outside.authorization_consumed is False


def test_e2b_budget_and_output_bounds_are_enforced_or_recorded():
    cycle, state, plan, request, authorization = _e2b_tuple(command_name="python_compile", requested_execution_budget=_e2_budget(max_workspace_writes=1, max_artifact_count=1, max_output_bytes=8))
    too_many_files = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="python_compile",
        command_arguments=("fixture.py",),
        fixture_files={"fixture.py": "x = 1\n", "other.py": "y = 2\n"},
        sequence=request.requested_execution_sequence,
    )
    noisy = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="python_compile",
        command_arguments=("fixture.py",),
        fixture_files={"fixture.py": "def broken(:\n"},
        sequence=request.requested_execution_sequence,
    )

    assert too_many_files.accepted is False
    assert too_many_files.reason == "workspace_write_budget_exceeded"
    assert too_many_files.authorization_consumed is False
    assert noisy.execution_performed is True
    assert noisy.evidence.output_truncated is True


def test_e2b_cleanup_failure_requires_operator_review_without_retry(monkeypatch):
    cycle, state, plan, request, authorization = _e2b_tuple()
    original_rmtree = py_shutil.rmtree

    def fail_cleanup(_path):
        raise OSError("cleanup blocked")

    monkeypatch.setattr(gsr.shutil, "rmtree", fail_cleanup)
    result = gsr.execute_disposable_sandbox_attempt(
        cycle,
        state,
        plan,
        request,
        authorization,
        command_name="static_scan",
        command_arguments=(),
        fixture_files={"fixture.py": "x = 1\n"},
        sequence=request.requested_execution_sequence,
    )

    assert result.accepted is False
    assert result.reason == "cleanup_failed"
    assert result.authorization_consumed is True
    assert result.cleanup_verified is False
    assert result.attempt.operator_review_required is True
    assert result.second_attempt_created is False
    assert result.automatic_continuation is False
    original_rmtree(Path(result.attempt.workspace_root).parent, ignore_errors=True)


def test_e2b_no_provider_model_memory_persistence_module_or_application_actions():
    _, _, _, _, _, result = _e2b_success_result()

    assert result.patch_applied is False
    assert result.source_mutated is False
    assert result.module_activated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert all(value is False for value in result.safety.values())


def _e3_constructed_result(
    *,
    return_code: int = 0,
    accepted: bool = True,
    reason: str = "sandbox_attempt_succeeded",
    cleanup_verified: bool = True,
    live_source_unchanged: bool = True,
    output_truncated: bool = False,
    budget_observed: dict[str, int] | None = None,
    artifact_manifest: tuple[str, ...] = ("fixture.py",),
    filesystem_write_manifest: tuple[str, ...] = ("fixture.py",),
    execution_performed: bool = True,
    authorization_consumed: bool = True,
    attempt_started: bool = True,
    second_attempt_created: bool = False,
    automatic_continuation: bool = False,
    provider_called: bool = False,
    model_invoked: bool = False,
    memory_written: bool = False,
    persistence_performed: bool = False,
    module_activated: bool = False,
    application_authorized: bool = False,
    application_performed: bool = False,
) -> gsr.SandboxExecutionResult:
    cycle, state, plan, request, authorization = _e2b_tuple(command_name="static_scan")
    _ = state
    consumed = replace(authorization, consumed=True) if authorization_consumed else authorization
    attempt = None
    evidence = None
    if attempt_started:
        attempt_id = "attempt-fixture"
        attempt = gsr.SandboxExecutionAttempt(
            attempt_id=attempt_id,
            cycle_id=cycle.cycle_id,
            sandbox_plan_id=plan.plan_id,
            request_id=request.request_id,
            authorization_id=consumed.authorization_id,
            execution_sequence=request.requested_execution_sequence,
            workspace_policy=request.requested_workspace_policy,
            command_name="static_scan",
            normalized_arguments=(),
            execution_budget=request.requested_execution_budget,
            workspace_root="C:/Temp/fixture-workspace",
            attempt_started=attempt_started,
            attempt_completed=execution_performed,
            authorization_consumed=authorization_consumed,
            cleanup_verified=cleanup_verified,
            live_source_unchanged=live_source_unchanged,
        )
        if execution_performed:
            evidence = gsr.SandboxExecutionEvidence(
                attempt_id=attempt_id,
                command_name="static_scan",
                normalized_arguments=(),
                start_sequence=request.requested_execution_sequence,
                end_sequence=request.requested_execution_sequence,
                return_code=return_code,
                stdout_summary="ok" if return_code == 0 else "",
                stderr_summary="" if return_code == 0 else "failure",
                output_truncated=output_truncated,
                artifact_manifest=artifact_manifest,
                filesystem_write_manifest=filesystem_write_manifest,
                budget_observed=budget_observed or {
                    "command_count": 1,
                    "tool_call_count": 0,
                    "process_count": 1,
                    "artifact_count": len(artifact_manifest),
                    "workspace_write_count": len(filesystem_write_manifest),
                    "retry_count": 0,
                    "duration_ms": 1,
                },
                cleanup_result="verified" if cleanup_verified else "cleanup_failed:OSError",
                live_source_integrity_status="unchanged" if live_source_unchanged else "changed",
                execution_performed=True,
            )
    return gsr.SandboxExecutionResult(
        accepted=accepted,
        reason=reason,
        cycle=cycle,
        sandbox_plan=plan,
        request=request,
        original_authorization=authorization,
        consumed_authorization=consumed if authorization_consumed else None,
        attempt=attempt,
        evidence=evidence,
        eligible_for_operator_review=True,
        execution_performed=execution_performed,
        execution_succeeded=accepted,
        cleanup_verified=cleanup_verified,
        live_source_unchanged=live_source_unchanged,
        authorization_consumed=authorization_consumed,
        second_attempt_created=second_attempt_created,
        automatic_continuation=automatic_continuation,
        provider_called=provider_called,
        model_invoked=model_invoked,
        memory_written=memory_written,
        persistence_performed=persistence_performed,
        module_activated=module_activated,
        application_authorized=application_authorized,
        application_performed=application_performed,
    )


def _finding_codes(evaluation: gsr.SandboxEvidenceEvaluation) -> set[str]:
    return {finding.code for finding in evaluation.findings}


def test_e3a_successful_and_failed_complete_evidence_are_reviewable_without_application_authority():
    success = gsr.evaluate_sandbox_execution_evidence(_e3_constructed_result())
    failed = gsr.evaluate_sandbox_execution_evidence(
        _e3_constructed_result(return_code=1, accepted=False, reason="command_failed")
    )

    assert success.accepted_for_operator_review is True
    assert success.classification == "execution_succeeded"
    assert failed.accepted_for_operator_review is True
    assert failed.classification == "execution_failed"
    assert failed.command_failed is True
    for evaluation in (success, failed):
        assert evaluation.application_authorized is False
        assert evaluation.application_performed is False
        assert evaluation.next_attempt_authorized is False
        assert evaluation.automatic_continuation is False
        assert evaluation.execution_authorization_created is False
        assert evaluation.lifecycle_transition_applied is False
        assert evaluation.next_request_created is False
        assert evaluation.authorization_consumed is False


def test_e3a_preflight_denial_is_classified_without_requiring_command_evidence():
    result = _e3_constructed_result(
        accepted=False,
        reason="command_not_authorized",
        execution_performed=False,
        authorization_consumed=False,
        attempt_started=False,
    )
    evaluation = gsr.evaluate_sandbox_execution_evidence(result)

    assert evaluation.classification == "preflight_denied"
    assert "preflight_denied" in _finding_codes(evaluation)
    assert evaluation.accepted_for_operator_review is True


def test_e3a_missing_identity_and_digest_mismatches_fail_closed():
    result = _e3_constructed_result()
    wrong_attempt = replace(result, evidence=replace(result.evidence, attempt_id="wrong-attempt"))
    wrong_cycle = replace(result, attempt=replace(result.attempt, cycle_id="wrong-cycle"))
    wrong_plan = replace(result, attempt=replace(result.attempt, sandbox_plan_id="wrong-plan"))
    wrong_request = replace(result, attempt=replace(result.attempt, request_id="wrong-request"))
    wrong_auth = replace(result, attempt=replace(result.attempt, authorization_id="wrong-auth"))
    digest_mismatch = gsr.evaluate_sandbox_execution_evidence(result, expected_evidence_digest="not-the-digest")

    cases = (
        (wrong_attempt, "wrong_attempt"),
        (wrong_cycle, "wrong_cycle"),
        (wrong_plan, "wrong_plan"),
        (wrong_request, "wrong_request"),
        (wrong_auth, "wrong_authorization"),
    )
    for bad_result, code in cases:
        evaluation = gsr.evaluate_sandbox_execution_evidence(bad_result)
        assert evaluation.accepted_for_operator_review is False
        assert code in _finding_codes(evaluation)
    assert digest_mismatch.accepted_for_operator_review is False
    assert "evidence_digest_mismatch" in _finding_codes(digest_mismatch)


def test_e3a_inconsistent_evidence_fails_closed():
    result = _e3_constructed_result()
    contradictions = (
        replace(result, attempt=replace(result.attempt, authorization_consumed=False)),
        replace(result, evidence=replace(result.evidence, execution_performed=False)),
        replace(result, execution_succeeded=False, accepted=True),
    )

    for bad_result in contradictions:
        evaluation = gsr.evaluate_sandbox_execution_evidence(bad_result)
        assert evaluation.accepted_for_operator_review is False
        assert "evidence_inconsistent" in _finding_codes(evaluation)


def test_e3a_cleanup_and_live_source_integrity_failures_block_acceptance():
    cleanup = gsr.evaluate_sandbox_execution_evidence(
        _e3_constructed_result(accepted=False, reason="cleanup_failed", cleanup_verified=False)
    )
    integrity = gsr.evaluate_sandbox_execution_evidence(
        _e3_constructed_result(accepted=False, reason="live_source_integrity_failed", live_source_unchanged=False)
    )

    assert cleanup.classification == "cleanup_failed"
    assert cleanup.accepted_for_operator_review is False
    assert "cleanup_failed" in _finding_codes(cleanup)
    assert integrity.classification == "live_source_integrity_failed"
    assert integrity.accepted_for_operator_review is False
    assert "live_source_integrity_failed" in _finding_codes(integrity)
    assert any(finding.requires_deeper_design for finding in integrity.findings)


def test_e3a_budget_output_artifact_and_write_findings_are_reported():
    budget = gsr.evaluate_sandbox_execution_evidence(
        _e3_constructed_result(budget_observed={"command_count": 2, "tool_call_count": 0, "process_count": 1, "artifact_count": 1, "workspace_write_count": 1, "retry_count": 0, "duration_ms": 1})
    )
    truncated = gsr.evaluate_sandbox_execution_evidence(_e3_constructed_result(output_truncated=True))
    bad_artifact = gsr.evaluate_sandbox_execution_evidence(_e3_constructed_result(artifact_manifest=("../escape.txt",)))
    bad_write = gsr.evaluate_sandbox_execution_evidence(_e3_constructed_result(filesystem_write_manifest=("../escape.txt",)))

    assert budget.accepted_for_operator_review is False
    assert "budget_exceeded" in _finding_codes(budget)
    assert truncated.accepted_for_operator_review is True
    assert "output_truncated" in _finding_codes(truncated)
    assert bad_artifact.accepted_for_operator_review is False
    assert "unsupported_artifact" in _finding_codes(bad_artifact)
    assert bad_write.accepted_for_operator_review is False
    assert "external_write_detected" in _finding_codes(bad_write)


def test_e3a_action_evidence_fails_closed_without_creating_authority():
    cases = (
        ("provider_called", _e3_constructed_result(provider_called=True)),
        ("model_invoked", _e3_constructed_result(model_invoked=True)),
        ("memory_written", _e3_constructed_result(memory_written=True)),
        ("persistence_performed", _e3_constructed_result(persistence_performed=True)),
        ("module_activated", _e3_constructed_result(module_activated=True)),
        ("application_authority_detected", _e3_constructed_result(application_authorized=True)),
        ("application_authority_detected", _e3_constructed_result(application_performed=True)),
        ("second_attempt_created", _e3_constructed_result(second_attempt_created=True)),
        ("automatic_continuation", _e3_constructed_result(automatic_continuation=True)),
    )

    for expected_code, result in cases:
        evaluation = gsr.evaluate_sandbox_execution_evidence(result)
        assert evaluation.accepted_for_operator_review is False
        assert expected_code in _finding_codes(evaluation)
        assert evaluation.application_authorized is False
        assert evaluation.execution_authorization_created is False


def test_e3a_missing_evidence_fails_closed():
    result = replace(_e3_constructed_result(), evidence=None)
    evaluation = gsr.evaluate_sandbox_execution_evidence(result)

    assert evaluation.accepted_for_operator_review is False
    assert evaluation.classification == "evidence_incomplete"
    assert "evidence_incomplete" in _finding_codes(evaluation)


def test_e3a_operator_disposition_request_and_review_are_separate_from_evaluation():
    evaluation = gsr.evaluate_sandbox_execution_evidence(_e3_constructed_result())
    request = gsr.make_sandbox_evaluation_disposition_request(
        evaluation,
        proposed_disposition="accept_evidence_for_future_application_consideration",
    )
    disposition = gsr.make_sandbox_evaluation_disposition(
        request,
        decision="accept_evidence_for_future_application_consideration",
        reason="operator reviewed bounded evidence",
        issued_sequence=90,
    )
    review = gsr.review_sandbox_evaluation_disposition(evaluation, request, disposition)

    assert request.evaluation_id == evaluation.evaluation_id
    assert request.application_requested is False
    assert request.next_execution_requested is False
    assert review.accepted is True
    assert review.reason == "operator_disposition_recorded"
    assert review.application_authorized is False
    assert review.execution_authorized is False
    assert review.lifecycle_transition_applied is False
    assert review.automatic_continuation is False


def test_e3a_non_operator_and_wrong_evaluation_dispositions_fail_closed():
    evaluation = gsr.evaluate_sandbox_execution_evidence(_e3_constructed_result())
    request = gsr.make_sandbox_evaluation_disposition_request(evaluation, proposed_disposition="reject")
    non_operator = gsr.make_sandbox_evaluation_disposition(
        request,
        decision="reject",
        reason="bad authority",
        operator_authority="DELTA_GENERATED",
        issued_sequence=90,
    )
    wrong = replace(non_operator, operator_authority=gsr.OPERATOR_CONTROLLED_AUTHORITY, evaluation_id="wrong-evaluation")

    non_operator_review = gsr.review_sandbox_evaluation_disposition(evaluation, request, non_operator)
    wrong_review = gsr.review_sandbox_evaluation_disposition(evaluation, request, wrong)

    assert non_operator_review.accepted is False
    assert non_operator_review.reason == "operator_authority_required"
    assert wrong_review.accepted is False
    assert wrong_review.reason == "wrong_evaluation"


def _e3b_triplet(
    *,
    result: gsr.SandboxExecutionResult | None = None,
    decision: str = "accept_evidence_for_future_consideration",
    sequence: int = 120,
) -> tuple[gsr.SandboxEvidenceEvaluation, gsr.SandboxEvaluationDispositionRequest, gsr.SandboxEvaluationDisposition]:
    evaluation = gsr.evaluate_sandbox_execution_evidence(result or _e3_constructed_result())
    request = gsr.make_sandbox_evaluation_disposition_request(evaluation, proposed_disposition=decision)
    disposition = gsr.make_sandbox_evaluation_disposition(
        request,
        decision=decision,
        reason="operator recorded evidence disposition",
        issued_sequence=sequence,
    )
    return evaluation, request, disposition


def test_e3b_valid_operator_disposition_creates_one_inert_bound_record_and_consumes_replacement():
    evaluation, request, disposition = _e3b_triplet()

    result = gsr.apply_sandbox_evaluation_disposition(evaluation, request, disposition, sequence=120)

    assert result.accepted is True
    assert result.reason == "operator_evidence_disposition_recorded"
    assert result.disposition_applied is True
    assert result.disposition_authority_consumed is True
    assert result.record_created is True
    assert result.evaluation is evaluation
    assert result.request is request
    assert result.original_disposition == disposition
    assert result.consumed_disposition == replace(disposition, consumed=True)
    assert disposition.consumed is False
    assert result.consumed_disposition.consumed is True
    record = result.disposition_record
    assert record is not None
    assert record.evaluation_id == evaluation.evaluation_id
    assert record.evidence_digest == evaluation.evidence_digest
    assert record.cycle_id == evaluation.cycle_id
    assert record.plan_id == evaluation.plan_id
    assert record.attempt_id == evaluation.attempt_id
    assert record.request_id == evaluation.request_id
    assert record.authorization_id == evaluation.authorization_id
    assert record.disposition_request_id == request.disposition_request_id
    assert record.disposition_id == disposition.disposition_id
    assert record.operator_disposition == disposition.decision
    assert record.operator_issued is True
    assert record.disposition_authority_consumed is True
    assert record.accepted_evidence is True
    assert record.application_authorized is False
    assert record.execution_authorized is False
    assert record.lifecycle_transition_applied is False
    assert record.patch_created is False
    assert record.patch_applied is False
    assert record.source_mutated is False
    assert record.module_activated is False
    assert record.provider_called is False
    assert record.model_invoked is False
    assert record.memory_written is False
    assert record.persistence_performed is False
    assert record.scheduler_started is False
    assert record.thread_started is False
    assert record.background_task_started is False
    assert record.automatic_continuation is False
    assert result.execution_started is False
    assert result.sandbox_started is False
    assert result.next_execution_authorized is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert result.lifecycle_transition_applied is False
    assert result.patch_created is False
    assert result.patch_applied is False
    assert result.source_mutated is False
    assert result.module_activated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.automatic_continuation is False
    assert result.next_request_created is False


def test_e3b_exact_evaluation_request_and_disposition_identity_mismatches_fail_closed():
    evaluation, request, disposition = _e3b_triplet()
    cases = (
        (replace(disposition, evaluation_id="wrong-evaluation"), "wrong_evaluation"),
        (replace(disposition, disposition_request_id="wrong-request"), "wrong_disposition_request"),
        (replace(disposition, cycle_id="wrong-cycle"), "wrong_cycle"),
        (replace(disposition, plan_id="wrong-plan"), "wrong_plan"),
        (replace(disposition, attempt_id="wrong-attempt"), "wrong_attempt"),
        (replace(disposition, request_id="wrong-sandbox-request"), "wrong_request"),
        (replace(disposition, authorization_id="wrong-authorization"), "wrong_authorization"),
        (replace(disposition, evidence_digest="wrong-digest"), "wrong_evidence_digest"),
        (replace(disposition, decision="reject_evidence"), "wrong_disposition"),
        (
            replace(request, evaluation_id="wrong-evaluation"),
            "wrong_evaluation",
        ),
    )

    for bad_value, reason in cases:
        if isinstance(bad_value, gsr.SandboxEvaluationDispositionRequest):
            result = gsr.apply_sandbox_evaluation_disposition(evaluation, bad_value, disposition, sequence=120)
        else:
            result = gsr.apply_sandbox_evaluation_disposition(evaluation, request, bad_value, sequence=120)
        assert result.accepted is False
        assert result.reason == reason
        assert result.consumed_disposition is None
        assert result.disposition_record is None
        assert result.disposition_authority_consumed is False
        assert result.record_created is False


def test_e3b_operator_one_shot_consumption_and_expiration_fail_closed_without_consuming():
    evaluation, request, disposition = _e3b_triplet(sequence=120)
    bad_cases = (
        (replace(disposition, operator_authority="DELTA_GENERATED", accepted=False), "non_operator_disposition"),
        (replace(disposition, one_shot=False, accepted=True), "wrong_disposition"),
        (replace(disposition, consumed=True), "consumed"),
        (replace(disposition, issued_sequence=121), "expired"),
        (replace(disposition, decision="launch_application"), "unsupported_decision"),
        (replace(disposition, application_authorized=True), "application_authority_forbidden"),
        (replace(disposition, execution_authorized=True), "execution_authority_forbidden"),
        (replace(disposition, lifecycle_transition_applied=True), "lifecycle_authority_forbidden"),
        (replace(disposition, source_mutation_authorized=True), "source_mutation_forbidden"),
        (replace(disposition, automatic_continuation=True), "automatic_continuation_forbidden"),
    )

    for bad_disposition, reason in bad_cases:
        if bad_disposition.decision == "launch_application":
            bad_request = replace(request, proposed_disposition="launch_application")
        else:
            bad_request = request
        result = gsr.apply_sandbox_evaluation_disposition(evaluation, bad_request, bad_disposition, sequence=120)
        assert result.accepted is False
        assert result.reason == reason
        assert result.consumed_disposition is None
        assert result.disposition_record is None
        assert bad_disposition.consumed is (reason == "consumed")


def test_e3b_decision_compatibility_for_cleanup_integrity_and_incomplete_evidence():
    cleanup_eval, cleanup_req, cleanup_disp = _e3b_triplet(
        result=_e3_constructed_result(accepted=False, reason="cleanup_failed", cleanup_verified=False),
        decision="accept_evidence_for_future_consideration",
    )
    integrity_eval, integrity_req, integrity_disp = _e3b_triplet(
        result=_e3_constructed_result(accepted=False, reason="live_source_integrity_failed", live_source_unchanged=False),
        decision="accept_evidence_for_future_consideration",
    )
    incomplete_eval = gsr.evaluate_sandbox_execution_evidence(replace(_e3_constructed_result(), evidence=None))
    incomplete_req = gsr.make_sandbox_evaluation_disposition_request(
        incomplete_eval,
        proposed_disposition="accept_evidence_for_future_consideration",
    )
    incomplete_disp = gsr.make_sandbox_evaluation_disposition(
        incomplete_req,
        decision="accept_evidence_for_future_consideration",
        reason="bad acceptance",
        issued_sequence=120,
    )

    for evaluation, request, disposition in (
        (cleanup_eval, cleanup_req, cleanup_disp),
        (integrity_eval, integrity_req, integrity_disp),
        (incomplete_eval, incomplete_req, incomplete_disp),
    ):
        result = gsr.apply_sandbox_evaluation_disposition(evaluation, request, disposition, sequence=120)
        assert result.accepted is False
        assert result.reason == "decision_incompatible_with_evaluation"
        assert result.consumed_disposition is None
        assert result.disposition_record is None

    cleanup_mark = gsr.make_sandbox_evaluation_disposition_request(cleanup_eval, proposed_disposition="mark_cleanup_failure")
    cleanup_disposition = gsr.make_sandbox_evaluation_disposition(
        cleanup_mark,
        decision="mark_cleanup_failure",
        reason="operator marked cleanup failure",
        issued_sequence=120,
    )
    marked = gsr.apply_sandbox_evaluation_disposition(cleanup_eval, cleanup_mark, cleanup_disposition, sequence=120)
    assert marked.accepted is True
    assert marked.disposition_record.cleanup_failure_marked is True
    assert marked.disposition_record.application_authorized is False


def test_e3b_failed_execution_can_be_dispositioned_and_successful_execution_can_be_rejected():
    failed_eval, failed_req, failed_disp = _e3b_triplet(
        result=_e3_constructed_result(return_code=1, accepted=False, reason="command_failed"),
        decision="accept_evidence_for_future_consideration",
    )
    success_eval, success_req, success_disp = _e3b_triplet(decision="reject_evidence")

    failed = gsr.apply_sandbox_evaluation_disposition(failed_eval, failed_req, failed_disp, sequence=120)
    rejected = gsr.apply_sandbox_evaluation_disposition(success_eval, success_req, success_disp, sequence=120)

    assert failed.accepted is True
    assert failed.disposition_record.accepted_evidence is True
    assert failed.disposition_record.application_authorized is False
    assert rejected.accepted is True
    assert rejected.disposition_record.rejected_evidence is True
    assert rejected.disposition_record.application_authorized is False


def test_e3b_future_execution_and_lifecycle_dispositions_remain_metadata_only():
    another_eval, another_req, another_disp = _e3b_triplet(decision="request_another_sandbox_attempt")
    closure_eval, closure_req, closure_disp = _e3b_triplet(decision="close_objective_cycle_as_rejected")

    another = gsr.apply_sandbox_evaluation_disposition(another_eval, another_req, another_disp, sequence=120)
    closure = gsr.apply_sandbox_evaluation_disposition(closure_eval, closure_req, closure_disp, sequence=120)

    assert another.accepted is True
    assert another.disposition_record.another_execution_requested_metadata_only is True
    assert another.next_execution_authorized is False
    assert another.execution_authorized is False
    assert another.execution_started is False
    assert another.sandbox_started is False
    assert closure.accepted is True
    assert closure.disposition_record.lifecycle_closure_requested_metadata_only is True
    assert closure.lifecycle_transition_applied is False
    assert closure.next_request_created is False
    assert closure.automatic_continuation is False


def test_e3b_consumed_disposition_reuse_fails_closed():
    evaluation, request, disposition = _e3b_triplet()
    first = gsr.apply_sandbox_evaluation_disposition(evaluation, request, disposition, sequence=120)

    second = gsr.apply_sandbox_evaluation_disposition(evaluation, request, first.consumed_disposition, sequence=120)

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "consumed"
    assert second.consumed_disposition is None
    assert second.disposition_record is None


def _e4a_bundle(
    *,
    result: gsr.SandboxExecutionResult | None = None,
    disposition_decision: str = "accept_evidence_for_future_application_consideration",
    target_file_set: tuple[str, ...] = ("orchestration/runtime/example_target.py",),
    operation_set: tuple[str, ...] = ("replace_exact_file",),
    expected_hashes: dict[str, str] | None = None,
    artifact_digest: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
) -> tuple[
    gsr.SandboxEvidenceEvaluation,
    gsr.SandboxEvaluationDispositionRecord,
    gsr.ApplicationArtifact,
    gsr.ApplicationRequest,
    gsr.ApplicationAuthorization,
]:
    evaluation, disposition_request, disposition = _e3b_triplet(
        result=result,
        decision=disposition_decision,
        sequence=130,
    )
    disposition_result = gsr.apply_sandbox_evaluation_disposition(
        evaluation,
        disposition_request,
        disposition,
        sequence=130,
    )
    assert disposition_result.accepted is True
    record = disposition_result.disposition_record
    hashes = expected_hashes or {path: "a" * 64 for path in target_file_set}
    artifact = gsr.make_application_artifact(
        evaluation,
        record,
        proposed_application_artifact_id="artifact-e4a",
        proposed_application_artifact_digest=artifact_digest,
        target_file_set=target_file_set,
        operation_set=operation_set,
        expected_pre_application_hashes=hashes,
        target_scope=target_file_set,
    )
    request = gsr.make_application_request(
        evaluation,
        record,
        artifact,
        requested_sequence=140,
    )
    authorization = gsr.make_application_authorization(
        request,
        issued_sequence=140,
        expiration_sequence=150,
    )
    return evaluation, record, artifact, request, authorization


def _e4a_result(**overrides):
    evaluation, record, artifact, request, authorization = _e4a_bundle()
    evaluation = overrides.get("evaluation", evaluation)
    record = overrides.get("record", record)
    artifact = overrides.get("artifact", artifact)
    request = overrides.get("request", request)
    authorization = overrides.get("authorization", authorization)
    return gsr.evaluate_application_eligibility(
        evaluation,
        record,
        artifact,
        request,
        authorization,
        sequence=overrides.get("sequence", 140),
    )


def test_e4a_exact_accepted_evidence_disposition_artifact_request_and_authorization_are_eligible_only():
    result = _e4a_result()

    assert result.accepted is True
    assert result.reason == "valid"
    assert result.eligible_for_future_application is True
    assert result.application_started is False
    assert result.application_performed is False
    assert result.authorization_consumed is False
    assert result.patch_created is False
    assert result.patch_applied is False
    assert result.source_mutated is False
    assert result.files_written is False
    assert result.git_diff_created is False
    assert result.git_staged is False
    assert result.git_committed is False
    assert result.git_pushed is False
    assert result.git_merged is False
    assert result.deployed is False
    assert result.published is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False
    assert result.execution_started is False
    assert result.execution_authorized is False


def test_e4a_exact_identity_mismatches_fail_closed():
    evaluation, record, artifact, request, authorization = _e4a_bundle()
    cases = (
        ({"request": replace(request, evaluation_id="wrong-eval")}, "wrong_evaluation"),
        ({"request": replace(request, disposition_record_id="wrong-record")}, "wrong_disposition_record"),
        ({"request": replace(request, cycle_id="wrong-cycle")}, "wrong_cycle"),
        ({"request": replace(request, plan_id="wrong-plan")}, "wrong_plan"),
        ({"request": replace(request, attempt_id="wrong-attempt")}, "wrong_attempt"),
        ({"request": replace(request, request_id="wrong-exec-request")}, "wrong_execution_request"),
        ({"request": replace(request, authorization_id="wrong-exec-auth")}, "wrong_execution_authorization"),
        ({"request": replace(request, evidence_digest="wrong-digest")}, "wrong_evidence_digest"),
        ({"artifact": replace(artifact, artifact_id="wrong-artifact")}, "wrong_artifact"),
        ({"artifact": replace(artifact, artifact_digest="wrong-digest")}, "wrong_artifact_digest"),
        ({"authorization": replace(authorization, application_request_id="wrong-app-request")}, "wrong_application_authorization"),
    )

    for override, reason in cases:
        assert _e4a_result(evaluation=evaluation, record=record, artifact=override.get("artifact", artifact), request=override.get("request", request), authorization=override.get("authorization", authorization)).reason == reason


def test_e4a_incompatible_evaluation_or_disposition_fails_closed():
    cleanup_eval, cleanup_record, cleanup_artifact, cleanup_request, cleanup_auth = _e4a_bundle(
        result=_e3_constructed_result(accepted=False, reason="cleanup_failed", cleanup_verified=False),
        disposition_decision="mark_cleanup_failure",
    )
    integrity_eval, integrity_record, integrity_artifact, integrity_request, integrity_auth = _e4a_bundle(
        result=_e3_constructed_result(accepted=False, reason="live_source_integrity_failed", live_source_unchanged=False),
        disposition_decision="mark_live_source_integrity_failure",
    )
    incomplete = replace(_e3_constructed_result(), evidence=None)
    incomplete_eval = gsr.evaluate_sandbox_execution_evidence(incomplete)
    base_eval, _, _, _, _ = _e4a_bundle()
    bad_record = replace(_e4a_bundle()[1], operator_disposition="reject_evidence", accepted_evidence=False, rejected_evidence=True)

    assert gsr.evaluate_application_eligibility(cleanup_eval, cleanup_record, cleanup_artifact, cleanup_request, cleanup_auth, sequence=140).reason == "cleanup_not_verified"
    assert gsr.evaluate_application_eligibility(integrity_eval, integrity_record, integrity_artifact, integrity_request, integrity_auth, sequence=140).reason == "live_source_integrity_failed"
    assert gsr.evaluate_application_eligibility(incomplete_eval, _e4a_bundle()[1], _e4a_bundle()[2], _e4a_bundle()[3], _e4a_bundle()[4], sequence=140).reason == "evidence_incomplete"
    assert _e4a_result(evaluation=base_eval, record=bad_record).reason == "incompatible_disposition"


def test_e4a_application_request_authorization_scope_artifact_and_precondition_mismatches_fail_closed():
    evaluation, record, artifact, request, authorization = _e4a_bundle()
    cases = (
        (replace(request, target_file_set=("orchestration/runtime/other.py",)), authorization, "target_file_mismatch"),
        (replace(request, requested_operation_set=("add_exact_reviewed_file",)), authorization, "operation_mismatch"),
        (replace(request, expected_pre_application_hashes={request.target_file_set[0]: "b" * 64}), authorization, "precondition_mismatch"),
        (request, replace(authorization, authorized_target_file_set=("orchestration/runtime/other.py",)), "target_file_mismatch"),
        (request, replace(authorization, expected_pre_application_hashes={request.target_file_set[0]: "b" * 64}), "precondition_mismatch"),
    )

    for bad_request, bad_authorization, reason in cases:
        result = gsr.evaluate_application_eligibility(evaluation, record, artifact, bad_request, bad_authorization, sequence=140)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.patch_applied is False
        assert result.source_mutated is False

    duplicate_files = (request.target_file_set[0], request.target_file_set[0])
    duplicate_artifact = replace(artifact, target_file_set=duplicate_files, target_scope=duplicate_files)
    duplicate_request = replace(request, target_file_set=duplicate_files, target_scope=duplicate_files)
    duplicate_authorization = replace(authorization, authorized_target_file_set=duplicate_files, authorized_target_scope=duplicate_files)
    duplicate_result = gsr.evaluate_application_eligibility(evaluation, record, duplicate_artifact, duplicate_request, duplicate_authorization, sequence=140)
    assert duplicate_result.accepted is False
    assert duplicate_result.reason == "precondition_mismatch"

    unsupported_artifact = replace(artifact, operation_set=("run_shell_command",))
    unsupported_request = replace(request, requested_operation_set=("run_shell_command",))
    unsupported_authorization = replace(authorization, authorized_operation_set=("run_shell_command",))
    unsupported_result = gsr.evaluate_application_eligibility(evaluation, record, unsupported_artifact, unsupported_request, unsupported_authorization, sequence=140)
    assert unsupported_result.accepted is False
    assert unsupported_result.reason == "unsupported_operation"

    for unsafe_path in (
        "../escape.py",
        "C:/outside.py",
        "*.py",
        ".git/config",
        ".env",
        "reports/RC4_FREEZE_READINESS_FINAL.md",
        "DELTA-75/secret.py",
        ".github/workflows/deploy.yml",
        "data/canonical_memory/store.sqlite",
    ):
        hashes = {unsafe_path: "a" * 64}
        unsafe_artifact = replace(artifact, target_file_set=(unsafe_path,), target_scope=(unsafe_path,), expected_pre_application_hashes=hashes)
        unsafe_request = replace(request, target_file_set=(unsafe_path,), target_scope=(unsafe_path,), expected_pre_application_hashes=hashes)
        unsafe_authorization = replace(authorization, authorized_target_file_set=(unsafe_path,), authorized_target_scope=(unsafe_path,), expected_pre_application_hashes=hashes)
        unsafe_result = gsr.evaluate_application_eligibility(evaluation, record, unsafe_artifact, unsafe_request, unsafe_authorization, sequence=140)
        assert unsafe_result.accepted is False
        assert unsafe_result.reason == "unsafe_target"


def test_e4a_operator_authorization_availability_and_forbidden_authority_fail_closed():
    _, _, _, request, authorization = _e4a_bundle()
    cases = (
        (replace(authorization, operator_authority="DELTA_GENERATED"), "non_operator_authorization"),
        (replace(authorization, consumed=True), "consumed"),
        (replace(authorization, expiration_sequence=139), "expired"),
        (replace(authorization, application_started=True), "immediate_application_authority"),
        (replace(authorization, git_stage_authorized=True), "forbidden_scope"),
        (replace(authorization, git_commit_authorized=True), "forbidden_scope"),
        (replace(authorization, git_push_authorized=True), "forbidden_scope"),
        (replace(authorization, merge_authorized=True), "forbidden_scope"),
        (replace(authorization, deployment_authorized=True), "forbidden_scope"),
        (replace(authorization, publication_authorized=True), "forbidden_scope"),
        (replace(authorization, module_activation_authorized=True), "forbidden_scope"),
        (replace(authorization, provider_model_authorized=True), "forbidden_scope"),
        (replace(authorization, memory_write_authorized=True), "forbidden_scope"),
        (replace(authorization, persistence_authorized=True), "forbidden_scope"),
        (replace(authorization, scheduler_authorized=True), "forbidden_scope"),
        (replace(authorization, thread_authorized=True), "forbidden_scope"),
        (replace(authorization, background_task_authorized=True), "forbidden_scope"),
        (replace(authorization, lifecycle_transition_authorized=True), "forbidden_scope"),
        (replace(authorization, another_execution_authorized=True), "forbidden_scope"),
        (replace(authorization, automatic_continuation=True), "forbidden_scope"),
        (replace(request, immediate_application_authority=True), "immediate_application_authority"),
        (replace(request, git_commit_authorized=True), "forbidden_scope"),
        (replace(request, provider_model_authorized=True), "forbidden_scope"),
        (replace(request, memory_write_authorized=True), "forbidden_scope"),
        (replace(request, scheduler_authorized=True), "forbidden_scope"),
        (replace(request, lifecycle_transition_authorized=True), "forbidden_scope"),
        (replace(request, another_execution_authorized=True), "forbidden_scope"),
    )

    for bad_value, reason in cases:
        if isinstance(bad_value, gsr.ApplicationAuthorization):
            result = _e4a_result(request=request, authorization=bad_value)
        else:
            result = _e4a_result(request=bad_value)
        assert result.accepted is False
        assert result.reason == reason
        assert result.eligible_for_future_application is False
        assert result.authorization_consumed is False


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _e4b_package(
    tmp_path: Path,
    *,
    target_name: str = "safe_target.txt",
    content: str = "before\n",
    operation: str = "replace_exact_file",
    create_target: bool = True,
    worktree: gsr.ApplicationWorktreeStatus | None = None,
) -> tuple[gsr.ApplicationEligibilityResult, gsr.ApplicationPlan, Path, gsr.ApplicationWorktreeStatus]:
    target = tmp_path / target_name
    if create_target:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))
    target_hash = _sha256_text(content) if create_target else "0" * 64
    evaluation, record, artifact, request, authorization = _e4a_bundle(
        target_file_set=(target_name,),
        operation_set=(operation,),
        expected_hashes={target_name: target_hash},
    )
    eligibility = gsr.evaluate_application_eligibility(
        evaluation,
        record,
        artifact,
        request,
        authorization,
        sequence=140,
    )
    assert eligibility.accepted is True
    if operation == "add_exact_reviewed_file":
        rollback_operation = "delete_added_file"
        rollback_hash = None
    elif operation == "delete_exact_reviewed_generated_file":
        rollback_operation = "restore_deleted_file"
        rollback_hash = target_hash
    else:
        rollback_operation = "restore_exact_content"
        rollback_hash = target_hash
    plan_operation = gsr.ApplicationPlanOperation(
        sequence=1,
        operation=operation,
        target_path=target_name,
        expected_current_hash=target_hash if create_target else None,
        expected_post_application_hash="b" * 64,
        expected_absent_before=not create_target,
        rollback_operation=rollback_operation,
        rollback_artifact_id="rollback-artifact-1",
        rollback_target_path=target_name,
        rollback_expected_hash=rollback_hash,
    )
    plan = gsr.make_application_plan(
        eligibility,
        ordered_target_operations=(plan_operation,),
        expected_post_application_hashes={target_name: "b" * 64},
        rollback_metadata=(
            {
                "target_path": target_name,
                "rollback_operation": rollback_operation,
                "rollback_artifact_id": "rollback-artifact-1",
                "rollback_target_path": target_name,
                "rollback_expected_hash": rollback_hash,
            },
        ),
        application_sequence=150,
    )
    return eligibility, plan, target, worktree or gsr.ApplicationWorktreeStatus(
        modified_paths=("reports/RC4_FREEZE_READINESS_FINAL.md", "DELTA.py"),
        known_dirty_paths=("reports/RC4_FREEZE_READINESS_FINAL.md",),
        expected_dirty_paths=("DELTA.py", "tests/runtime_gsr/test_gsr_evaluation_tab_ui.py"),
    )


def test_e4b_exact_package_passes_read_only_preflight_without_actions(tmp_path):
    eligibility, plan, target, worktree = _e4b_package(tmp_path)
    before_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    authorization_before = asdict(eligibility.authorization)

    result = gsr.evaluate_application_preflight(eligibility, plan, root=tmp_path, worktree=worktree, sequence=141)

    assert result.accepted is True
    assert result.reason == "valid"
    assert result.ready_for_future_application is True
    assert result.current_target_hashes["safe_target.txt"] == before_hash
    assert target.read_text(encoding="utf-8") == "before\n"
    assert asdict(eligibility.authorization) == authorization_before
    assert result.authorization_consumed is False
    assert result.application_started is False
    assert result.patch_created is False
    assert result.patch_applied is False
    assert result.source_mutated is False
    assert result.files_written is False
    assert result.git_diff_created is False
    assert result.git_staged is False
    assert result.git_committed is False
    assert result.git_pushed is False
    assert result.git_merged is False
    assert result.deployed is False
    assert result.published is False
    assert result.module_activated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False
    assert result.execution_started is False
    assert result.execution_authorized is False
    assert "reports/RC4_FREEZE_READINESS_FINAL.md" in result.worktree_classification["known_unrelated_dirty"]
    assert "DELTA.py" in result.worktree_classification["expected_unrelated_dirty"]


def test_e4b_add_replace_and_delete_target_expectations_are_read_only(tmp_path):
    add_eligibility, add_plan, add_target, worktree = _e4b_package(
        tmp_path,
        target_name="new_file.txt",
        operation="add_exact_reviewed_file",
        create_target=False,
    )
    add_result = gsr.evaluate_application_preflight(add_eligibility, add_plan, root=tmp_path, worktree=worktree, sequence=141)
    assert add_result.accepted is True
    assert add_result.target_existence_map["new_file.txt"] is False
    assert add_target.exists() is False

    replace_eligibility, replace_plan, replace_target, worktree = _e4b_package(tmp_path, target_name="replace_file.txt")
    replace_result = gsr.evaluate_application_preflight(replace_eligibility, replace_plan, root=tmp_path, worktree=worktree, sequence=141)
    assert replace_result.accepted is True
    assert replace_result.target_type_map["replace_file.txt"] == "file"
    assert replace_target.read_text(encoding="utf-8") == "before\n"

    delete_eligibility, delete_plan, delete_target, worktree = _e4b_package(
        tmp_path,
        target_name="delete_file.txt",
        operation="delete_exact_reviewed_generated_file",
    )
    delete_result = gsr.evaluate_application_preflight(delete_eligibility, delete_plan, root=tmp_path, worktree=worktree, sequence=141)
    assert delete_result.accepted is True
    assert delete_target.exists() is True

    add_target.write_text("collision\n", encoding="utf-8")
    collision = gsr.evaluate_application_preflight(add_eligibility, add_plan, root=tmp_path, worktree=worktree, sequence=141)
    assert collision.accepted is False
    assert collision.reason == "target_unexpectedly_exists"


def test_e4b_plan_artifact_authorization_and_order_mismatches_fail_closed(tmp_path):
    eligibility, plan, _target, worktree = _e4b_package(tmp_path)
    cases = (
        (replace(plan, application_request_id="wrong-request"), "wrong_application_request"),
        (replace(plan, application_authorization_id="wrong-authorization"), "wrong_application_authorization"),
        (replace(plan, artifact_id="wrong-artifact"), "wrong_artifact"),
        (replace(plan, artifact_digest="wrong-digest"), "wrong_artifact_digest"),
        (replace(plan, evaluation_id="wrong-evaluation"), "wrong_evaluation"),
        (replace(plan, disposition_record_id="wrong-record"), "wrong_disposition_record"),
        (replace(plan, evidence_digest="wrong-digest"), "wrong_evidence_digest"),
        (replace(plan, target_file_set=("other.txt",)), "target_file_mismatch"),
        (replace(plan, ordered_target_operations=(replace(plan.ordered_target_operations[0], operation="add_exact_reviewed_file"),)), "operation_mismatch"),
        (replace(plan, ordered_target_operations=(replace(plan.ordered_target_operations[0], sequence=2),)), "operation_order_invalid"),
        (replace(plan, ordered_target_operations=(plan.ordered_target_operations[0], plan.ordered_target_operations[0])), "operation_mismatch"),
        (replace(plan, rollback_metadata=()), "rollback_metadata_missing"),
        (
            replace(plan, rollback_metadata=({**plan.rollback_metadata[0], "rollback_artifact_id": "wrong"},)),
            "rollback_artifact_mismatch",
        ),
        (
            replace(plan, rollback_metadata=({**plan.rollback_metadata[0], "rollback_target_path": "other.txt"},)),
            "rollback_scope_mismatch",
        ),
        (
            replace(plan, ordered_target_operations=(replace(plan.ordered_target_operations[0], rollback_operation="delete_added_file"),), rollback_metadata=({**plan.rollback_metadata[0], "rollback_operation": "delete_added_file"},)),
            "rollback_not_exact",
        ),
    )
    for bad_plan, reason in cases:
        result = gsr.evaluate_application_preflight(eligibility, bad_plan, root=tmp_path, worktree=worktree, sequence=141)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.source_mutated is False


def test_e4b_target_hash_type_size_symlink_and_forbidden_paths_fail_closed(tmp_path):
    eligibility, plan, target, worktree = _e4b_package(tmp_path)
    target.write_text("changed\n", encoding="utf-8")
    stale = gsr.evaluate_application_preflight(eligibility, plan, root=tmp_path, worktree=worktree, sequence=141)
    assert stale.accepted is False
    assert stale.reason == "stale_precondition"

    missing_eligibility, missing_plan, _missing_target, worktree = _e4b_package(tmp_path, target_name="missing.txt")
    (tmp_path / "missing.txt").unlink()
    missing = gsr.evaluate_application_preflight(missing_eligibility, missing_plan, root=tmp_path, worktree=worktree, sequence=141)
    assert missing.accepted is False
    assert missing.reason == "target_missing"

    dir_eligibility, dir_plan, dir_target, worktree = _e4b_package(tmp_path, target_name="dir_target")
    dir_target.unlink()
    dir_target.mkdir()
    directory = gsr.evaluate_application_preflight(dir_eligibility, dir_plan, root=tmp_path, worktree=worktree, sequence=141)
    assert directory.accepted is False
    assert directory.reason == "target_type_mismatch"

    large_eligibility, large_plan, large_target, worktree = _e4b_package(tmp_path, target_name="large.txt", content="x")
    large_target.write_bytes(b"x" * (gsr.MAX_APPLICATION_PREFLIGHT_TARGET_BYTES + 1))
    oversized = gsr.evaluate_application_preflight(large_eligibility, large_plan, root=tmp_path, worktree=worktree, sequence=141)
    assert oversized.accepted is False
    assert oversized.reason == "target_too_large"

    symlink_path = tmp_path / "link.txt"
    if hasattr(symlink_path, "symlink_to"):
        symlink_eligibility, symlink_plan, symlink_target, worktree = _e4b_package(tmp_path, target_name="link.txt")
        symlink_target.unlink()
        try:
            symlink_path.symlink_to(tmp_path / "safe_target.txt")
        except OSError:
            pass
        else:
            symlink = gsr.evaluate_application_preflight(symlink_eligibility, symlink_plan, root=tmp_path, worktree=worktree, sequence=141)
            assert symlink.accepted is False
            assert symlink.reason == "unsafe_target"

    for unsafe_path in ("../escape.py", "C:/outside.py", "*.py", ".git/config", ".env", "reports/RC4_X.md", "DELTA-75/secret.py", "data/canonical_memory/store.sqlite"):
        unsafe_eligibility, unsafe_plan, _target, worktree = _e4b_package(tmp_path, target_name="safe_again.txt")
        unsafe_plan = replace(
            unsafe_plan,
            target_file_set=(unsafe_path,),
            ordered_target_operations=(replace(unsafe_plan.ordered_target_operations[0], target_path=unsafe_path),),
            expected_current_hashes={unsafe_path: "a" * 64},
            rollback_metadata=({**unsafe_plan.rollback_metadata[0], "target_path": unsafe_path, "rollback_target_path": unsafe_path},),
        )
        unsafe = gsr.evaluate_application_preflight(unsafe_eligibility, unsafe_plan, root=tmp_path, worktree=worktree, sequence=141)
        assert unsafe.accepted is False
        assert unsafe.reason in {"unsafe_target", "forbidden_scope", "target_file_mismatch"}


def test_e4b_worktree_boundary_and_authorization_failures_do_not_consume(tmp_path):
    eligibility, plan, _target, _worktree = _e4b_package(tmp_path)
    cases = (
        (gsr.ApplicationWorktreeStatus(staged_paths=("safe_target.txt",)), "staged_target"),
        (gsr.ApplicationWorktreeStatus(conflicted_paths=("safe_target.txt",)), "conflicted_target"),
        (gsr.ApplicationWorktreeStatus(modified_paths=("safe_target.txt",)), "unexpected_dirty_target"),
        (gsr.ApplicationWorktreeStatus(untracked_paths=("safe_target.txt",)), "untracked_target_collision"),
    )
    for worktree, reason in cases:
        result = gsr.evaluate_application_preflight(eligibility, plan, root=tmp_path, worktree=worktree, sequence=141)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False

    consumed = replace(eligibility.authorization, consumed=True)
    consumed_eligibility = replace(eligibility, authorization=consumed)
    consumed_result = gsr.evaluate_application_preflight(consumed_eligibility, plan, root=tmp_path, worktree=gsr.ApplicationWorktreeStatus(), sequence=141)
    assert consumed_result.accepted is False
    assert consumed_result.reason == "consumed"

    expired = replace(eligibility.authorization, expiration_sequence=140)
    expired_eligibility = replace(eligibility, authorization=expired)
    expired_result = gsr.evaluate_application_preflight(expired_eligibility, plan, root=tmp_path, worktree=gsr.ApplicationWorktreeStatus(), sequence=141)
    assert expired_result.accepted is False
    assert expired_result.reason == "expired"

    denied_eligibility = replace(eligibility, accepted=False, eligible_for_future_application=False)
    denied = gsr.evaluate_application_preflight(denied_eligibility, plan, root=tmp_path, worktree=gsr.ApplicationWorktreeStatus(), sequence=141)
    assert denied.accepted is False
    assert denied.reason == "eligibility_not_accepted"
