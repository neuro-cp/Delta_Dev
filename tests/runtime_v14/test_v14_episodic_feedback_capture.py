from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_episode import (
    EpisodeReplayStatus,
    EpisodeReplayIntent,
    TraceRiskFlag,
    attach_feedback_to_episode,
    attach_replay_marker_to_episode,
    create_episode_from_answer_trace,
    summarize_episode_for_report,
    validate_episode_is_non_mutating,
)
from orchestration.runtime.v14_feedback import (
    FeedbackDisposition,
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackSource,
    FeedbackTarget,
    capture_feedback_from_episode,
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
    create_replay_marker_from_episode,
    create_replay_marker_from_feedback,
    should_queue_for_replay,
)
from orchestration.runtime.v14_trace import ReplayEligibility, TraceAnswerMode, create_answer_trace


def _answer_trace(*, risk_flags=(TraceRiskFlag.NONE,), confidence=0.5):
    return create_answer_trace(
        trace_id="trace-episode-test",
        question="How should DELTA proceed?",
        answer_mode=TraceAnswerMode.WEAK_GUESS,
        confidence=confidence,
        risk_flags=risk_flags,
        uncertainty_reason="limited evidence" if risk_flags != (TraceRiskFlag.NONE,) else "",
        final_answer_summary="Proceed cautiously.",
    )


def _episode(*, risk_flags=(TraceRiskFlag.WEAK_EVIDENCE,), benchmark_only=False):
    return create_episode_from_answer_trace(_answer_trace(risk_flags=risk_flags), benchmark_only=benchmark_only)


def test_importing_new_modules_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False


def test_can_create_episode_trace_from_answer_trace():
    episode = _episode()

    assert episode.source_trace_id == "trace-episode-test"
    assert episode.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE
    assert episode.replay_intent == EpisodeReplayIntent.REVIEW_EVIDENCE_USE
    assert validate_episode_is_non_mutating(episode)


def test_benchmark_only_answer_trace_creates_do_not_train_episode():
    episode = _episode(benchmark_only=True)

    assert episode.benchmark_only
    assert episode.replay_status == EpisodeReplayStatus.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert episode.replay_intent == EpisodeReplayIntent.NO_REPLAY


def test_safety_risk_episode_requires_human_review():
    episode = _episode(risk_flags=(TraceRiskFlag.UNSAFE_ACTION,))

    assert episode.human_review_required
    assert episode.replay_status == EpisodeReplayStatus.REQUIRES_HUMAN_REVIEW
    assert episode.replay_intent == EpisodeReplayIntent.REVIEW_SAFETY


def test_weak_or_conflicting_evidence_can_become_replay_candidate():
    weak = _episode(risk_flags=(TraceRiskFlag.WEAK_EVIDENCE,))
    conflicting = _episode(risk_flags=(TraceRiskFlag.CONFLICTING_EVIDENCE,))

    assert weak.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE
    assert conflicting.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE


def test_episode_attachment_functions_return_updated_values():
    episode = _episode()
    with_feedback = attach_feedback_to_episode(episode, "feedback-1")
    with_marker = attach_replay_marker_to_episode(with_feedback, "marker-1")

    assert episode.attached_feedback_ids == ()
    assert with_feedback.attached_feedback_ids == ("feedback-1",)
    assert with_marker.attached_replay_marker_ids == ("marker-1",)


def test_episode_summary_is_report_only():
    summary = summarize_episode_for_report(_episode())

    assert summary["non_mutating"] is True
    assert summary["replay_status"] == "replay_candidate"


def test_feedback_can_be_created_from_answer_trace():
    record = capture_feedback_from_trace(
        _answer_trace(),
        source=FeedbackSource.USER_EXPLICIT,
        polarity=FeedbackPolarity.CORRECTS,
        severity=FeedbackSeverity.MEDIUM,
        target=FeedbackTarget.FINAL_ANSWER,
        feedback_text="Correction.",
    )

    assert record.trace_id == "trace-episode-test"
    assert record.episode_id == ""
    assert record.proposed_disposition == FeedbackDisposition.ELIGIBLE_FOR_REPLAY


def test_feedback_can_be_created_from_episode_trace():
    episode = _episode()
    record = capture_feedback_from_episode(
        episode,
        source=FeedbackSource.USER_EXPLICIT,
        polarity=FeedbackPolarity.REJECTS,
        severity=FeedbackSeverity.HIGH,
        target=FeedbackTarget.EPISODE_BOUNDARY,
        feedback_text="The episode boundary is wrong.",
    )

    assert record.episode_id == episode.episode_id
    assert record.trace_id == episode.source_trace_id
    assert record.proposed_disposition == FeedbackDisposition.ELIGIBLE_FOR_REPLAY


def test_feedback_training_safe_is_false_for_v14d_records():
    record = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.EVIDENCE_USE,
        "Correction.",
    )

    assert is_feedback_training_safe(record) is False


def test_benchmark_only_feedback_forces_do_not_train():
    record = capture_feedback_from_trace(
        _answer_trace(),
        FeedbackSource.BENCHMARK_REPORT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.HIGH,
        FeedbackTarget.FINAL_ANSWER,
        "Benchmark-only.",
        benchmark_only=True,
    )

    assert record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert record.benchmark_only


def test_critical_and_safety_feedback_require_human_review():
    critical = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.HUMAN_REVIEW,
        FeedbackPolarity.REJECTS,
        FeedbackSeverity.CRITICAL,
        FeedbackTarget.FINAL_ANSWER,
        "Critical issue.",
    )
    safety = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.MODEL_SELF_CHECK,
        FeedbackPolarity.FLAGS_SAFETY_RISK,
        FeedbackSeverity.HIGH,
        FeedbackTarget.PLANNING_LANE,
        "Unsafe action risk.",
    )

    assert requires_human_review(critical)
    assert requires_human_review(safety)


def test_noise_feedback_with_affected_concept_becomes_pruning_review_candidate():
    record = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.EVALUATOR_REPORT,
        FeedbackPolarity.FLAGS_NOISE,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.REASONING_LANE,
        "Same-topic noise.",
        affected_concepts=("concept-noise",),
        affected_lanes=(RuntimeLane.REASONING,),
    )

    assert record.proposed_disposition == FeedbackDisposition.PRUNING_REVIEW_CANDIDATE


def test_summarize_feedback_records_includes_episode_id():
    episode = _episode()
    record = capture_feedback_from_episode(
        episode,
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.FINAL_ANSWER,
        "Correction.",
    )
    summary = summarize_feedback_records([record])

    assert summary.episode_id == episode.episode_id
    assert summary.feedback_count == 1


def test_feedback_to_event_draft_is_non_mutating():
    record = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.EVIDENCE_USE,
        "Correction.",
    )
    draft = feedback_to_event_draft(record)

    assert draft.proposed_replay_eligibility == ReplayEligibility.ELIGIBLE_FOR_REVIEW
    assert draft.proposed_pruning_review is False


def test_user_correction_and_rejection_create_replay_markers():
    correction = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.CORRECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.FINAL_ANSWER,
        "Correction.",
    )
    rejection = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.USER_EXPLICIT,
        FeedbackPolarity.REJECTS,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.FINAL_ANSWER,
        "Rejected.",
    )

    assert create_replay_marker_from_feedback(correction).reason == ReplayReason.USER_CORRECTION
    assert create_replay_marker_from_feedback(rejection).reason == ReplayReason.USER_REJECTION


def test_episode_can_create_replay_marker():
    episode = _episode()
    marker = create_replay_marker_from_episode(episode)

    assert marker.episode_id == episode.episode_id
    assert marker.eligibility == ReplayEligibility.ELIGIBLE_FOR_REVIEW
    assert marker.status == ReplayMarkerStatus.PROPOSED


def test_benchmark_only_creates_do_not_train_marker_and_is_not_queued():
    episode = _episode(benchmark_only=True)
    marker = create_replay_marker_from_episode(episode)

    assert marker.eligibility == ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert marker.status == ReplayMarkerStatus.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert should_queue_for_replay(episode) is False


def test_critical_safety_risk_marker_requires_human_review():
    episode = _episode(risk_flags=(TraceRiskFlag.UNSAFE_ACTION,))
    marker = create_replay_marker_from_episode(episode)

    assert marker.eligibility == ReplayEligibility.REQUIRES_HUMAN_REVIEW
    assert marker.status == ReplayMarkerStatus.REQUIRES_HUMAN_REVIEW
    assert classify_replay_priority(episode) == ReplayPriority.CRITICAL


def test_same_topic_noise_produces_dampen_or_require_context_review_proposal():
    record = capture_feedback_from_episode(
        _episode(),
        FeedbackSource.EVALUATOR_REPORT,
        FeedbackPolarity.FLAGS_NOISE,
        FeedbackSeverity.MEDIUM,
        FeedbackTarget.REASONING_LANE,
        "Same-topic noise.",
        affected_concepts=("concept-noise",),
        affected_lanes=(RuntimeLane.REASONING,),
    )

    proposals = feedback_to_pruning_review_proposals(record)

    assert proposals
    assert proposals[0].failure_type == PruningFailureType.SAME_TOPIC_NOISE
    assert proposals[0].corrective_action in {CorrectiveAction.DAMPEN, CorrectiveAction.REQUIRE_CONTEXT}
    assert proposals[0].episode_id == record.episode_id
    assert validate_pruning_proposal_non_mutating(proposals[0])


def test_low_severity_one_off_feedback_does_not_propose_quarantine():
    record = capture_feedback_from_episode(
        _episode(),
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
        _answer_trace(),
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
    record = capture_feedback_from_episode(
        _episode(),
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


def test_all_normal_pruning_review_proposals_are_reversible():
    record = capture_feedback_from_episode(
        _episode(),
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


def test_write_feedback_capture_report_creates_episodic_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14d_episodic_feedback_capture_scaffold.md"
    json_path = tmp_path / "runtime_v14d_episodic_feedback_capture_scaffold.json"

    write_feedback_capture_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_SLEEP_REPLAY_CONSOLIDATION_DESIGN"
    assert data["original_delta_path_trace"]["old_engine_runtime_adopted_directly"] is False
    assert "old `G:\\Delta_DevV0\\engine\\runtime.py` was not adopted directly" in text
    assert "observation -> episodic boundary -> episode trace -> episode replay" in text
