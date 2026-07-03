from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_episode import TraceRiskFlag, create_episode_from_answer_trace
from orchestration.runtime.v14_feedback import (
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackSource,
    FeedbackTarget,
    capture_feedback_from_episode,
)
from orchestration.runtime.v14_feedback_to_pruning import feedback_to_pruning_review_proposals
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_pruning_projection import (
    RUNTIME_V14G_INVARIANT_FLAGS,
    PruningProjectionDecisionOutcome,
    PruningProjectionEffect,
    PruningProjectionIntent,
    PruningProjectionReviewFinding,
    create_projection_plan,
    create_projection_request,
    create_projection_rollback_plan,
    create_projection_scope,
    create_projection_signal,
    create_projection_signal_from_feedback,
    create_projection_signal_from_pruning_proposal,
    create_temporary_pruning_projection,
    decide_projection_request,
    review_projection_request,
    validate_projection_decision_review_only,
    validate_projection_plan_inert,
    validate_projection_request_review_only,
    validate_projection_review_result_not_applied,
    validate_projection_rollback_not_applied,
    validate_projection_scope_lane_scoped,
    validate_temporary_projection_inactive,
    PruningProjectionSignalType,
)
from orchestration.runtime.v14_pruning_projection_report import (
    build_pruning_projection_report_data,
    write_pruning_projection_report,
)
from orchestration.runtime.v14_trace import TraceAnswerMode, create_answer_trace


def _feedback(*, polarity=FeedbackPolarity.FLAGS_NOISE, severity=FeedbackSeverity.MEDIUM):
    trace = create_answer_trace(
        trace_id="trace-v14g",
        question="Should this evidence be dampened?",
        answer_mode=TraceAnswerMode.WEAK_GUESS,
        confidence=0.44,
        risk_flags=(TraceRiskFlag.SAME_TOPIC_NOISE,),
        final_answer_summary="Review the noisy evidence.",
    )
    episode = create_episode_from_answer_trace(trace)
    return capture_feedback_from_episode(
        episode,
        source=FeedbackSource.EVALUATOR_REPORT,
        polarity=polarity,
        severity=severity,
        target=FeedbackTarget.REASONING_LANE,
        feedback_text="Same-topic noise entered reasoning.",
        affected_concepts=("concept-noise",),
        affected_lanes=(RuntimeLane.REASONING,),
    )


def _projection_request():
    record = _feedback()
    proposal = feedback_to_pruning_review_proposals(record)[0]
    signal = create_projection_signal_from_pruning_proposal(proposal)
    scope = create_projection_scope(
        lane=RuntimeLane.REASONING,
        projection_context_id="session-v14g",
        source_reference_ids=(proposal.proposal_id,),
    )
    request = create_projection_request(
        scope=scope,
        signals=[signal],
        requested_intent=PruningProjectionIntent.DAMPEN_TEMPORARILY,
        source_artifacts=("PruningReviewProposal",),
        created_from_refs=(proposal.proposal_id,),
    )
    return request


def test_importing_projection_design_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14G_INVARIANT_FLAGS.values())


def test_projection_scope_is_lane_scoped_not_global():
    scope = create_projection_scope(
        lane=RuntimeLane.PLANNING,
        projection_context_id="session-1",
        source_reference_ids=("concept-1",),
    )

    assert scope.lane_value() == "planning"
    assert scope.applies_globally is False
    assert scope.canonical_scope is False
    assert scope.runtime_recall_scope is False
    assert validate_projection_scope_lane_scoped(scope)


def test_projection_signal_from_pruning_proposal_is_deterministic_and_non_mutating():
    record = _feedback()
    proposal = feedback_to_pruning_review_proposals(record)[0]
    before = proposal.as_dict()

    first = create_projection_signal_from_pruning_proposal(proposal)
    second = create_projection_signal_from_pruning_proposal(proposal)

    assert first.signal_id == second.signal_id
    assert first.source_reference_id == proposal.proposal_id
    assert first.normalized_severity() == proposal.normalized_confidence()
    assert proposal.as_dict() == before


def test_projection_signal_from_feedback_is_review_only():
    record = _feedback(polarity=FeedbackPolarity.FLAGS_UNCERTAINTY, severity=FeedbackSeverity.LOW)
    signal = create_projection_signal_from_feedback(record)

    assert signal.signal_type == PruningProjectionSignalType.LOW_CONFIDENCE
    assert signal.source_reference_id == record.feedback_id
    assert record.affected_concepts == ("concept-noise",)


def test_projection_request_is_deterministic_and_not_applied():
    request = _projection_request()
    duplicate = create_projection_request(
        scope=request.scope,
        signals=request.signals,
        requested_intent=request.requested_intent,
        source_artifacts=request.source_artifacts,
        created_from_refs=request.created_from_refs,
    )

    assert request.request_id == duplicate.request_id
    assert request.applied is False
    assert request.requested_intent == PruningProjectionIntent.DAMPEN_TEMPORARILY
    assert validate_projection_request_review_only(request)


def test_projection_review_detects_useful_signal_without_applying():
    request = _projection_request()
    review = review_projection_request(request)

    assert PruningProjectionReviewFinding.USEFUL_TEMPORARY_DAMPENING_SIGNAL in review.findings
    assert review.projection_recommended
    assert review.applied is False
    assert validate_projection_review_result_not_applied(review)


def test_projection_review_can_reject_empty_or_explicit_reject_request():
    scope = create_projection_scope(lane=RuntimeLane.RESPONSE, projection_context_id="session-empty")
    empty = create_projection_request(
        scope=scope,
        signals=[],
        requested_intent=PruningProjectionIntent.REJECT_PROJECTION,
    )
    review = review_projection_request(empty)

    assert PruningProjectionReviewFinding.REJECT_PROJECTION in review.findings
    assert PruningProjectionReviewFinding.INSUFFICIENT_EVIDENCE in review.findings
    assert review.projection_recommended is False


def test_projection_decision_is_review_only_and_covers_outcomes():
    request = _projection_request()
    review = review_projection_request(request)

    outcomes = {
        decide_projection_request(request, review).outcome,
        decide_projection_request(request, review, defer=True).outcome,
        decide_projection_request(request, review, reject=True).outcome,
        decide_projection_request(request, review, require_human_review=True).outcome,
        decide_projection_request(request, review, invariant_block=True).outcome,
        decide_projection_request(request, review, eligible_for_future_projection=True).outcome,
    }

    assert outcomes == {
        PruningProjectionDecisionOutcome.PROJECTION_ONLY,
        PruningProjectionDecisionOutcome.DEFER,
        PruningProjectionDecisionOutcome.REJECT,
        PruningProjectionDecisionOutcome.REQUIRES_HUMAN_REVIEW,
        PruningProjectionDecisionOutcome.BLOCKED_BY_INVARIANT,
        PruningProjectionDecisionOutcome.ELIGIBLE_FOR_FUTURE_PROJECTION,
    }
    assert validate_projection_decision_review_only(decide_projection_request(request, review))


def test_temporary_projection_is_inactive_and_does_not_mutate_recall_or_canonical_memory():
    request = _projection_request()
    review = review_projection_request(request)
    decision = decide_projection_request(request, review)
    projection = create_temporary_pruning_projection(
        decision,
        request,
        projection_effect=PruningProjectionEffect.DAMPEN,
        projection_strength=0.6,
    )

    assert projection.applied is False
    assert projection.active is False
    assert projection.canonical_mutation is False
    assert projection.runtime_recall_mutation is False
    assert projection.projection_effect == PruningProjectionEffect.DAMPEN
    assert validate_temporary_projection_inactive(projection)


def test_projection_plan_has_no_pruning_or_scheduler_authority():
    request = _projection_request()
    review = review_projection_request(request)
    decision = decide_projection_request(request, review)
    projection = create_temporary_pruning_projection(decision, request)
    plan = create_projection_plan(requests=[request], decisions=[decision], projections=[projection])

    assert plan.request_ids == (request.request_id,)
    assert plan.projection_ids == (projection.projection_id,)
    assert validate_projection_plan_inert(plan)
    assert plan.pruning_enabled is False
    assert plan.canonical_pruning_enabled is False
    assert plan.projection_application_enabled is False
    assert plan.scheduler_enabled is False


def test_projection_rollback_plan_is_not_applied():
    request = _projection_request()
    review = review_projection_request(request)
    decision = decide_projection_request(request, review)
    projection = create_temporary_pruning_projection(decision, request)
    rollback = create_projection_rollback_plan(
        projection,
        rollback_reason="Projection was only a future review artifact.",
        required_evidence_or_approval=("human_review",),
    )

    assert rollback.projection_id == projection.projection_id
    assert rollback.reversible is True
    assert rollback.applied is False
    assert validate_projection_rollback_not_applied(rollback)


def test_manual_low_severity_signal_is_insufficient():
    scope = create_projection_scope(lane=RuntimeLane.REASONING, projection_context_id="session-low")
    signal = create_projection_signal(
        source_reference_id="source-low",
        signal_type=PruningProjectionSignalType.LOW_CONFIDENCE,
        severity=0.1,
        rationale="too weak",
    )
    request = create_projection_request(
        scope=scope,
        signals=[signal],
        requested_intent=PruningProjectionIntent.DAMPEN_TEMPORARILY,
    )
    review = review_projection_request(request)

    assert PruningProjectionReviewFinding.INSUFFICIENT_EVIDENCE in review.findings
    assert review.projection_recommended is False


def test_report_data_states_scaffold_only_and_non_mutating():
    data = build_pruning_projection_report_data()

    assert data["final_recommendation"] == "PROCEED_CONTROLLED_LEARNING_DESIGN"
    assert data["safety_boundaries"]["pruning_enabled"] is False
    assert data["safety_boundaries"]["canonical_pruning_enabled"] is False
    assert data["safety_boundaries"]["projection_application_enabled"] is False
    assert data["inactive_systems"]["actual_pruning"] is False


def test_write_projection_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14g_temporary_pruning_projection_design.md"
    json_path = tmp_path / "runtime_v14g_temporary_pruning_projection_design.json"

    write_pruning_projection_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_LEARNING_DESIGN"
    assert "projection != pruning" in text
    assert "Temporary pruning projection is a reversible, lane-scoped proposal layer." in text
