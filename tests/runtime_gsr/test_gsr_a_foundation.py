from __future__ import annotations

import json

from orchestration.runtime import gsr_a_governed_self_regulation as gsr
from orchestration.runtime.delta_1_0_objective_engine import propose_objective, transition_objective
from orchestration.runtime.rc4_governed_action_runtime import make_permission_grant, make_scope
from orchestration.runtime.rc5_developmental_cognition import build_purpose_constitution


def _objects():
    objective = gsr.make_development_objective("Observe and propose only.", sequence=1)
    observation = gsr.make_observation(
        objective.objective_id,
        source_subsystem="test",
        observed_behavior="observed",
        expected_behavior="expected",
        evidence_references=("test://evidence",),
    )
    diagnosis = gsr.make_diagnosis_candidate(
        (observation,),
        first_incorrect_transition="first wrong branch",
        suspected_mechanism="bounded mechanism",
    )
    proposal = gsr.make_repair_proposal(
        diagnosis,
        proposed_change="bounded inert proposal",
        files_or_components_in_scope=("orchestration/runtime/example.py",),
        forbidden_files_or_components=("DELTA.py", "live_router"),
        validation_plan=("py_compile", "focused_tests"),
    )
    sandbox = gsr.make_sandbox_plan(proposal)
    return objective, observation, diagnosis, proposal, sandbox


def test_development_objective_cannot_become_active_without_operator_authorization():
    objective, *_ = _objects()

    assert gsr.can_activate_objective(objective) is False
    self_decision = gsr.make_governance_decision(
        objective.objective_id,
        decision="approve",
        allowed_scope=("objective_activation",),
        operator_authority="DELTA_GENERATED",
        sequence=objective.sequence,
    )
    assert gsr.can_activate_objective(objective, self_decision) is False
    operator_decision = gsr.make_governance_decision(
        objective.objective_id,
        decision="approve",
        allowed_scope=("objective_activation",),
        sequence=objective.sequence,
    )
    assert gsr.can_activate_objective(objective, operator_decision) is True


def test_observation_is_inert_and_does_not_auto_create_diagnosis():
    _, observation, *_ = _objects()

    assert gsr.observation_mutates_state(observation) is False
    assert gsr.observation_auto_diagnoses(observation) is False
    assert all(value is False for value in observation.safety.values())


def test_diagnosis_and_repair_proposal_cannot_self_authorize_or_apply():
    _, _, diagnosis, proposal, _ = _objects()

    assert diagnosis.provisional is True
    assert gsr.diagnosis_authorizes_proposal(diagnosis) is False
    assert proposal.proposal_only_status == "PROPOSAL_ONLY"
    assert gsr.proposal_can_apply_itself(proposal) is False


def test_sandbox_evaluation_requires_explicit_scoped_governance_decision():
    _, _, _, proposal, sandbox = _objects()

    assert gsr.can_begin_sandbox(sandbox, None, sequence=1) is False
    wrong_scope = gsr.make_governance_decision(proposal.proposal_id, decision="approve", allowed_scope=("application",), sequence=1)
    assert gsr.can_begin_sandbox(sandbox, wrong_scope, sequence=1) is False
    sandbox_decision = gsr.make_governance_decision(proposal.proposal_id, decision="approve", allowed_scope=("sandbox_evaluation",), sequence=1)
    assert gsr.can_begin_sandbox(sandbox, sandbox_decision, sequence=1) is True


def test_sandbox_approval_does_not_imply_application_approval():
    _, _, _, proposal, sandbox = _objects()
    sandbox_decision = gsr.make_governance_decision(proposal.proposal_id, decision="approve", allowed_scope=("sandbox_evaluation",), sequence=1)

    assert gsr.can_begin_sandbox(sandbox, sandbox_decision, sequence=1) is True
    assert gsr.can_apply_proposal(proposal, sandbox_decision, sequence=1) is False


def test_application_authorization_is_scoped_one_shot_and_expiring():
    _, _, _, proposal, _ = _objects()
    application = gsr.make_governance_decision(
        proposal.proposal_id,
        decision="approve",
        allowed_scope=("application",),
        sequence=1,
        expires_after_sequence=1,
    )
    consumed = gsr.GovernanceDecision(**{**gsr.serialize(application), "consumed": True})

    assert gsr.can_apply_proposal(proposal, application, sequence=1) is True
    assert gsr.can_apply_proposal(proposal, application, sequence=2) is False
    assert gsr.can_apply_proposal(proposal, consumed, sequence=1) is False


def test_rejected_suspended_rolled_back_and_deeper_design_states_deny_execution():
    objective, *_ = _objects()

    for state_name in ("rejected", "suspended", "rolled_back", "deeper_design_required"):
        state = gsr.RegulationCycleState("cycle", objective.objective_id, state_name, 1, deeper_design_required=state_name == "deeper_design_required")
        assert gsr.execution_allowed_for_state(state) is False


def test_deeper_design_classification_prevents_automatic_repair_continuation():
    objective, *_ = _objects()
    state = gsr.RegulationCycleState("cycle", objective.objective_id, "diagnosis_review", 1, deeper_design_required=True)

    result = gsr.transition_cycle(state, "proposal_drafting")

    assert result.accepted is False
    assert result.reason == "deeper_design_required_blocks_continuation"


def test_no_delta_generated_object_counts_as_operator_approval():
    _, _, _, proposal, sandbox = _objects()
    delta_decision = gsr.make_governance_decision(
        proposal.proposal_id,
        decision="approve",
        allowed_scope=("sandbox_evaluation", "application"),
        operator_authority="DELTA_SELF_AUTHORITY",
        sequence=1,
    )

    assert gsr.can_begin_sandbox(sandbox, delta_decision, sequence=1) is False
    assert gsr.can_apply_proposal(proposal, delta_decision, sequence=1) is False


def test_serialization_and_deserialization_preserve_governance_state():
    objective, observation, diagnosis, proposal, sandbox = _objects()
    decision = gsr.make_governance_decision(proposal.proposal_id, decision="approve", allowed_scope=("sandbox_evaluation",), sequence=1)

    for item in (objective, observation, diagnosis, proposal, sandbox, decision):
        restored = gsr.deserialize(type(item), json.loads(json.dumps(gsr.serialize(item))))
        assert restored == item


def test_invalid_lifecycle_transitions_fail_closed():
    objective, *_ = _objects()
    state = gsr.initial_cycle(objective)

    result = gsr.transition_cycle(state, "applying")

    assert result.accepted is False
    assert result.execution_allowed is False
    assert result.state == state


def test_valid_sandbox_and_application_transitions_require_distinct_decisions():
    objective, _, _, proposal, _ = _objects()
    state = gsr.RegulationCycleState("cycle", objective.objective_id, "proposal_review", 1, proposal_ids=(proposal.proposal_id,))
    sandbox_decision = gsr.make_governance_decision(proposal.proposal_id, decision="approve", allowed_scope=("sandbox_evaluation",), sequence=1)
    application_decision = gsr.make_governance_decision(proposal.proposal_id, decision="approve", allowed_scope=("application",), sequence=2)

    sandbox = gsr.transition_cycle(state, "sandbox_authorized", decision=sandbox_decision, proposal_id=proposal.proposal_id)
    assert sandbox.accepted is True
    evaluated = gsr.transition_cycle(gsr.transition_cycle(sandbox.state, "sandbox_evaluating").state, "evaluation_review")
    application = gsr.transition_cycle(evaluated.state, "application_authorized", decision=application_decision, proposal_id=proposal.proposal_id)
    assert application.accepted is True


def test_existing_rc3_rc4_rc5_governance_boundaries_remain_unchanged():
    delta_objective = propose_objective("Keep objective proposal-only.", objective_type="GOVERNANCE_HARDENING", origin="OPERATOR_CREATED")
    unchanged, reason = transition_objective(delta_objective, "APPROVED", operator_approved=False)
    grant = make_permission_grant(make_scope(), seconds=-1)
    purpose = build_purpose_constitution()

    assert unchanged.state == "PROPOSED"
    assert reason == "invalid_transition"
    assert grant.revoked is False
    assert purpose.version.change_authority == "operator_only"


def test_report_and_safety_are_inert():
    report = gsr.build_gsr_a_foundation_report()

    assert report["live_runtime_integration_performed"] is False
    assert all(value is False for value in report["safety"].values())
    assert report["status"] == "INERT_GOVERNED_SCAFFOLD"
