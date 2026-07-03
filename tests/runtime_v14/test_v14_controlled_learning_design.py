from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_controlled_learning import (
    RUNTIME_V14H_INVARIANT_FLAGS,
    ControlledLearningDecisionOutcome,
    LearningEligibilitySignalType,
    LearningSafetyStatus,
    LearningSignalPolarity,
    create_controlled_learning_plan,
    create_learning_candidate,
    create_learning_evidence_packet,
    create_learning_rollback_plan,
    create_learning_signal,
    create_learning_signal_from_feedback,
    decide_controlled_learning,
    review_learning_candidate,
    validate_controlled_learning_plan_inert,
    validate_evidence_packet_not_training_dataset,
    validate_learning_candidate_inactive,
    validate_learning_decision_review_only,
    validate_learning_rollback_not_applied,
    validate_safety_review_non_training,
    validate_signal_non_mutating,
)
from orchestration.runtime.v14_controlled_learning_report import (
    build_controlled_learning_report_data,
    write_controlled_learning_report,
)
from orchestration.runtime.v14_episode import TraceRiskFlag, create_episode_from_answer_trace
from orchestration.runtime.v14_feedback import (
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackSource,
    FeedbackTarget,
    capture_feedback_from_episode,
)
from orchestration.runtime.v14_learning_audit import (
    create_learning_audit_record,
    validate_learning_audit_record_report_only,
)
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_trace import TraceAnswerMode, create_answer_trace


def _feedback(*, polarity=FeedbackPolarity.CORRECTS, severity=FeedbackSeverity.MEDIUM):
    trace = create_answer_trace(
        trace_id="trace-v14h",
        question="Should this correction become learning material?",
        answer_mode=TraceAnswerMode.WEAK_GUESS,
        confidence=0.52,
        risk_flags=(TraceRiskFlag.WEAK_EVIDENCE,),
        final_answer_summary="Record the correction for future review only.",
    )
    episode = create_episode_from_answer_trace(trace)
    return capture_feedback_from_episode(
        episode,
        source=FeedbackSource.USER_EXPLICIT,
        polarity=polarity,
        severity=severity,
        target=FeedbackTarget.EVIDENCE_USE,
        feedback_text="This correction may be useful later.",
        affected_concepts=("concept-v14h",),
        affected_lanes=(RuntimeLane.REASONING,),
    )


def _candidate():
    signal = create_learning_signal_from_feedback(_feedback())
    packet = create_learning_evidence_packet(
        signals=[signal],
        source_reference_ids=("trace-v14h",),
        evidence_summary="correction supported by feedback",
    )
    candidate = create_learning_candidate(
        packet,
        proposed_learning_scope="offline_hypothesis_review",
        proposed_change_summary="Review correction as future learning candidate.",
        lane_scope=("reasoning",),
    )
    return candidate, packet


def test_importing_controlled_learning_design_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14H_INVARIANT_FLAGS.values())


def test_learning_signal_from_feedback_is_deterministic_and_non_mutating():
    feedback = _feedback()
    before = feedback.as_dict()

    first = create_learning_signal_from_feedback(feedback)
    second = create_learning_signal_from_feedback(feedback)

    assert first.signal_id == second.signal_id
    assert first.signal_type == LearningEligibilitySignalType.CORRECTION_CONFIRMED
    assert first.polarity == LearningSignalPolarity.SUPPORTS_LEARNING
    assert validate_signal_non_mutating(first)
    assert feedback.as_dict() == before


def test_learning_evidence_packet_is_not_training_dataset():
    signal = create_learning_signal(
        source_reference_id="source-1",
        signal_type=LearningEligibilitySignalType.REPLAY_SUPPORTED,
        polarity=LearningSignalPolarity.SUPPORTS_LEARNING,
        weight=0.7,
        rationale="replay supported future review",
    )
    packet = create_learning_evidence_packet(signals=[signal], source_reference_ids=("source-1",))
    duplicate = create_learning_evidence_packet(signals=[signal], source_reference_ids=("source-1",))

    assert packet.packet_id == duplicate.packet_id
    assert packet.training_dataset_export_enabled is False
    assert packet.learning_active is False
    assert validate_evidence_packet_not_training_dataset(packet)


def test_learning_candidate_is_inactive_and_not_training_ready():
    candidate, packet = _candidate()

    assert candidate.evidence_packet_id == packet.packet_id
    assert candidate.active is False
    assert candidate.training_ready is False
    assert candidate.applied is False
    assert candidate.canonical_mutation is False
    assert candidate.runtime_recall_mutation is False
    assert validate_learning_candidate_inactive(candidate)


def test_learning_safety_review_is_non_training():
    candidate, packet = _candidate()
    review = review_learning_candidate(candidate, packet)

    assert review.safety_status == LearningSafetyStatus.SAFE_FOR_FUTURE_REVIEW
    assert review.training_approved is False
    assert review.applied is False
    assert validate_safety_review_non_training(review)


def test_learning_safety_review_handles_conflict_and_human_review():
    conflict = create_learning_signal(
        source_reference_id="conflict",
        signal_type=LearningEligibilitySignalType.REPLAY_CONFLICTED,
        polarity=LearningSignalPolarity.BLOCKS_LEARNING,
        weight=0.8,
        rationale="conflict",
    )
    packet = create_learning_evidence_packet(signals=[conflict])
    candidate = create_learning_candidate(
        packet,
        proposed_learning_scope="offline_hypothesis_review",
        proposed_change_summary="conflicting candidate",
    )
    review = review_learning_candidate(candidate, packet)

    assert review.safety_status == LearningSafetyStatus.CONFLICTING_EVIDENCE

    human_signal = create_learning_signal_from_feedback(
        _feedback(polarity=FeedbackPolarity.FLAGS_SAFETY_RISK, severity=FeedbackSeverity.HIGH)
    )
    human_packet = create_learning_evidence_packet(signals=[human_signal])
    human_candidate = create_learning_candidate(
        human_packet,
        proposed_learning_scope="offline_hypothesis_review",
        proposed_change_summary="human review candidate",
    )
    human_review = review_learning_candidate(human_candidate, human_packet)
    assert human_review.safety_status == LearningSafetyStatus.REQUIRES_HUMAN_REVIEW


def test_controlled_learning_decisions_are_review_only_and_cover_outcomes():
    candidate, packet = _candidate()
    review = review_learning_candidate(candidate, packet)

    outcomes = {
        decide_controlled_learning(candidate, review).outcome,
        decide_controlled_learning(candidate, review, defer=True).outcome,
        decide_controlled_learning(candidate, review, reject=True).outcome,
        decide_controlled_learning(candidate, review, require_human_review=True).outcome,
        decide_controlled_learning(candidate, review, invariant_block=True).outcome,
        decide_controlled_learning(candidate, review, eligible_for_future_offline_review=True).outcome,
    }

    assert outcomes == {
        ControlledLearningDecisionOutcome.CANDIDATE_ONLY,
        ControlledLearningDecisionOutcome.DEFER,
        ControlledLearningDecisionOutcome.REJECT,
        ControlledLearningDecisionOutcome.REQUIRES_HUMAN_REVIEW,
        ControlledLearningDecisionOutcome.BLOCKED_BY_INVARIANT,
        ControlledLearningDecisionOutcome.ELIGIBLE_FOR_FUTURE_OFFLINE_REVIEW,
    }
    decision = decide_controlled_learning(candidate, review)
    assert decision.training_enabled is False
    assert decision.applied is False
    assert validate_learning_decision_review_only(decision)


def test_controlled_learning_plan_has_no_training_or_scheduler_authority():
    candidate, packet = _candidate()
    review = review_learning_candidate(candidate, packet)
    decision = decide_controlled_learning(candidate, review)
    plan = create_controlled_learning_plan(candidates=[candidate], decisions=[decision])

    assert plan.candidate_ids == (candidate.candidate_id,)
    assert plan.training_enabled is False
    assert plan.fine_tuning_enabled is False
    assert plan.weight_update_enabled is False
    assert plan.training_dataset_export_enabled is False
    assert plan.scheduler_enabled is False
    assert validate_controlled_learning_plan_inert(plan)


def test_learning_rollback_plan_is_not_applied():
    candidate, _packet = _candidate()
    rollback = create_learning_rollback_plan(
        candidate,
        rollback_reason="future learned change would need reversal",
        required_evidence_or_approval=("human_review",),
    )

    assert rollback.candidate_id == candidate.candidate_id
    assert rollback.applied is False
    assert validate_learning_rollback_not_applied(rollback)


def test_learning_audit_record_is_report_only():
    candidate, packet = _candidate()
    review = review_learning_candidate(candidate, packet)
    decision = decide_controlled_learning(candidate, review)
    audit = create_learning_audit_record(candidate, review, decision)

    assert audit.candidate_id == candidate.candidate_id
    assert audit.decision_id == decision.decision_id
    assert audit.review_id == review.review_id
    assert audit.applied is False
    assert audit.persisted_to_active_store is False
    assert audit.training_triggered is False
    assert validate_learning_audit_record_report_only(audit)


def test_report_data_states_controlled_learning_is_scaffold_only():
    data = build_controlled_learning_report_data()

    assert data["final_recommendation"] == "PROCEED_REPORT_ONLY_HYPOTHESIS_ARBITRATION_DESIGN"
    assert data["safety_boundaries"]["training_enabled"] is False
    assert data["safety_boundaries"]["fine_tuning_enabled"] is False
    assert data["safety_boundaries"]["weight_update_enabled"] is False
    assert data["safety_boundaries"]["training_dataset_export_enabled"] is False
    assert data["inactive_systems"]["provider_calls"] is False


def test_write_controlled_learning_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14h_controlled_learning_design.md"
    json_path = tmp_path / "runtime_v14h_controlled_learning_design.json"

    write_controlled_learning_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_REPORT_ONLY_HYPOTHESIS_ARBITRATION_DESIGN"
    assert "Controlled Learning Design is an eligibility and governance scaffold, not training." in text
    assert "learning_design != learning" in text
