from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from orchestration.runtime.v14_episode import EpisodeTrace
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_trace import (
    AnswerTrace,
    FeedbackEventDraft,
    FeedbackSignalType,
    ReplayEligibility,
    TraceRiskFlag,
)


class FeedbackSource(str, Enum):
    USER_EXPLICIT = "user_explicit"
    USER_IMPLICIT = "user_implicit"
    MODEL_SELF_CHECK = "model_self_check"
    EVALUATOR_REPORT = "evaluator_report"
    SPECIALIST_DRAFT = "specialist_draft"
    BENCHMARK_REPORT = "benchmark_report"
    HUMAN_REVIEW = "human_review"
    UNKNOWN = "unknown"


class FeedbackPolarity(str, Enum):
    CONFIRMS = "confirms"
    CORRECTS = "corrects"
    REJECTS = "rejects"
    ASKS_FOR_MORE_EVIDENCE = "asks_for_more_evidence"
    FLAGS_UNCERTAINTY = "flags_uncertainty"
    FLAGS_SAFETY_RISK = "flags_safety_risk"
    FLAGS_NOISE = "flags_noise"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class FeedbackSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class FeedbackTarget(str, Enum):
    FINAL_ANSWER = "final_answer"
    EVIDENCE_USE = "evidence_use"
    REASONING_LANE = "reasoning_lane"
    PLANNING_LANE = "planning_lane"
    RESPONSE_LANE = "response_lane"
    SPECIALIST_ROUTE = "specialist_route"
    UNCERTAINTY_MODE = "uncertainty_mode"
    CONCEPT_USAGE = "concept_usage"
    EPISODE_BOUNDARY = "episode_boundary"
    UNKNOWN = "unknown"


class FeedbackDisposition(str, Enum):
    RECORD_ONLY = "record_only"
    ELIGIBLE_FOR_REPLAY = "eligible_for_replay"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    PRUNING_REVIEW_CANDIDATE = "pruning_review_candidate"
    BENCHMARK_ONLY_DO_NOT_TRAIN = "benchmark_only_do_not_train"
    IGNORE_NO_ACTION = "ignore_no_action"


@dataclass(frozen=True)
class FeedbackCaptureRecord:
    feedback_id: str
    trace_id: str
    episode_id: str
    source: FeedbackSource
    polarity: FeedbackPolarity
    severity: FeedbackSeverity
    target: FeedbackTarget
    feedback_text: str = ""
    affected_concepts: tuple[str, ...] = ()
    affected_lanes: tuple[RuntimeLane | str, ...] = ()
    evidence_snapshot: dict[str, object] = field(default_factory=dict)
    proposed_disposition: FeedbackDisposition = FeedbackDisposition.RECORD_ONLY
    human_review_required: bool = False
    benchmark_only: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "feedback_id": self.feedback_id,
            "trace_id": self.trace_id,
            "episode_id": self.episode_id,
            "source": self.source.value,
            "polarity": self.polarity.value,
            "severity": self.severity.value,
            "target": self.target.value,
            "feedback_text": self.feedback_text,
            "affected_concepts": list(self.affected_concepts),
            "affected_lanes": [_lane_value(lane) for lane in self.affected_lanes],
            "evidence_snapshot": self.evidence_snapshot,
            "proposed_disposition": self.proposed_disposition.value,
            "human_review_required": self.human_review_required,
            "benchmark_only": self.benchmark_only,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FeedbackCaptureSummary:
    trace_id: str
    episode_id: str
    feedback_count: int
    highest_severity: FeedbackSeverity
    replay_candidate_count: int
    pruning_review_candidate_count: int
    human_review_required: bool
    benchmark_only_count: int
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "episode_id": self.episode_id,
            "feedback_count": self.feedback_count,
            "highest_severity": self.highest_severity.value,
            "replay_candidate_count": self.replay_candidate_count,
            "pruning_review_candidate_count": self.pruning_review_candidate_count,
            "human_review_required": self.human_review_required,
            "benchmark_only_count": self.benchmark_only_count,
            "notes": self.notes,
        }


def capture_feedback_from_trace(
    answer_trace: AnswerTrace,
    source: FeedbackSource,
    polarity: FeedbackPolarity,
    severity: FeedbackSeverity,
    target: FeedbackTarget,
    feedback_text: str,
    affected_concepts: tuple[str, ...] | None = None,
    affected_lanes: tuple[RuntimeLane | str, ...] | None = None,
    evidence_snapshot: dict[str, object] | None = None,
    benchmark_only: bool = False,
    human_review_required: bool | None = None,
    notes: str | None = None,
) -> FeedbackCaptureRecord:
    concepts = affected_concepts or ()
    lanes = affected_lanes or ()
    disposition = _classify_disposition_from_fields(
        polarity=polarity,
        severity=severity,
        affected_concepts=concepts,
        benchmark_only=benchmark_only,
        human_review_required=human_review_required,
    )
    review_required = _human_review_from_fields(
        polarity=polarity,
        severity=severity,
        disposition=disposition,
        explicit=human_review_required,
    )
    return FeedbackCaptureRecord(
        feedback_id=f"feedback-{uuid4().hex}",
        trace_id=answer_trace.trace_id,
        episode_id="",
        source=source,
        polarity=polarity,
        severity=severity,
        target=target,
        feedback_text=feedback_text,
        affected_concepts=concepts,
        affected_lanes=lanes,
        evidence_snapshot=evidence_snapshot or answer_trace.as_dict(),
        proposed_disposition=disposition,
        human_review_required=review_required,
        benchmark_only=benchmark_only,
        notes=notes or "",
    )


def capture_feedback_from_episode(
    episode: EpisodeTrace,
    source: FeedbackSource,
    polarity: FeedbackPolarity,
    severity: FeedbackSeverity,
    target: FeedbackTarget,
    feedback_text: str,
    affected_concepts: tuple[str, ...] | None = None,
    affected_lanes: tuple[RuntimeLane | str, ...] | None = None,
    evidence_snapshot: dict[str, object] | None = None,
    human_review_required: bool | None = None,
    notes: str | None = None,
) -> FeedbackCaptureRecord:
    concepts = affected_concepts or ()
    lanes = affected_lanes or ()
    disposition = _classify_disposition_from_fields(
        polarity=polarity,
        severity=severity,
        affected_concepts=concepts,
        benchmark_only=episode.benchmark_only,
        human_review_required=human_review_required,
    )
    review_required = episode.human_review_required or _human_review_from_fields(
        polarity=polarity,
        severity=severity,
        disposition=disposition,
        explicit=human_review_required,
    )
    return FeedbackCaptureRecord(
        feedback_id=f"feedback-{uuid4().hex}",
        trace_id=episode.source_trace_id,
        episode_id=episode.episode_id,
        source=source,
        polarity=polarity,
        severity=severity,
        target=target,
        feedback_text=feedback_text,
        affected_concepts=concepts,
        affected_lanes=lanes,
        evidence_snapshot=evidence_snapshot or episode.as_dict(),
        proposed_disposition=disposition,
        human_review_required=review_required,
        benchmark_only=episode.benchmark_only,
        notes=notes or "",
    )


def summarize_feedback_records(records: tuple[FeedbackCaptureRecord, ...] | list[FeedbackCaptureRecord]) -> FeedbackCaptureSummary:
    if not records:
        return FeedbackCaptureSummary(
            trace_id="",
            episode_id="",
            feedback_count=0,
            highest_severity=FeedbackSeverity.UNKNOWN,
            replay_candidate_count=0,
            pruning_review_candidate_count=0,
            human_review_required=False,
            benchmark_only_count=0,
            notes="no feedback records",
        )
    first_trace_id = records[0].trace_id
    first_episode_id = records[0].episode_id
    return FeedbackCaptureSummary(
        trace_id=first_trace_id,
        episode_id=first_episode_id,
        feedback_count=len(records),
        highest_severity=max((record.severity for record in records), key=_severity_rank),
        replay_candidate_count=sum(
            record.proposed_disposition == FeedbackDisposition.ELIGIBLE_FOR_REPLAY for record in records
        ),
        pruning_review_candidate_count=sum(
            record.proposed_disposition == FeedbackDisposition.PRUNING_REVIEW_CANDIDATE for record in records
        ),
        human_review_required=any(record.human_review_required for record in records),
        benchmark_only_count=sum(
            record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN for record in records
        ),
        notes="summary is report-only; no memory mutation performed",
    )


def feedback_to_event_draft(record: FeedbackCaptureRecord) -> FeedbackEventDraft:
    signal_type = _signal_type_for_feedback(record)
    return FeedbackEventDraft(
        trace_id=record.trace_id,
        signal_type=signal_type,
        feedback_text=record.feedback_text,
        affected_concepts=record.affected_concepts,
        proposed_replay_eligibility=_replay_eligibility_for_disposition(record.proposed_disposition),
        proposed_pruning_review=record.proposed_disposition == FeedbackDisposition.PRUNING_REVIEW_CANDIDATE,
        human_review_required=record.human_review_required,
    )


def is_feedback_training_safe(record: FeedbackCaptureRecord) -> bool:
    return False


def requires_human_review(record: FeedbackCaptureRecord) -> bool:
    return record.human_review_required


def classify_feedback_disposition(record: FeedbackCaptureRecord) -> FeedbackDisposition:
    return record.proposed_disposition


def _classify_disposition_from_fields(
    *,
    polarity: FeedbackPolarity,
    severity: FeedbackSeverity,
    affected_concepts: tuple[str, ...],
    benchmark_only: bool,
    human_review_required: bool | None,
) -> FeedbackDisposition:
    if benchmark_only:
        return FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN
    if human_review_required or severity == FeedbackSeverity.CRITICAL or polarity == FeedbackPolarity.FLAGS_SAFETY_RISK:
        return FeedbackDisposition.REQUIRES_HUMAN_REVIEW
    if polarity in {FeedbackPolarity.CORRECTS, FeedbackPolarity.REJECTS, FeedbackPolarity.ASKS_FOR_MORE_EVIDENCE}:
        return FeedbackDisposition.ELIGIBLE_FOR_REPLAY
    if polarity == FeedbackPolarity.FLAGS_NOISE and affected_concepts:
        return FeedbackDisposition.PRUNING_REVIEW_CANDIDATE
    if polarity == FeedbackPolarity.NEUTRAL:
        return FeedbackDisposition.RECORD_ONLY
    if polarity == FeedbackPolarity.UNKNOWN:
        return FeedbackDisposition.IGNORE_NO_ACTION
    return FeedbackDisposition.RECORD_ONLY


def _human_review_from_fields(
    *,
    polarity: FeedbackPolarity,
    severity: FeedbackSeverity,
    disposition: FeedbackDisposition,
    explicit: bool | None,
) -> bool:
    if explicit is not None:
        return explicit
    return (
        severity == FeedbackSeverity.CRITICAL
        or polarity == FeedbackPolarity.FLAGS_SAFETY_RISK
        or disposition == FeedbackDisposition.REQUIRES_HUMAN_REVIEW
    )


def _signal_type_for_feedback(record: FeedbackCaptureRecord) -> FeedbackSignalType:
    if record.polarity == FeedbackPolarity.CONFIRMS:
        return FeedbackSignalType.USER_CONFIRMED
    if record.polarity == FeedbackPolarity.CORRECTS:
        return FeedbackSignalType.USER_CORRECTED
    if record.polarity == FeedbackPolarity.REJECTS:
        return FeedbackSignalType.USER_REJECTED
    if record.polarity == FeedbackPolarity.ASKS_FOR_MORE_EVIDENCE:
        return FeedbackSignalType.USER_REQUESTED_MORE_EVIDENCE
    if record.polarity == FeedbackPolarity.FLAGS_UNCERTAINTY:
        return FeedbackSignalType.MODEL_SELF_FLAGGED_UNCERTAINTY
    if record.polarity == FeedbackPolarity.FLAGS_SAFETY_RISK:
        return FeedbackSignalType.UNSAFE_OR_ACTIONABLE_RISK
    return FeedbackSignalType.UNKNOWN


def _replay_eligibility_for_disposition(disposition: FeedbackDisposition) -> ReplayEligibility:
    if disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN
    if disposition == FeedbackDisposition.REQUIRES_HUMAN_REVIEW:
        return ReplayEligibility.REQUIRES_HUMAN_REVIEW
    if disposition in {FeedbackDisposition.ELIGIBLE_FOR_REPLAY, FeedbackDisposition.PRUNING_REVIEW_CANDIDATE}:
        return ReplayEligibility.ELIGIBLE_FOR_REVIEW
    return ReplayEligibility.NOT_ELIGIBLE


def _severity_rank(severity: FeedbackSeverity) -> int:
    return {
        FeedbackSeverity.LOW: 1,
        FeedbackSeverity.MEDIUM: 2,
        FeedbackSeverity.HIGH: 3,
        FeedbackSeverity.CRITICAL: 4,
        FeedbackSeverity.UNKNOWN: 0,
    }[severity]


def _lane_value(lane: RuntimeLane | str) -> str:
    return lane.value if isinstance(lane, RuntimeLane) else str(lane)
