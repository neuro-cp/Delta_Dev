from __future__ import annotations

import json

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


PROPOSAL_ID = "proposal-ready-for-sandbox-planning"
OTHER_PROPOSAL_ID = "other-proposal"


def _proposal_state(*, eligible: bool = True) -> gsr.DiagnosisProposalState:
    return gsr.DiagnosisProposalState(
        state_version="GSR-C-1",
        future_sandbox_planning_eligible_proposals=(PROPOSAL_ID,) if eligible else (),
    )


def _planning_state() -> gsr.SandboxPlanningState:
    return gsr.make_sandbox_planning_state()


def _authorization(**kwargs) -> gsr.SandboxPlanningAuthorization:
    return gsr.make_sandbox_planning_authorization(
        PROPOSAL_ID,
        allowed_planning_scope=("sandbox_plan_drafting",),
        decision_sequence=10,
        **kwargs,
    )


def _attempt(
    proposal_state: gsr.DiagnosisProposalState | None = None,
    planning_state: gsr.SandboxPlanningState | None = None,
    authorization: gsr.SandboxPlanningAuthorization | None = None,
    *,
    proposal_id: str = PROPOSAL_ID,
    sequence: int = 10,
) -> gsr.SandboxPlanCreationResult:
    return gsr.authorize_sandbox_plan_creation(
        proposal_state or _proposal_state(),
        planning_state or _planning_state(),
        authorization,
        proposal_id=proposal_id,
        sequence=sequence,
    )


def _assert_no_actions(result: gsr.SandboxPlanCreationResult) -> None:
    assert result.sandbox_created is False
    assert result.sandbox_started is False
    assert result.workspace_created is False
    assert result.repository_cloned is False
    assert result.command_executed is False
    assert result.tool_invoked is False
    assert result.patch_created is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.registry_mutated is False
    assert result.permissions_granted is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.network_accessed is False
    assert result.memory_written is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False


def _authorized_state() -> tuple[gsr.DiagnosisProposalState, gsr.SandboxPlanningState, gsr.SandboxPlanningAuthorization]:
    proposal_state = _proposal_state()
    authorization = _authorization()
    authorized = _attempt(proposal_state=proposal_state, authorization=authorization)
    assert authorized.accepted is True
    return proposal_state, authorized.state, authorization


def _module_kwargs(**overrides):
    payload = {
        "module_identifier": "review-only-python-adapter",
        "module_type": "python_module",
        "source_package_description": "existing module package description only",
        "required_interfaces": ("proposal_review",),
        "requested_permissions": ("repo_read", "proposal_prepare"),
        "forbidden_permissions": ("provider_call", "network_call", "source_mutation"),
        "data_access_boundaries": ("fixture metadata only",),
        "network_boundaries": ("network prohibited",),
        "memory_boundaries": ("memory writes prohibited",),
        "tool_boundaries": ("tool invocation prohibited",),
        "lifecycle_hooks_described": ("manual review before activation",),
        "activation_conditions": ("future explicit operator activation gate",),
        "deactivation_conditions": ("manual removal gate",),
        "rollback_or_removal_description": "remove the plan artifact from review queue",
        "compatibility_requirements": ("GSR plan-only contract",),
        "validation_requirements": ("focused inertness tests",),
    }
    payload.update(overrides)
    return payload


def _plan_kwargs(**overrides):
    payload = {
        "proposal_id": PROPOSAL_ID,
        "disposable_workspace_description": "temporary workspace description only; no path is created",
        "repository_snapshot_description": "read-only source snapshot description",
        "files_or_components_in_scope": ("orchestration/runtime/example.py",),
        "forbidden_files_or_components": ("DELTA.py", "live_router"),
        "allowed_tool_classes": ("read_only_inspection",),
        "forbidden_tool_classes": ("command_execution", "patch_generation", "source_mutation"),
        "allowed_command_categories": ("focused_test_runner",),
        "forbidden_command_categories": ("shell_command", "git_operation", "deployment"),
        "test_selection": ("tests/runtime_gsr/test_gsr_d_sandbox_planning.py",),
        "focused_test_requirements": ("D1-B focused tests",),
        "adjacent_test_requirements": ("GSR-C/B/A regression",),
        "live_runtime_evidence_requirements": ("none for D1-B",),
        "provider_model_restrictions": ("provider calls prohibited", "model inference prohibited"),
        "network_restrictions": ("network access prohibited",),
        "memory_write_restrictions": ("canonical and noncanonical writes prohibited",),
        "source_mutation_restrictions": ("source mutation prohibited",),
        "success_criteria": ("plan accepted as PLAN_ONLY",),
        "failure_criteria": ("any execution flag true",),
        "rollback_proof_requirements": ("discard inert plan artifact",),
        "cleanup_proof_requirements": ("no workspace exists to clean up",),
        "artifact_retention_policy": "review metadata only; no persistence side effect",
        "execution_budget_metadata": ("zero command execution budget",),
        "creation_sequence": 20,
    }
    payload.update(overrides)
    return payload


def _create_plan(
    proposal_state: gsr.DiagnosisProposalState | None = None,
    planning_state: gsr.SandboxPlanningState | None = None,
    authorization: gsr.SandboxPlanningAuthorization | None = None,
    **overrides,
) -> gsr.SandboxPlanCreationResult:
    if planning_state is None or authorization is None:
        default_proposal_state, planning_state, authorization = _authorized_state()
        if proposal_state is None:
            proposal_state = default_proposal_state
    kwargs = _plan_kwargs(**overrides)
    return gsr.create_inert_sandbox_plan(proposal_state, planning_state, authorization, **kwargs)


def test_d1a_proposal_eligibility_alone_cannot_create_plan():
    result = _attempt(authorization=None)

    assert result.accepted is False
    assert result.reason == "sandbox_planning_authorization_required"
    assert result.state.consumed_planning_authorization_ids == ()
    assert result.state.sandbox_plans == ()
    _assert_no_actions(result)


def test_d1a_valid_operator_authorization_permits_one_inert_plan_creation_attempt():
    authorization = _authorization()
    result = _attempt(authorization=authorization)

    assert result.accepted is True
    assert result.reason == "sandbox_planning_authorization_accepted"
    assert result.authorization == authorization
    assert result.state.planning_authorization_ids == (authorization.authorization_id,)
    assert result.state.consumed_planning_authorization_ids == (authorization.authorization_id,)
    assert result.state.sandbox_plans == ()
    assert result.state.module_attachment_plans == ()
    _assert_no_actions(result)


def test_d1a_wrong_target_authorization_fails_without_consuming():
    authorization = gsr.make_sandbox_planning_authorization(
        OTHER_PROPOSAL_ID,
        allowed_planning_scope=("sandbox_plan_drafting",),
        decision_sequence=10,
    )
    proposal_state = gsr.DiagnosisProposalState(
        state_version="GSR-C-1",
        future_sandbox_planning_eligible_proposals=(PROPOSAL_ID, OTHER_PROPOSAL_ID),
    )

    result = _attempt(proposal_state=proposal_state, authorization=authorization)

    assert result.accepted is False
    assert result.reason == "sandbox_planning_authorization_target_mismatch"
    assert result.state.consumed_planning_authorization_ids == ()
    _assert_no_actions(result)


def test_d1a_non_operator_authorization_fails_without_consuming():
    result = _attempt(authorization=_authorization(operator_authority="DELTA_SELF_AUTHORITY"))

    assert result.accepted is False
    assert result.reason == "operator_authority_required"
    assert result.state.consumed_planning_authorization_ids == ()
    _assert_no_actions(result)


def test_d1a_expired_authorization_fails_without_consuming():
    result = _attempt(authorization=_authorization(expires_after_sequence=9), sequence=10)

    assert result.accepted is False
    assert result.reason == "sandbox_planning_authorization_expired"
    assert result.state.consumed_planning_authorization_ids == ()
    _assert_no_actions(result)


def test_d1a_consumed_authorization_fails_without_consuming_state():
    result = _attempt(authorization=_authorization(consumed=True))

    assert result.accepted is False
    assert result.reason == "sandbox_planning_authorization_consumed"
    assert result.state.consumed_planning_authorization_ids == ()
    _assert_no_actions(result)


def test_d1a_reused_authorization_fails_closed():
    authorization = _authorization()
    first = _attempt(authorization=authorization)
    second = _attempt(planning_state=first.state, authorization=authorization)

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "sandbox_planning_authorization_already_consumed"
    assert first.state.consumed_planning_authorization_ids == (authorization.authorization_id,)
    assert second.state.consumed_planning_authorization_ids == (authorization.authorization_id,)
    _assert_no_actions(second)


def test_d1a_failed_attempts_remain_unconsumed():
    authorization = _authorization(operator_authority="DELTA_GENERATED")
    failed = _attempt(authorization=authorization)
    valid = _attempt(authorization=_authorization())

    assert failed.accepted is False
    assert failed.state.consumed_planning_authorization_ids == ()
    assert valid.accepted is True
    assert valid.state.consumed_planning_authorization_ids


def test_d1a_ineligible_proposal_fails_even_with_authorization():
    authorization = _authorization()
    result = _attempt(proposal_state=_proposal_state(eligible=False), authorization=authorization)

    assert result.accepted is False
    assert result.reason == "proposal_not_future_sandbox_planning_eligible"
    assert result.state.consumed_planning_authorization_ids == ()
    _assert_no_actions(result)


def test_d1a_serialization_preserves_consumed_authorization_ids_without_plans():
    authorization = _authorization()
    result = _attempt(authorization=authorization)

    restored = gsr.deserialize(gsr.SandboxPlanningState, json.loads(json.dumps(gsr.serialize(result.state))))

    assert restored.consumed_planning_authorization_ids == (authorization.authorization_id,)
    assert restored.sandbox_plans == ()
    assert restored.future_sandbox_execution_eligible_plans == ()


def test_d1b_no_plan_without_consumed_d1a_authorization_or_eligibility():
    proposal_state = _proposal_state()
    authorization = _authorization()

    unconsumed = gsr.create_inert_sandbox_plan(proposal_state, _planning_state(), authorization, **_plan_kwargs())
    ineligible = _create_plan(proposal_state=_proposal_state(eligible=False))

    assert unconsumed.accepted is False
    assert unconsumed.reason == "consumed_sandbox_planning_authorization_required"
    assert ineligible.accepted is False
    assert ineligible.reason == "proposal_not_future_sandbox_planning_eligible"
    assert unconsumed.state.sandbox_plans == ()
    _assert_no_actions(unconsumed)


def test_d1b_target_scope_and_authorization_reuse_fail_closed():
    proposal_state, planning_state, authorization = _authorized_state()
    wrong_target = _create_plan(proposal_state=proposal_state, planning_state=planning_state, authorization=authorization, proposal_id=OTHER_PROPOSAL_ID)
    forbidden_scope_auth = gsr.make_sandbox_planning_authorization(
        PROPOSAL_ID,
        allowed_planning_scope=("observation_only",),
        decision_sequence=11,
    )
    forbidden_state = _attempt(proposal_state=proposal_state, authorization=forbidden_scope_auth).state
    scope_mismatch = _create_plan(proposal_state=proposal_state, planning_state=forbidden_state, authorization=forbidden_scope_auth)
    created = _create_plan(proposal_state=proposal_state, planning_state=planning_state, authorization=authorization)
    reused = _create_plan(proposal_state=proposal_state, planning_state=created.state, authorization=authorization)

    assert wrong_target.reason == "proposal_not_future_sandbox_planning_eligible"
    assert scope_mismatch.reason == "sandbox_planning_scope_mismatch"
    assert created.accepted is True
    assert reused.accepted is False
    assert reused.reason == "sandbox_planning_authorization_already_used_for_plan"
    _assert_no_actions(reused)


def test_d1b_authorization_restriction_mismatch_fails_closed():
    proposal_state = _proposal_state()
    authorization = gsr.make_sandbox_planning_authorization(
        PROPOSAL_ID,
        allowed_planning_scope=("sandbox_plan_drafting",),
        allowed_tool_classes=("read_only_inspection",),
        forbidden_tool_classes=("compiler",),
        decision_sequence=12,
    )
    planning_state = _attempt(proposal_state=proposal_state, authorization=authorization).state
    outside = _create_plan(
        proposal_state=proposal_state,
        planning_state=planning_state,
        authorization=authorization,
        allowed_tool_classes=("compiler",),
    )

    assert outside.accepted is False
    assert outside.reason == "tool_class_outside_authorization"
    assert outside.state.sandbox_plans == ()
    _assert_no_actions(outside)


def test_d1b_accepted_plan_links_exact_proposal_and_authorization():
    proposal_state, planning_state, authorization = _authorized_state()
    result = _create_plan(proposal_state=proposal_state, planning_state=planning_state, authorization=authorization)

    assert result.accepted is True
    assert result.reason == "inert_sandbox_plan_created"
    assert result.sandbox_plan is not None
    assert result.sandbox_plan.proposal_id == PROPOSAL_ID
    assert result.sandbox_plan.planning_authorization_id == authorization.authorization_id
    assert result.sandbox_plan.plan_only_status == "PLAN_ONLY"
    assert result.sandbox_plan.operator_review_status == "pending_review"
    assert result.state.pending_plan_review_queue == (result.sandbox_plan.plan_id,)
    assert result.state.plan_ids_by_proposal[PROPOSAL_ID] == (result.sandbox_plan.plan_id,)
    assert result.state.future_sandbox_execution_eligible_plans == ()
    _assert_no_actions(result)


def test_d1b_scope_overlap_and_missing_required_plan_fields_fail_closed():
    cases = [
        ("file_scope_overlaps_forbidden_scope", {"files_or_components_in_scope": ("DELTA.py",)}),
        ("tool_class_overlaps_forbidden_tool_class", {"allowed_tool_classes": ("command_execution",)}),
        ("command_category_overlaps_forbidden_category", {"allowed_command_categories": ("shell_command",)}),
        ("rollback_proof_requirements_required", {"rollback_proof_requirements": ()}),
        ("cleanup_proof_requirements_required", {"cleanup_proof_requirements": ()}),
        ("provider_model_restrictions_required", {"provider_model_restrictions": ()}),
        ("network_restrictions_required", {"network_restrictions": ()}),
        ("memory_write_restrictions_required", {"memory_write_restrictions": ()}),
        ("source_mutation_restrictions_required", {"source_mutation_restrictions": ()}),
        ("success_criteria_required", {"success_criteria": ()}),
        ("failure_criteria_required", {"failure_criteria": ()}),
        ("artifact_retention_policy_required", {"artifact_retention_policy": ""}),
    ]

    for reason, overrides in cases:
        result = _create_plan(**overrides)
        assert result.accepted is False
        assert result.reason == reason
        assert result.state.sandbox_plans == ()
        _assert_no_actions(result)


def test_d1b_executable_plan_content_fails_closed():
    cases = [
        {"success_criteria": ("run powershell command",)},
        {"repository_snapshot_description": "git clone https://example.invalid/repo"},
        {"rollback_proof_requirements": ("diff --git a/x b/x",)},
        {"cleanup_proof_requirements": ("write this file into the repo",)},
        {"execution_budget_metadata": ("{\"command\": \"pytest\"}",)},
        {"repository_snapshot_description": "attach_module would load a runtime module"},
    ]

    for overrides in cases:
        result = _create_plan(**overrides)
        assert result.accepted is False
        assert result.reason == "executable_plan_content_prohibited"
        assert result.state.sandbox_plans == ()
        _assert_no_actions(result)


def test_d1b_valid_module_attachment_plan_is_attachment_only_and_inert():
    result = _create_plan(module_attachment=_module_kwargs())

    assert result.accepted is True
    assert result.module_attachment_plan is not None
    assert result.sandbox_plan is not None
    module_plan = result.module_attachment_plan
    assert module_plan.attachment_only_status == "ATTACHMENT_PLAN_ONLY"
    assert module_plan.live_activation_prohibited is True
    assert module_plan.permissions_granted is False
    assert module_plan.module_loaded is False
    assert module_plan.registry_mutated is False
    assert result.state.attachment_plan_ids_by_sandbox_plan[result.sandbox_plan.plan_id] == (module_plan.attachment_plan_id,)
    _assert_no_actions(result)


def test_d1b_invalid_module_attachment_plan_fails_closed():
    cases = [
        ("module_permission_overlap", {"requested_permissions": ("provider_call",)}),
        ("rollback_or_removal_description_required", {"rollback_or_removal_description": ""}),
        ("validation_requirements_required", {"validation_requirements": ()}),
        ("module_type_not_allowed", {"module_type": "live_kernel"}),
        ("executable_module_attachment_content_prohibited", {"lifecycle_hooks_described": ("importlib loads the module",)}),
    ]

    for reason, overrides in cases:
        result = _create_plan(module_attachment=_module_kwargs(**overrides))
        assert result.accepted is False
        assert result.reason == reason
        assert result.state.module_attachment_plans == ()
        _assert_no_actions(result)


def test_d1b_sandbox_and_attachment_plans_survive_serialization_without_activation():
    result = _create_plan(module_attachment=_module_kwargs())
    assert result.sandbox_plan is not None
    assert result.module_attachment_plan is not None

    restored_state = gsr.deserialize(gsr.SandboxPlanningState, json.loads(json.dumps(gsr.serialize(result.state))))
    restored_plan = gsr.deserialize(gsr.SandboxEvaluationPlan, restored_state.sandbox_plans[0])
    restored_module = gsr.deserialize(gsr.ModuleAttachmentPlan, restored_state.module_attachment_plans[0])

    assert restored_plan.plan_only_status == "PLAN_ONLY"
    assert restored_plan.workspace_creation_prohibited is True
    assert restored_plan.sandbox_execution_prohibited is True
    assert restored_plan.module_loading_prohibited is True
    assert restored_module.attachment_only_status == "ATTACHMENT_PLAN_ONLY"
    assert restored_module.permissions_granted is False
    assert restored_module.module_loaded is False
    assert restored_module.registry_mutated is False
    assert restored_state.future_sandbox_execution_eligible_plans == ()
