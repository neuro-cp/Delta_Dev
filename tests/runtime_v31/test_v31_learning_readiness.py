from orchestration.runtime.v31_cognitive_timeline import build_cognitive_timeline
from orchestration.runtime.v31_contradiction_aggregation import aggregate_contradictions, sample_contradiction_observations
from orchestration.runtime.v31_gated_integration import (
    EXACT_ADMIN_APPROVAL_PREFIX,
    build_gated_integration_report,
    build_local_overwatch_result,
    build_owner_override,
    evaluate_gated_integration,
    parse_admin_approval,
)
from orchestration.runtime.v31_learning_explainability import explain_learning_proposal
from orchestration.runtime.v31_learning_opportunity import detect_learning_opportunities
from orchestration.runtime.v31_learning_proposal import build_learning_proposals
from orchestration.runtime.v31_local_learning_answer import is_v31_learning_question, run_v31_learning_answer
from orchestration.runtime.v31_safety_checkpoint import build_v31_safety_checkpoint


def test_v31_detects_learning_opportunity_without_learning():
    opportunities = detect_learning_opportunities("What should DELTA learn from this interaction?")
    assert opportunities
    assert opportunities[0].requires_review is True
    assert opportunities[0].eligible_for_learning is False


def test_v31_proposal_admin_approval_is_not_automatic_integration():
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    assert proposal.review_status == "admin_approved"
    assert proposal.eligible_for_gated_integration is True
    assert proposal.integrated is False


def test_v31_gated_integration_blocks_without_overwatch_or_override():
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    approval = parse_admin_approval(
        f"{EXACT_ADMIN_APPROVAL_PREFIX}\nproposal_id={proposal.proposal_id}\napproved_by=admin\napproval_scope=single_learning_proposal_only",
        proposal.proposal_id,
    )
    event = evaluate_gated_integration(proposal, approval, build_local_overwatch_result(proposal, allow=False))
    assert approval.valid is True
    assert event.allowed is False
    assert event.write_performed is False


def test_v31_owner_override_can_allow_event_but_still_no_live_write():
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    approval = parse_admin_approval(
        f"{EXACT_ADMIN_APPROVAL_PREFIX}\nproposal_id={proposal.proposal_id}\napproved_by=admin\napproval_scope=single_learning_proposal_only",
        proposal.proposal_id,
    )
    event = evaluate_gated_integration(
        proposal,
        approval,
        build_local_overwatch_result(proposal, allow=False),
        build_owner_override(proposal.proposal_id, reason="owner single-trial override"),
    )
    assert event.allowed is True
    assert event.override_status == "owner_override_allowed"
    assert event.write_performed is False
    assert event.rollback_token


def test_v31_cognitive_timeline_stops_at_gate_scaffold():
    timeline = build_cognitive_timeline()
    assert timeline["stops_at"] == "gated_integration_event_scaffold"
    assert timeline["integration_active"] is False


def test_v31_contradiction_aggregation_does_not_resolve():
    bundles = aggregate_contradictions(sample_contradiction_observations())
    assert bundles
    assert all(bundle.resolved is False for bundle in bundles)


def test_v31_explainability_reports_gate_blockers():
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="review")[0]
    explanation = explain_learning_proposal(proposal)
    assert "admin_approval_or_gate_missing" in explanation["why_blocked"]
    assert explanation["integrated"] is False


def test_v31_local_learning_answers_are_safe():
    assert is_v31_learning_question("What should DELTA learn from this interaction?")
    data = run_v31_learning_answer("Approve this learning proposal.")
    assert data["phase"] == "Runtime V3.1"
    assert data["safety"]["integration_write_performed"] is False
    assert data["safety"]["training_performed"] is False
    assert data["safety"]["provider_call_performed"] is False


def test_v31_gated_integration_report_is_scaffold_only():
    data = build_gated_integration_report()
    assert data["live_write_performed"] is False
    assert data["training_performed"] is False
    assert data["blocked_without_override"]["allowed"] is False
    assert data["allowed_with_owner_override"]["allowed"] is True
    assert data["allowed_with_owner_override"]["write_performed"] is False


def test_v31_safety_checkpoint_preserves_invariants():
    data = build_v31_safety_checkpoint()
    assert data["learning_performed"] is False
    assert data["integration_performed"] is False
    assert data["memory_mutation_performed"] is False
    assert data["provider_call_performed"] is False
    assert data["model_b_default"] == "unchanged"
