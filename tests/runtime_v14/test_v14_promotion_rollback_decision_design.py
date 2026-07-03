from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_promotion_rollback import (
    RUNTIME_V14V_INVARIANT_FLAGS,
    PromotionCandidateType,
    PromotionDecisionOutcome,
    PromotionSafetyStatus,
    RollbackDecisionOutcome,
    RuntimeDefaultChangeBlockerType,
    create_promotion_candidate,
    create_promotion_decision,
    create_promotion_evidence_packet,
    create_promotion_human_review_requirement,
    create_promotion_rollback_audit_record,
    create_promotion_rollback_report_entry,
    create_promotion_rollback_plan,
    create_promotion_safety_gate,
    create_rollback_decision,
    create_runtime_default_change_blocker,
    validate_audit_record_review_only,
    validate_default_blocker_unresolved,
    validate_evidence_packet_review_only,
    validate_human_review_unsatisfied,
    validate_promotion_candidate_inert,
    validate_promotion_decision_inert,
    validate_report_entry_review_only,
    validate_rollback_decision_inert,
    validate_rollback_plan_inert,
    validate_safety_gate_closed,
)
from orchestration.runtime.v14_promotion_rollback_report import build_promotion_rollback_report_data, write_promotion_rollback_report


def _parts():
    candidate = create_promotion_candidate(
        candidate_name="HYB1",
        candidate_type=PromotionCandidateType.HYB1_RUNTIME_VARIANT,
        baseline_reference_id="runtime-v13-model-b",
        comparison_reference_ids=("comparison",),
        evidence_reference_ids=("evidence",),
        safety_reference_ids=("safety",),
        rollback_reference_ids=("rollback",),
    )
    evidence = create_promotion_evidence_packet(
        candidate=candidate,
        comparison_summary="comparison",
        improvement_summary="improved",
        regression_summary="unresolved",
        safety_summary="safe for review",
        uncertainty_summary="not authority",
        sufficient_for_review=True,
    )
    gate = create_promotion_safety_gate(
        candidate=candidate,
        required_reviews=("human",),
        invariant_failures=(),
        unresolved_regressions=("unknown",),
        missing_requirements=("human",),
        safety_status=PromotionSafetyStatus.HUMAN_REVIEW_REQUIRED,
    )
    review = create_promotion_human_review_requirement(candidate=candidate, required_actor="human", review_reason="promotion")
    rollback_plan = create_promotion_rollback_plan(
        candidate=candidate,
        rollback_strategy="restore Model B",
        rollback_trigger_conditions=("regression",),
    )
    promotion_decision = create_promotion_decision(
        candidate=candidate,
        outcome=PromotionDecisionOutcome.ELIGIBLE_FOR_FUTURE_GATED_TRIAL_DESIGN,
        rationale="review only",
        invariant_status="all false",
    )
    rollback_decision = create_rollback_decision(
        candidate=candidate,
        rollback_plan=rollback_plan,
        outcome=RollbackDecisionOutcome.ROLLBACK_DESIGN_ONLY,
        rationale="not active",
    )
    blocker = create_runtime_default_change_blocker(
        candidate=candidate,
        blocker_type=RuntimeDefaultChangeBlockerType.CANDIDATE_STILL_DORMANT,
        rationale="still dormant",
        required_resolution="future review",
    )
    audit = create_promotion_rollback_audit_record(
        candidate=candidate,
        blocker_ids=(blocker.blocker_id,),
        audit_summary="review only",
        decision=promotion_decision,
        rollback_decision=rollback_decision,
        evidence_packet=evidence,
        safety_gate=gate,
    )
    entry = create_promotion_rollback_report_entry(
        candidate=candidate,
        evidence_summary="evidence",
        safety_summary="closed",
        human_review_summary="missing",
        rollback_summary="not executed",
        blocker_summary="blocked",
        promotion_decision_summary="future trial design",
        rollback_decision_summary="design only",
        unresolved_gaps=("human",),
        recommended_next_review_step="closure",
    )
    return candidate, evidence, gate, review, rollback_plan, promotion_decision, rollback_decision, blocker, audit, entry


def test_importing_promotion_rollback_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V14V_INVARIANT_FLAGS["hyb1_remains_dormant"] is True
    assert all(value is False for key, value in RUNTIME_V14V_INVARIANT_FLAGS.items() if key != "hyb1_remains_dormant")


def test_hyb1_candidate_is_inactive_unpromoted_and_not_default():
    candidate, *_ = _parts()
    duplicate = create_promotion_candidate(
        candidate_name="HYB1",
        candidate_type=PromotionCandidateType.HYB1_RUNTIME_VARIANT,
        baseline_reference_id="runtime-v13-model-b",
        comparison_reference_ids=("comparison",),
        evidence_reference_ids=("evidence",),
        safety_reference_ids=("safety",),
        rollback_reference_ids=("rollback",),
    )
    assert candidate.candidate_id == duplicate.candidate_id
    assert candidate.candidate_type == PromotionCandidateType.HYB1_RUNTIME_VARIANT
    assert candidate.baseline_reference_id == "runtime-v13-model-b"
    assert validate_promotion_candidate_inert(candidate)


def test_evidence_gate_review_and_rollback_are_not_authority_or_execution():
    _, evidence, gate, review, rollback_plan, *_ = _parts()
    assert evidence.sufficient_for_review is True
    assert validate_evidence_packet_review_only(evidence)
    assert validate_safety_gate_closed(gate)
    assert validate_human_review_unsatisfied(review)
    assert validate_rollback_plan_inert(rollback_plan)


def test_promotion_and_rollback_decisions_are_not_applied():
    *_, promotion_decision, rollback_decision, blocker, audit, entry = _parts()
    assert validate_promotion_decision_inert(promotion_decision)
    assert validate_rollback_decision_inert(rollback_decision)
    assert validate_default_blocker_unresolved(blocker)
    assert validate_audit_record_review_only(audit)
    assert validate_report_entry_review_only(entry)


def test_report_data_states_design_only_no_activation_or_promotion():
    data = build_promotion_rollback_report_data()
    assert data["final_recommendation"] == "PROCEED_FINAL_V14_SAFETY_CLOSURE_REPORT"
    assert data["candidate"]["candidate_name"] == "HYB1"
    assert data["candidate"]["active"] is False
    assert data["candidate"]["promoted"] is False
    assert data["candidate"]["default_change_allowed"] is False
    assert data["promotion_decision"]["applied"] is False
    assert data["promotion_decision"]["promoted"] is False
    assert data["rollback_decision"]["rollback_executed"] is False
    assert data["default_change_blocker"]["blocks_default_change"] is True
    assert data["invariant_flags"]["hyb1_remains_dormant"] is True
    assert all(value is False for key, value in data["invariant_flags"].items() if key != "hyb1_remains_dormant")


def test_write_promotion_rollback_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_promotion_rollback_report as report_module

    md_path = tmp_path / "promotion.md"
    json_path = tmp_path / "promotion.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_promotion_rollback_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8").lower()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "promotion-rollback-design-only" in text
    assert "hyb1 remains dormant" in text
