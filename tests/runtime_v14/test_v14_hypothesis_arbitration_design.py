from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_hypothesis_arbitration import (
    RUNTIME_V14I_INVARIANT_FLAGS,
    HypothesisArbitrationOutcome,
    HypothesisConflictType,
    HypothesisEscalationType,
    HypothesisEvidenceRelation,
    HypothesisType,
    create_hypothesis_arbitration_input,
    create_hypothesis_arbitration_plan,
    create_hypothesis_arbitration_report,
    create_hypothesis_claim,
    create_hypothesis_conflict,
    create_hypothesis_evidence_link,
    create_hypothesis_review_escalation,
    decide_hypothesis_arbitration,
    score_hypotheses,
    validate_arbitration_decision_report_only,
    validate_arbitration_input_inert,
    validate_arbitration_plan_inert,
    validate_arbitration_report_review_only,
    validate_hypothesis_claim_inert,
    validate_review_escalation_not_triggered,
    validate_scorecard_report_only,
)
from orchestration.runtime.v14_hypothesis_report import (
    build_hypothesis_arbitration_report_data,
    write_hypothesis_arbitration_report,
)


def _claims():
    first = create_hypothesis_claim(
        claim_text="The correction should be preserved for future review.",
        hypothesis_type=HypothesisType.CORRECTION,
        source_reference_ids=("feedback-1",),
        lane_scope=("reasoning",),
        confidence_state=0.55,
        provenance_notes="from user correction",
    )
    second = create_hypothesis_claim(
        claim_text="The correction should be deferred because evidence is weak.",
        hypothesis_type=HypothesisType.INTERPRETATION,
        source_reference_ids=("feedback-2",),
        lane_scope=("reasoning",),
        confidence_state=0.35,
        provenance_notes="from weak evidence",
    )
    return first, second


def _arbitration_input():
    first, second = _claims()
    links = (
        create_hypothesis_evidence_link(
            hypothesis_id=first.hypothesis_id,
            source_reference_id="feedback-1",
            evidence_relation=HypothesisEvidenceRelation.SUPPORTS,
            evidence_weight=0.8,
            rationale="direct correction",
            provenance_reference_ids=("trace-1",),
        ),
        create_hypothesis_evidence_link(
            hypothesis_id=second.hypothesis_id,
            source_reference_id="feedback-2",
            evidence_relation=HypothesisEvidenceRelation.WEAKLY_SUPPORTS,
            evidence_weight=0.3,
            rationale="weak support",
            provenance_reference_ids=("trace-2",),
        ),
    )
    conflict = create_hypothesis_conflict(
        hypothesis_ids=(first.hypothesis_id, second.hypothesis_id),
        conflict_type=HypothesisConflictType.INSUFFICIENT_EVIDENCE,
        rationale="one claim has weaker evidence",
        source_reference_ids=("feedback-1", "feedback-2"),
    )
    return create_hypothesis_arbitration_input(
        hypotheses=(first, second),
        evidence_links=links,
        conflicts=(conflict,),
        source_artifact_references=("packet-1",),
        lane_scope=("reasoning",),
    )


def test_importing_hypothesis_arbitration_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14I_INVARIANT_FLAGS.values())


def test_hypothesis_claims_are_deterministic_inactive_not_canonical_or_learned():
    first, _second = _claims()
    duplicate = create_hypothesis_claim(
        claim_text=first.claim_text,
        hypothesis_type=first.hypothesis_type,
        source_reference_ids=first.source_reference_ids,
        lane_scope=first.lane_scope,
        confidence_state=first.confidence_state,
        provenance_notes=first.provenance_notes,
    )

    assert first.hypothesis_id == duplicate.hypothesis_id
    assert first.active is False
    assert first.canonical is False
    assert first.learned is False
    assert validate_hypothesis_claim_inert(first)


def test_evidence_links_do_not_mutate_source_and_are_deterministic():
    first, _second = _claims()
    link = create_hypothesis_evidence_link(
        hypothesis_id=first.hypothesis_id,
        source_reference_id="source-1",
        evidence_relation=HypothesisEvidenceRelation.SUPPORTS,
        evidence_weight=0.7,
        rationale="supports",
        provenance_reference_ids=("trace-1",),
    )
    duplicate = create_hypothesis_evidence_link(
        hypothesis_id=first.hypothesis_id,
        source_reference_id="source-1",
        evidence_relation=HypothesisEvidenceRelation.SUPPORTS,
        evidence_weight=0.7,
        rationale="supports",
        provenance_reference_ids=("trace-1",),
    )

    assert link.link_id == duplicate.link_id
    assert link.normalized_weight() == 0.7


def test_hypothesis_conflict_is_unresolved_report_material():
    first, second = _claims()
    conflict = create_hypothesis_conflict(
        hypothesis_ids=(second.hypothesis_id, first.hypothesis_id),
        conflict_type=HypothesisConflictType.DIRECT_CONTRADICTION,
        requires_replay_review=True,
    )
    duplicate = create_hypothesis_conflict(
        hypothesis_ids=(first.hypothesis_id, second.hypothesis_id),
        conflict_type=HypothesisConflictType.DIRECT_CONTRADICTION,
        requires_replay_review=True,
    )

    assert conflict.conflict_id == duplicate.conflict_id
    assert conflict.resolved is False
    assert conflict.requires_replay_review is True


def test_arbitration_input_is_deterministic_and_inert():
    arbitration_input = _arbitration_input()
    duplicate = create_hypothesis_arbitration_input(
        hypotheses=arbitration_input.hypotheses,
        evidence_links=arbitration_input.evidence_links,
        conflicts=arbitration_input.conflicts,
        source_artifact_references=arbitration_input.source_artifact_references,
        lane_scope=arbitration_input.lane_scope,
    )

    assert arbitration_input.arbitration_input_id == duplicate.arbitration_input_id
    assert arbitration_input.provider_calls_enabled is False
    assert arbitration_input.specialist_routing_enabled is False
    assert validate_arbitration_input_inert(arbitration_input)


def test_scorecards_are_report_only_and_not_authoritative():
    arbitration_input = _arbitration_input()
    scorecards = score_hypotheses(arbitration_input)

    assert len(scorecards) == 2
    assert all(validate_scorecard_report_only(scorecard) for scorecard in scorecards)
    assert all(scorecard.score_is_authoritative is False for scorecard in scorecards)
    assert max(scorecard.overall_rank_score for scorecard in scorecards) > 0


def test_arbitration_decision_report_preferred_is_not_truth():
    arbitration_input = _arbitration_input()
    scorecards = score_hypotheses(arbitration_input)
    decision = decide_hypothesis_arbitration(arbitration_input, scorecards)

    assert decision.outcome == HypothesisArbitrationOutcome.REPORT_PREFERRED_HYPOTHESIS
    assert decision.preferred_hypothesis_id
    assert decision.applied is False
    assert decision.authoritative is False
    assert "not truth" in decision.rationale
    assert validate_arbitration_decision_report_only(decision)


def test_arbitration_decision_can_require_replay_or_human_review():
    first, second = _claims()
    replay_conflict = create_hypothesis_conflict(
        hypothesis_ids=(first.hypothesis_id, second.hypothesis_id),
        conflict_type=HypothesisConflictType.DIRECT_CONTRADICTION,
        requires_replay_review=True,
    )
    replay_input = create_hypothesis_arbitration_input(hypotheses=(first, second), conflicts=(replay_conflict,))
    replay_decision = decide_hypothesis_arbitration(replay_input, score_hypotheses(replay_input))

    assert replay_decision.outcome == HypothesisArbitrationOutcome.CONFLICT_REQUIRES_REPLAY

    human_conflict = create_hypothesis_conflict(
        hypothesis_ids=(first.hypothesis_id, second.hypothesis_id),
        conflict_type=HypothesisConflictType.SAFETY_CONFLICT,
        requires_human_review=True,
    )
    human_input = create_hypothesis_arbitration_input(hypotheses=(first, second), conflicts=(human_conflict,))
    human_decision = decide_hypothesis_arbitration(human_input, score_hypotheses(human_input))
    assert human_decision.outcome == HypothesisArbitrationOutcome.REQUIRES_HUMAN_REVIEW


def test_arbitration_report_is_review_only():
    arbitration_input = _arbitration_input()
    scorecards = score_hypotheses(arbitration_input)
    decision = decide_hypothesis_arbitration(arbitration_input, scorecards)
    report = create_hypothesis_arbitration_report(arbitration_input, scorecards, decision)

    assert report.generated_for_review_only is True
    assert report.decision.applied is False
    assert report.unresolved_conflicts
    assert validate_arbitration_report_review_only(report)


def test_arbitration_plan_has_no_authority_or_provider_path():
    arbitration_input = _arbitration_input()
    scorecards = score_hypotheses(arbitration_input)
    decision = decide_hypothesis_arbitration(arbitration_input, scorecards)
    plan = create_hypothesis_arbitration_plan(inputs=[arbitration_input], decisions=[decision])

    assert plan.arbitration_input_ids == (arbitration_input.arbitration_input_id,)
    assert plan.arbitration_authority_enabled is False
    assert plan.canonical_write_enabled is False
    assert plan.provider_calls_enabled is False
    assert plan.specialist_routing_enabled is False
    assert plan.scheduler_enabled is False
    assert validate_arbitration_plan_inert(plan)


def test_review_escalation_is_not_triggered():
    arbitration_input = _arbitration_input()
    decision = decide_hypothesis_arbitration(arbitration_input, score_hypotheses(arbitration_input))
    escalation = create_hypothesis_review_escalation(
        decision,
        escalation_type=HypothesisEscalationType.CONTROLLED_LEARNING_REVIEW,
        target_review_layer="controlled_learning",
        required_evidence_or_approval=("human_review",),
    )

    assert escalation.arbitration_decision_id == decision.decision_id
    assert escalation.triggered is False
    assert validate_review_escalation_not_triggered(escalation)


def test_report_data_states_report_only_non_authoritative_status():
    data = build_hypothesis_arbitration_report_data()

    assert data["final_recommendation"] == "PROCEED_DORMANT_SPECIALIST_MERGE_PROTOCOL_DESIGN"
    assert data["safety_boundaries"]["arbitration_authority_enabled"] is False
    assert data["safety_boundaries"]["canonical_write_enabled"] is False
    assert data["safety_boundaries"]["provider_calls_enabled"] is False
    assert data["inactive_systems"]["specialist_routing"] is False


def test_write_hypothesis_arbitration_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14i_report_only_hypothesis_arbitration_design.md"
    json_path = tmp_path / "runtime_v14i_report_only_hypothesis_arbitration_design.json"

    write_hypothesis_arbitration_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_DORMANT_SPECIALIST_MERGE_PROTOCOL_DESIGN"
    assert "arbitration != authority" in text
    assert "A report-preferred hypothesis is not truth" in text
