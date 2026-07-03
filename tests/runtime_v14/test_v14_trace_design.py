from __future__ import annotations

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_architecture_decisions import (
    ArchitectureConcept,
    ArchitectureDecisionStatus,
    build_v14c_decision_lock,
    concepts_requiring_user_decision,
    concepts_must_wait,
    get_decision_for_concept,
)
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_trace import (
    FeedbackSignalType,
    ReplayEligibility,
    TraceAnswerMode,
    TraceEvidenceUse,
    TraceRiskFlag,
    add_evidence_trace,
    classify_replay_eligibility,
    create_answer_trace,
    create_feedback_event_draft,
    mark_trace_for_replay,
    summarize_trace_for_report,
    validate_trace_is_non_mutating,
)


def test_architecture_decision_lock_builds():
    decisions = build_v14c_decision_lock()

    assert decisions
    assert {decision.concept for decision in decisions} >= set(ArchitectureConcept)


def test_sleep_cycle_preserved_as_scheduled_replay_consolidation():
    decision = get_decision_for_concept(ArchitectureConcept.SLEEP_REPLAY_CONSOLIDATION)

    assert decision.status == ArchitectureDecisionStatus.ACCEPTED
    assert "scheduled/batch replay-consolidation" in decision.implementation_decision
    assert "literal sleep" in decision.implementation_decision


def test_live_pruning_projection_accepted_but_canonical_pruning_deferred():
    live_pruning = get_decision_for_concept(ArchitectureConcept.LIVE_PRUNING_PROJECTION)
    canonical_pruning = get_decision_for_concept(ArchitectureConcept.CANONICAL_PRUNING)

    assert live_pruning.status == ArchitectureDecisionStatus.ACCEPTED
    assert "temporary runtime/session projection" in live_pruning.implementation_decision
    assert canonical_pruning.status == ArchitectureDecisionStatus.DEFERRED


def test_controlled_training_is_deferred():
    decision = get_decision_for_concept(ArchitectureConcept.CONTROLLED_TRAINING)

    assert decision.status == ArchitectureDecisionStatus.DEFERRED
    assert "output traces" in decision.implementation_decision


def test_specialist_routing_is_deferred_with_no_live_calls():
    decision = get_decision_for_concept(ArchitectureConcept.SPECIALIST_ROUTING)

    assert decision.status == ArchitectureDecisionStatus.DEFERRED
    assert "no provider calls" in decision.implementation_decision


def test_concepts_requiring_user_decision_and_wait_lists_are_available():
    user_decisions = concepts_requiring_user_decision()
    must_wait = concepts_must_wait()

    assert user_decisions
    assert must_wait
    assert any(decision.concept == ArchitectureConcept.LIVE_CANONICAL_STORE for decision in user_decisions)


def test_answer_trace_can_be_created():
    trace = create_answer_trace(
        question="What should DELTA do?",
        answer_mode=TraceAnswerMode.BEST_GUESS,
        confidence=0.6,
        risk_flags=(TraceRiskFlag.WEAK_EVIDENCE,),
        final_answer_summary="Proceed cautiously.",
    )

    assert trace.trace_id.startswith("trace-")
    assert trace.answer_mode == TraceAnswerMode.BEST_GUESS
    assert trace.normalized_confidence() == 0.6


def test_evidence_trace_can_be_added():
    trace = create_answer_trace(question="Why?", answer_mode=TraceAnswerMode.DIRECT_ANSWER)
    updated = add_evidence_trace(
        trace,
        concept_id="concept-1",
        evidence_use=TraceEvidenceUse.CITABLE_USED,
        lane=RuntimeLane.REASONING,
        reason="supports answer",
        confidence=0.8,
    )

    assert len(updated.evidence_traces) == 1
    assert updated.evidence_traces[0].concept_id == "concept-1"
    assert len(trace.evidence_traces) == 0


def test_feedback_event_draft_can_be_created():
    draft = create_feedback_event_draft(
        trace_id="trace-1",
        signal_type=FeedbackSignalType.USER_CORRECTED,
        feedback_text="That evidence was wrong.",
        affected_concepts=("concept-1",),
    )

    assert draft.proposed_replay_eligibility == ReplayEligibility.ELIGIBLE_FOR_REVIEW
    assert draft.proposed_pruning_review


def test_replay_eligibility_can_be_classified():
    assert (
        classify_replay_eligibility(signal_type=FeedbackSignalType.USER_CONFIRMED)
        == ReplayEligibility.ELIGIBLE_FOR_REPLAY
    )
    assert (
        classify_replay_eligibility(
            signal_type=FeedbackSignalType.UNSAFE_OR_ACTIONABLE_RISK,
            risk_flags=(TraceRiskFlag.UNSAFE_ACTION,),
        )
        == ReplayEligibility.REQUIRES_HUMAN_REVIEW
    )


def test_benchmark_only_do_not_train_prevents_replay_eligibility():
    eligibility = classify_replay_eligibility(
        signal_type=FeedbackSignalType.USER_CORRECTED,
        benchmark_only=True,
    )

    assert eligibility == ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN


def test_replay_marker_and_summary_are_report_only():
    trace = create_answer_trace(question="What happened?", answer_mode=TraceAnswerMode.WEAK_GUESS)
    trace = add_evidence_trace(
        trace,
        concept_id="concept-2",
        evidence_use=TraceEvidenceUse.IGNORED,
        lane=RuntimeLane.ATTENTION,
        reason="not relevant enough",
    )
    marker = mark_trace_for_replay(
        trace,
        eligibility=ReplayEligibility.ELIGIBLE_FOR_REVIEW,
        reason="user asked for more evidence",
        priority=0.7,
    )
    summary = summarize_trace_for_report(trace)

    assert marker.trace_id == trace.trace_id
    assert summary["evidence_use_counts"]["ignored"] == 1
    assert summary["non_mutating"] is True


def test_validate_trace_is_non_mutating_returns_true_for_trace_objects():
    trace = create_answer_trace(question="Safe?", answer_mode=TraceAnswerMode.ABSTAINED)
    feedback = create_feedback_event_draft(trace_id=trace.trace_id, signal_type=FeedbackSignalType.UNKNOWN)
    marker = mark_trace_for_replay(trace, eligibility=ReplayEligibility.NOT_ELIGIBLE, reason="no signal")

    assert validate_trace_is_non_mutating(trace)
    assert validate_trace_is_non_mutating(feedback)
    assert validate_trace_is_non_mutating(marker)


def test_importing_trace_design_does_not_change_model_b_or_hyb1_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
