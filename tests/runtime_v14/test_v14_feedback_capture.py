from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_feedback import (
    FeedbackDisposition,
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackSource,
    FeedbackTarget,
    capture_feedback_from_trace,
    feedback_to_event_draft,
    is_feedback_training_safe,
    requires_human_review,
    summarize_feedback_records,
)
from orchestration.runtime.v14_feedback_report import build_feedback_capture_report_data, write_feedback_capture_report
from orchestration.runtime.v14_feedback_to_pruning import (
    PruningReviewDecision,
    classify_pruning_failure_type,
    feedback_to_pruning_review_proposals,
    validate_pruning_proposal_non_mutating,
)
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_pruning import CorrectiveAction, PruningFailureType
from orchestration.runtime.v14_replay_markers import (
    ReplayMarkerStatus,
    ReplayPriority,
    ReplayReason,
    classify_replay_priority,
    create_replay_marker_from_feedback,
    should_queue_for_replay,
)
from orchestration.runtime.v14_trace import ReplayEligibility, TraceAnswerMode, create_answer_trace


def _trace():
    return create_answer_trace(
        trace_id="trace-test",
        question="What should DELTA do?",
        answer_mode=TraceAnswerMode.WEAK_GUESS,
        confidence=0.4,
        final_answer_summary="Proceed cautiously.",
    )


def test_new_modules_import_without_changing_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False


def test_can_create_feedback_record_from_answer_trace():
    record = capture_feedback_from_trace(
        _trace(),
        source=FeedbackSource.USER_EXPLICIT,
        polarity=FeedbackPolarity.CONFIRMS,
        severity=FeedbackSeverity.LOW,
        target=FeedbackTarget.FINAL_ANSWER,
        feedback_text="That was useful.",
    )

    assert record.feedback_id.startswith("feedback-")
    assert record.trace_id == "trace-test"
    assert record.proposed_disposition == FeedbackDisposition.RECORD_ONLY


def test_user_correction_becomes_eligible_for_replay_not_immediate_training():
    record = capture_feedback_from_trace(
        _trace(),
        source=FeedbackSource.USER_EXPLICIT,
        polarity=FeedbackPolarity.CORRECTS,
        severity=FeedbackSeverity.MEDIUM,
        target=FeedbackTarget.EVIDENCE_USE,
        feedback_text="The cited concept was wrong.",
        affected_concepts=("concept-1",),
    )

    assert record.proposed_disposition == FeedbackDisposition.ELIGIBLE_FOR_REPLAY
    assert is_feedback_training_safe(record) is False


def test_benchmark_only_forces_do_not_train():
    record = capture_feedback_from_trace(
        _trace(),
        source=FeedbackSource.BENCHMARK_REPORT,
        polarity=FeedbackPolarity.CORRECTS,
        severity=FeedbackSeverity.HIGH,
        target=FeedbackTarget.FINAL_ANSWER,
        feedback_text="Fixture expected another concept.",
        benchmark_only=True,
    )

    assert record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert not is_feedback_training_safe(record)


def test_critical_severity_requires_human_review():
    record = capture_feedback_from_trace(
        _trace(),
        source=FeedbackSource.USER_EXPLICIT,
        polarity=FeedbackPolarity.REJECTS,
        severity=FeedbackSeverity.CRITICAL,
        target=FeedbackTarget.FINAL_ANSWER,
        feedback_text="This was dangerously wrong.",
    )

    assert requires_human_review(record)
    assert record.proposed_disposition == FeedbackDisposition.REQUIRES_HUMAN_REVIEW


def test_safety_risk_requires_human_review():
    record = capture_feedback_from_trace(
        _trace(),
        source=FeedbackSource.MODEL_SELF_CHECK,
        polarity=FeedbackPolarity.FLAGS_SAFETY_RISK,
        severity=FeedbackSeverity.HIGH,
        target=FeedbackTarget.PLANNING_LANE,
        feedback_text="Unsafe action risk.",
    )

    assert requires_human_review(record)
    assert record.proposed_disposition == FeedbackDisposition.REQUIRES_HUMAN_REVIEW


def test_noise_feedback_with_affected_concept_becomes_pruning_review_candidate():
    record = capture_feedback_from_trace(
        _trace(),
        source=FeedbackSource.EVALUATOR_REPORT,
        polarity=FeedbackPolarity.FLAGS_NOISE,
        severity=FeedbackSeverity.MEDIUM,
        target=FeedbackTarget.REASONING_LANE,
        feedback_text="Same-topic noise entered reasoning.",
        affected_concepts=("concept-noise",),
        affected_lanes=(RuntimeLane.REASONING,),
    )

    assert record.proposed_disposition == FeedbackDisposition.PRUNING_REVIEW_CANDIDATE
    assert should_queue_for_replay(record)


def test_summarize_feedback_records_works():
    first = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.FINAL_ANSWER,
        "Needs correction.",
    )
    second = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.HUMAN_REVIEW,
        FeedbackPolarity.REJECTS,
        FeedbackSeverity.CRITICAL,
        FeedbackTarget.PLANNING_LANE,
        "Unsafe plan.",
    )

    summary = summarize_feedback_records([first, second])

    assert summary.feedback_count == 2
    assert summary.highest_severity == FeedbackSeverity.CRITICAL
    assert summary.human_review_required


def test_feedback_to_event_draft_returns_non_mutating_draft():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.EVIDENCE_USE,
        "Correct this later.",
        affected_concepts=("concept-1",),
    )

    draft = feedback_to_event_draft(record)

    assert draft.trace_id == record.trace_id
    assert draft.proposed_replay_eligibility == ReplayEligibility.ELIGIBLE_FOR_REVIEW
    assert draft.proposed_pruning_review is False


def test_user_correction_creates_replay_marker():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.FINAL_ANSWER,
        "Correction.",
    )

    marker = create_replay_marker_from_feedback(record)

    assert marker.reason == ReplayReason.USER_CORRECTION
    assert marker.eligibility == ReplayEligibility.ELIGIBLE_FOR_REPLAY
    assert marker.status == ReplayMarkerStatus.PROPOSED


def test_benchmark_only_creates_do_not_train_marker():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.BENCHMARK_REPORT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.LOW,
        FeedbackTarget.FINAL_ANSWER,
        "Benchmark-only.",
        benchmark_only=True,
    )

    marker = create_replay_marker_from_feedback(record)

    assert marker.eligibility == ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert marker.status == ReplayMarkerStatus.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert not should_queue_for_replay(record)


def test_critical_safety_risk_marker_requires_human_review():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.HUMAN_REVIEW,
        FeedbackPolarity.FLAGS_SAFETY_RISK,
        FeedbackSeverity.CRITICAL,
        FeedbackTarget.PLANNING_LANE,
        "Do not action this.",
    )

    marker = create_replay_marker_from_feedback(record)

    assert marker.eligibility == ReplayEligibility.REQUIRES_HUMAN_REVIEW
    assert marker.status == ReplayMarkerStatus.REQUIRES_HUMAN_REVIEW
    assert marker.priority == ReplayPriority.CRITICAL


def test_replay_priority_classification_works():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.ASKS_FOR_MORE_EVIDENCE,
        FeedbackSeverity.HIGH,
        FeedbackTarget.UNCERTAINTY_MODE,
        "Need stronger evidence.",
    )

    assert classify_replay_priority(record) == ReplayPriority.HIGH


def test_same_topic_noise_produces_dampen_or_require_context_review_proposal():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.EVALUATOR_REPORT,
        FeedbackPolarity.FLAGS_NOISE,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.REASONING_LANE,
        "Same-topic noise entered reasoning.",
        affected_concepts=("concept-noise",),
        affected_lanes=(RuntimeLane.REASONING,),
    )

    proposals = feedback_to_pruning_review_proposals(record)

    assert proposals
    assert proposals[0].failure_type == PruningFailureType.SAME_TOPIC_NOISE
    assert proposals[0].corrective_action in {CorrectiveAction.DAMPEN, CorrectiveAction.REQUIRE_CONTEXT}
    assert validate_pruning_proposal_non_mutating(proposals[0])


def test_low_severity_one_off_feedback_does_not_propose_quarantine():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.LOW,
        FeedbackTarget.EVIDENCE_USE,
        "Small correction.",
        affected_concepts=("concept-1",),
    )

    proposals = feedback_to_pruning_review_proposals(record)

    assert all(proposal.decision != PruningReviewDecision.PROPOSE_QUARANTINE_REVIEW for proposal in proposals)


def test_benchmark_only_feedback_produces_no_pruning_proposal():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.BENCHMARK_REPORT,
        FeedbackPolarity.FLAGS_NOISE,
        FeedbackSeverity.HIGH,
        FeedbackTarget.REASONING_LANE,
        "Benchmark-only noise.",
        affected_concepts=("concept-1",),
        benchmark_only=True,
    )

    assert feedback_to_pruning_review_proposals(record) == []


def test_false_or_corrupt_concept_requires_human_review():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.HUMAN_REVIEW,
        FeedbackPolarity.REJECTS,
        FeedbackSeverity.HIGH,
        FeedbackTarget.CONCEPT_USAGE,
        "This is a false or corrupt concept.",
        affected_concepts=("concept-corrupt",),
        affected_lanes=(RuntimeLane.REASONING,),
    )

    proposals = feedback_to_pruning_review_proposals(record)

    assert classify_pruning_failure_type(record) == PruningFailureType.FALSE_OR_CORRUPT_CONCEPT
    assert proposals
    assert proposals[0].human_review_required
    assert not proposals[0].reversible


def test_all_normal_pruning_review_proposals_are_reversible():
    record = capture_feedback_from_trace(
        _trace(),
        FeedbackSource.EVALUATOR_REPORT,
        FeedbackPolarity.FLAGS_NOISE,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.REASONING_LANE,
        "Same-topic noise.",
        affected_concepts=("concept-1", "concept-2"),
        affected_lanes=(RuntimeLane.REASONING,),
    )

    proposals = feedback_to_pruning_review_proposals(record)

    assert proposals
    assert all(proposal.reversible for proposal in proposals)


def test_no_provider_or_canonical_mutation_functions_are_exposed():
    data = build_feedback_capture_report_data()

    assert data["safety_boundaries"]["provider_calls_enabled"] is False
    assert data["safety_boundaries"]["canonical_mutation_enabled"] is False
    assert data["safety_boundaries"]["training_enabled"] is False


def test_write_feedback_capture_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14d_feedback_capture_scaffold.md"
    json_path = tmp_path / "runtime_v14d_feedback_capture_scaffold.json"

    write_feedback_capture_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["final_recommendation"] == "PROCEED_SLEEP_REPLAY_CONSOLIDATION_DESIGN"
