from orchestration.runtime.delta_1_0_learning_loop import (
    assess_capability,
    create_learning_loop,
    dispose_lesson,
    evaluate_practice,
    prepare_practice,
    propose_lesson,
)
from orchestration.runtime.delta_1_0_module_framework import (
    ModuleCallRequest,
    attach_module,
    evaluate_module_call,
    python_module_manifest,
    register_module,
)
from orchestration.runtime.delta_1_0_objective_engine import (
    detect_capability_gap,
    propose_objective,
    transition_objective,
)


def test_objective_requires_operator_approval_for_active_state():
    objective = propose_objective("Improve routing", objective_type="CAPABILITY_IMPROVEMENT", origin="OPERATOR_CREATED")
    updated, reason = transition_objective(objective, "APPROVED", operator_approved=False)
    assert updated.state == "PROPOSED"
    assert reason == "invalid_transition"
    updated, _ = transition_objective(objective, "AWAITING_OPERATOR_APPROVAL")
    approved, reason = transition_objective(updated, "APPROVED", operator_approved=True)
    assert reason == "transition_accepted"
    assert approved.operator_approved is True


def test_gap_detection_produces_proposal_only_objective():
    gap = detect_capability_gap("missing rollback evidence", "RC4", ("pilot-1",))
    assert gap.proposal_only is True
    assert gap.proposed_objective.state == "PROPOSED"


def test_module_attachment_rejects_prohibited_permissions():
    entry = register_module(python_module_manifest())
    attached = attach_module(entry, operator_approved=True)
    decision = evaluate_module_call(
        attached,
        ModuleCallRequest(
            module_id="PYTHON_CODING_MODULE_V1",
            requested_permission="automatic_push",
            input_type="approved_repo_root",
            output_type="patch_proposal",
            operator_approved=True,
            payload_summary="push from runtime",
        ),
        session_permissions=("repo_read", "proposal_prepare"),
    )
    assert decision.allowed is False
    assert "prohibited_permission_requested" in decision.reasons


def test_learning_loop_lesson_requires_operator_for_noncanonical_approval():
    objective = propose_objective("Improve Python analysis", objective_type="CAPABILITY_IMPROVEMENT", origin="OPERATOR_CREATED")
    objective, _ = transition_objective(objective, "AWAITING_OPERATOR_APPROVAL")
    objective, _ = transition_objective(objective, "APPROVED", operator_approved=True)
    loop = create_learning_loop(objective, "PYTHON_CODING_MODULE_V1")
    loop = assess_capability(loop, baseline_score=0.7, gaps=("failure_mapping",), evidence_refs=("e1",))
    loop = prepare_practice(loop, "classify failure", "classification only")
    loop = evaluate_practice(loop, score=0.9, evidence_refs=("e2",))
    loop = propose_lesson(loop, "failure mapping improved", ("e2",))
    unchanged = dispose_lesson(loop, "APPROVED_NONCANONICAL", operator_approved=False)
    assert unchanged.lesson_candidate.status == "PROPOSED"
    approved = dispose_lesson(loop, "APPROVED_NONCANONICAL", operator_approved=True)
    assert approved.lesson_candidate.status == "APPROVED_NONCANONICAL"
