from __future__ import annotations

from orchestration.runtime import gsr_a_governed_self_regulation as gsr
from tests.runtime_gsr.test_gsr_c_diagnosis_review import _state_with_two_hypotheses


def _accepted_state():
    state, diagnosis, _, first, _ = _state_with_two_hypotheses()
    decision = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="accepted_for_proposal_drafting",
        selected_hypothesis_id=first.hypothesis_id,
        rationale="operator accepts diagnosis for proposal drafting only",
        allowed_next_transition="proposal_drafting",
        decision_sequence=100,
    )
    reviewed = gsr.review_diagnosis_candidate(state, decision, sequence=100)
    assert reviewed.diagnosis is not None
    return reviewed.state, reviewed.diagnosis, first


def _proposal_kwargs(**overrides):
    base = {
        "proposal_title": "Bound pending-consent recall before ordinary discourse",
        "proposed_mechanism_level_change": "Separate pending approval handling from discourse-history recall before repair is considered.",
        "problem_statement": "A pending local-model consent prompt can obscure a later request to recall the prior topic.",
        "files_or_components_in_scope": ("DELTA.py",),
        "forbidden_files_or_components": ("provider_runtime", "sandbox_execution", "rc4_execution"),
        "predicted_effects": ("ordinary discourse recall remains available while consent is pending",),
        "expected_user_visible_effects": ("what were we discussing before that recalls the prior topic",),
        "regression_risks": ("approval prompt routing could become too permissive",),
        "governance_risks": ("operator approval paths must remain explicit",),
        "safety_risks": ("local model execution must remain approval-gated",),
        "alternatives_considered": ("change concept retrieval ranking", "alter local-model provider state"),
        "reasons_alternatives_rejected": ("retrieval ranking is not the first incorrect transition", "provider state is outside the bounded mechanism"),
        "rollback_description": "Discard the candidate change and restore prior pending-consent routing behavior.",
        "validation_plan": ("focused pending-consent recall tests", "GSR regressions"),
        "focused_test_requirements": ("pending consent recall", "ordinary approval still works"),
        "adjacent_test_requirements": ("conversation topic state",),
        "live_runtime_evidence_requirements": ("controlled operator pilot transcript",),
        "full_suite_policy": "not required before proposal review",
        "provider_model_restrictions": ("no provider calls", "no local model inference"),
        "memory_write_restrictions": ("no canonical writes", "no noncanonical writes"),
        "creation_sequence": 101,
    }
    base.update(overrides)
    return base


def _create(state, diagnosis, **overrides):
    return gsr.create_proposal_only_repair_proposal(
        state,
        diagnosis.diagnosis_id,
        **_proposal_kwargs(**overrides),
    )


def test_c1_pending_and_blocked_diagnoses_cannot_create_proposal():
    state, diagnosis, _, _, _ = _state_with_two_hypotheses()
    pending = _create(state, diagnosis)

    assert pending.accepted is False
    assert pending.reason == "diagnosis_not_accepted_for_proposal_drafting"

    blocked = (
        ("rejected", "diagnosis_rejected_blocks_proposal"),
        ("competing_hypothesis_unresolved", "diagnosis_unresolved_blocks_proposal"),
        ("non_defect", "diagnosis_non_defect_blocks_proposal"),
        ("insufficient_evidence", "diagnosis_insufficient_evidence_blocks_proposal"),
        ("suspended", "diagnosis_suspended_blocks_proposal"),
        ("expired", "diagnosis_expired_blocks_proposal"),
        ("duplicate_diagnosis", "diagnosis_duplicate_blocks_proposal"),
        ("deeper_design_required", "diagnosis_deeper_design_blocks_proposal"),
    )
    for disposition, reason in blocked:
        state, diagnosis, _, first, _ = _state_with_two_hypotheses()
        decision = gsr.make_diagnosis_review_decision(
            diagnosis.diagnosis_id,
            disposition=disposition,
            selected_hypothesis_id=first.hypothesis_id,
            rationale=f"operator marks {disposition}",
            allowed_next_transition=disposition,
            decision_sequence=100,
        )
        reviewed = gsr.review_diagnosis_candidate(state, decision, sequence=100)
        result = _create(reviewed.state, reviewed.diagnosis)
        assert result.accepted is False
        assert result.reason == reason


def test_c1_accepted_diagnosis_creates_one_proposal_only_artifact():
    state, diagnosis, hypothesis = _accepted_state()

    result = _create(state, diagnosis, linked_selected_hypothesis_id=hypothesis.hypothesis_id)

    assert result.accepted is True
    assert result.proposal is not None
    assert result.proposal.diagnosis_id == diagnosis.diagnosis_id
    assert result.proposal.proposal_only_status == "PROPOSAL_ONLY"
    assert result.proposal.operator_review_status == "pending_review"
    assert result.proposal.linked_selected_hypothesis_id == hypothesis.hypothesis_id
    assert result.proposal.proposal_id in result.state.pending_proposal_review_queue
    assert len(result.state.repair_proposals) == 1
    assert result.creates_patch is False
    assert result.creates_sandbox_authorization is False
    assert result.starts_sandbox is False
    assert result.mutates_source is False
    assert result.authorizes_application is False
    assert result.performs_application is False
    assert result.performs_persistence is False
    assert result.provider_calls_performed is False
    assert result.model_inference_performed is False
    assert result.memory_write_performed is False


def test_c1_selected_foreign_hypothesis_and_forbidden_scope_fail_closed():
    state, diagnosis, _ = _accepted_state()

    foreign = _create(state, diagnosis, linked_selected_hypothesis_id="foreign-hypothesis")
    overlap = _create(
        state,
        diagnosis,
        files_or_components_in_scope=("DELTA.py", "provider_runtime"),
        forbidden_files_or_components=("provider_runtime",),
    )

    assert foreign.accepted is False
    assert foreign.reason == "selected_hypothesis_not_in_diagnosis"
    assert overlap.accepted is False
    assert overlap.reason == "scope_overlaps_forbidden_components"


def test_c1_missing_required_review_metadata_fails_closed():
    state, diagnosis, _ = _accepted_state()

    no_rollback = _create(state, diagnosis, rollback_description="")
    no_validation = _create(state, diagnosis, validation_plan=())
    no_provider_restrictions = _create(state, diagnosis, provider_model_restrictions=())
    no_memory_restrictions = _create(state, diagnosis, memory_write_restrictions=())

    assert no_rollback.reason == "rollback_description_required"
    assert no_validation.reason == "validation_plan_required"
    assert no_provider_restrictions.reason == "provider_model_restrictions_required"
    assert no_memory_restrictions.reason == "memory_write_restrictions_required"


def test_c1_executable_patch_or_command_content_fails_closed():
    state, diagnosis, _ = _accepted_state()

    patch = _create(state, diagnosis, proposed_mechanism_level_change="diff --git a/file b/file")
    command = _create(state, diagnosis, validation_plan=("pytest tests/runtime_gsr",))

    assert patch.accepted is False
    assert patch.reason == "executable_content_prohibited"
    assert command.accepted is False
    assert command.reason == "executable_content_prohibited"


def test_c1_proposal_contains_no_patch_execution_or_mutation_capability():
    state, diagnosis, _ = _accepted_state()

    result = _create(state, diagnosis)

    assert result.proposal is not None
    assert not hasattr(result.proposal, "patch")
    assert not hasattr(result.proposal, "unified_diff")
    assert gsr.proposal_contains_patch_or_executable_content(result.proposal) is False
    assert gsr.proposal_mutates_source(result.proposal) is False
    assert gsr.proposal_starts_sandbox(result.proposal) is False
    assert gsr.proposal_authorizes_application(result.proposal) is False


def _proposal_state():
    state, diagnosis, _ = _accepted_state()
    result = _create(state, diagnosis)
    assert result.proposal is not None
    return result.state, result.proposal


def test_c2_proposal_remains_pending_without_review_and_cannot_self_review():
    state, proposal = _proposal_state()
    self_decision = gsr.make_proposal_review_decision(
        proposal.proposal_id,
        disposition="revise",
        rationale="proposal cannot review itself",
        allowed_scope=("proposal_review",),
        operator_authority=proposal.proposal_id,
        decision_sequence=120,
    )

    result = gsr.review_repair_proposal(state, self_decision, sequence=120)

    assert proposal.proposal_id in state.pending_proposal_review_queue
    assert gsr.proposal_can_review_itself(proposal) is False
    assert result.accepted is False
    assert result.reason == "operator_authority_required"
    assert self_decision.decision_id not in result.state.consumed_proposal_decision_ids


def test_c2_non_operator_wrong_target_expired_and_consumed_decisions_fail():
    state, proposal = _proposal_state()
    cases = (
        (gsr.make_proposal_review_decision(proposal.proposal_id, disposition="reject", rationale="bad auth", allowed_scope=("proposal_review",), operator_authority="DELTA_GENERATED", decision_sequence=120), "operator_authority_required"),
        (gsr.make_proposal_review_decision("missing-proposal", disposition="reject", rationale="wrong target", allowed_scope=("proposal_review",), decision_sequence=121), "proposal_not_found"),
        (gsr.make_proposal_review_decision(proposal.proposal_id, disposition="reject", rationale="expired", allowed_scope=("proposal_review",), decision_sequence=122, expires_after_sequence=121), "proposal_review_decision_expired"),
        (gsr.make_proposal_review_decision(proposal.proposal_id, disposition="reject", rationale="consumed", allowed_scope=("proposal_review",), decision_sequence=123, consumed=True), "proposal_review_decision_consumed"),
    )
    for decision, reason in cases:
        result = gsr.review_repair_proposal(state, decision, sequence=123)
        assert result.accepted is False
        assert result.reason == reason
        assert decision.decision_id not in result.state.consumed_proposal_decision_ids


def test_c2_successful_one_shot_decision_is_consumed_and_reuse_fails():
    state, proposal = _proposal_state()
    decision = gsr.make_proposal_review_decision(
        proposal.proposal_id,
        disposition="revise",
        rationale="operator requests revision",
        allowed_scope=("proposal_review",),
        decision_sequence=120,
    )

    first = gsr.review_repair_proposal(state, decision, sequence=120)
    second = gsr.review_repair_proposal(first.state, decision, sequence=121)

    assert first.accepted is True
    assert first.proposal is not None
    assert first.proposal.operator_review_status == "revise"
    assert decision.decision_id in first.state.consumed_proposal_decision_ids
    assert second.accepted is False
    assert second.reason == "proposal_review_decision_already_consumed"


def test_c2_blocking_review_dispositions_enter_denial_indexes():
    indexes = {
        "reject": "rejected_proposals",
        "revise": "revision_required_proposals",
        "defer": "deferred_proposals",
        "deeper_design_required": "deeper_design_proposals",
        "suspend": "suspended_proposals",
        "expire": "expired_proposals",
    }
    for disposition, index_name in indexes.items():
        state, proposal = _proposal_state()
        decision = gsr.make_proposal_review_decision(
            proposal.proposal_id,
            disposition=disposition,
            rationale=f"operator marks {disposition}",
            allowed_scope=("proposal_review",),
            decision_sequence=120,
        )
        result = gsr.review_repair_proposal(state, decision, sequence=120)
        assert result.accepted is True
        assert proposal.proposal_id in getattr(result.state, index_name)
        assert proposal.proposal_id not in result.state.future_sandbox_planning_eligible_proposals
        assert result.sandbox_authorization_created is False
        assert result.patch_created is False


def test_c2_serialization_preserves_denial_state_and_consumed_decision_id():
    import json

    state, proposal = _proposal_state()
    decision = gsr.make_proposal_review_decision(
        proposal.proposal_id,
        disposition="reject",
        rationale="operator rejects proposal",
        allowed_scope=("proposal_review",),
        decision_sequence=120,
    )
    reviewed = gsr.review_repair_proposal(state, decision, sequence=120)
    restored = gsr.deserialize(gsr.DiagnosisProposalState, json.loads(json.dumps(gsr.serialize(reviewed.state))))
    repeat = gsr.review_repair_proposal(restored, decision, sequence=121)

    assert proposal.proposal_id in restored.rejected_proposals
    assert decision.decision_id in restored.consumed_proposal_decision_ids
    assert repeat.accepted is False
    assert repeat.reason == "proposal_review_decision_already_consumed"


def test_c3_valid_operator_approval_adds_only_future_sandbox_planning_eligibility():
    state, proposal = _proposal_state()
    decision = gsr.make_proposal_review_decision(
        proposal.proposal_id,
        disposition="approve_for_future_sandbox_planning",
        rationale="operator approves only future sandbox planning eligibility",
        allowed_scope=("future_sandbox_planning",),
        forbidden_scope=("sandbox_authorization", "patch_generation", "source_mutation", "application"),
        decision_sequence=140,
    )

    result = gsr.review_repair_proposal(state, decision, sequence=140)

    assert result.accepted is True
    assert result.future_sandbox_planning_eligible is True
    assert proposal.proposal_id in result.state.future_sandbox_planning_eligible_proposals
    assert result.sandbox_authorization_created is False
    assert result.sandbox_started is False
    assert result.patch_created is False
    assert result.source_mutated is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert result.persistence_performed is False
    assert result.proposal is not None
    assert result.proposal.proposal_only_status == "PROPOSAL_ONLY"


def test_c3_eligibility_survives_serialization_without_reactivating_decision():
    import json

    state, proposal = _proposal_state()
    decision = gsr.make_proposal_review_decision(
        proposal.proposal_id,
        disposition="approve_for_future_sandbox_planning",
        rationale="operator approves only future sandbox planning eligibility",
        allowed_scope=("future_sandbox_planning",),
        decision_sequence=140,
    )
    reviewed = gsr.review_repair_proposal(state, decision, sequence=140)
    restored = gsr.deserialize(gsr.DiagnosisProposalState, json.loads(json.dumps(gsr.serialize(reviewed.state))))
    repeat = gsr.review_repair_proposal(restored, decision, sequence=141)

    assert proposal.proposal_id in restored.future_sandbox_planning_eligible_proposals
    assert decision.decision_id in restored.consumed_proposal_decision_ids
    assert repeat.accepted is False
    assert repeat.reason == "proposal_review_decision_already_consumed"


def test_c3_no_execution_provider_memory_or_scheduler_activity_occurs():
    state, proposal = _proposal_state()
    decision = gsr.make_proposal_review_decision(
        proposal.proposal_id,
        disposition="approve_for_future_sandbox_planning",
        rationale="future planning eligibility only",
        allowed_scope=("future_sandbox_planning",),
        decision_sequence=140,
    )

    result = gsr.review_repair_proposal(state, decision, sequence=140)

    assert result.accepted is True
    assert result.sandbox_authorization_created is False
    assert result.sandbox_started is False
    assert result.patch_created is False
    assert result.source_mutated is False
    assert result.application_authorized is False
    assert result.application_performed is False
    assert result.persistence_performed is False
    assert all(value is False for value in result.state.safety.values())


def test_c3_rc4_execution_helpers_are_not_required_for_gate_c():
    import sys

    before = set(sys.modules)
    state, proposal = _proposal_state()
    decision = gsr.make_proposal_review_decision(
        proposal.proposal_id,
        disposition="approve_for_future_sandbox_planning",
        rationale="future planning eligibility only",
        allowed_scope=("future_sandbox_planning",),
        decision_sequence=140,
    )
    result = gsr.review_repair_proposal(state, decision, sequence=140)
    after = set(sys.modules)

    assert result.accepted is True
    assert "orchestration.runtime.rc4_governed_action_runtime" not in after - before
