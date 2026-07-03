from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from orchestration.runtime.v14_episode import EpisodeReplayStatus, EpisodeTrace, replay_status_to_eligibility
from orchestration.runtime.v14_feedback import (
    FeedbackCaptureRecord,
    FeedbackDisposition,
    FeedbackPolarity,
    FeedbackSeverity,
)
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_trace import ReplayEligibility


class ReplayPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReplayReason(str, Enum):
    USER_CORRECTION = "user_correction"
    USER_REJECTION = "user_rejection"
    REJECTED_ANSWER = "rejected_answer"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    SAME_TOPIC_NOISE = "same_topic_noise"
    UNSAFE_ACTION_RISK = "unsafe_action_risk"
    SPECIALIST_NEEDED = "specialist_needed"
    CONFIDENCE_MISMATCH = "confidence_mismatch"
    EPISODE_BOUNDARY_REVIEW = "episode_boundary_review"
    BENCHMARK_ONLY = "benchmark_only"
    UNKNOWN = "unknown"


class ReplayMarkerStatus(str, Enum):
    PROPOSED = "proposed"
    QUEUED = "queued"
    REJECTED = "rejected"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BENCHMARK_ONLY_DO_NOT_TRAIN = "benchmark_only_do_not_train"


@dataclass(frozen=True)
class ReplayReviewMarker:
    marker_id: str
    trace_id: str
    episode_id: str
    feedback_id: str
    eligibility: ReplayEligibility
    priority: ReplayPriority
    reason: ReplayReason
    status: ReplayMarkerStatus
    affected_concepts: tuple[str, ...] = ()
    affected_lanes: tuple[RuntimeLane | str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "marker_id": self.marker_id,
            "trace_id": self.trace_id,
            "episode_id": self.episode_id,
            "feedback_id": self.feedback_id,
            "eligibility": self.eligibility.value,
            "priority": self.priority.value,
            "reason": self.reason.value,
            "status": self.status.value,
            "affected_concepts": list(self.affected_concepts),
            "affected_lanes": [_lane_value(lane) for lane in self.affected_lanes],
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_replay_marker_from_feedback(record: FeedbackCaptureRecord) -> ReplayReviewMarker:
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return mark_benchmark_only(record)
    reason = classify_replay_reason(record)
    priority = classify_replay_priority(record)
    if record.human_review_required:
        eligibility = ReplayEligibility.REQUIRES_HUMAN_REVIEW
        status = ReplayMarkerStatus.REQUIRES_HUMAN_REVIEW
    elif should_queue_for_replay(record):
        eligibility = ReplayEligibility.ELIGIBLE_FOR_REPLAY
        status = ReplayMarkerStatus.PROPOSED
    else:
        eligibility = ReplayEligibility.NOT_ELIGIBLE
        status = ReplayMarkerStatus.REJECTED
    return ReplayReviewMarker(
        marker_id=f"replay-marker-{uuid4().hex}",
        trace_id=record.trace_id,
        episode_id=record.episode_id,
        feedback_id=record.feedback_id,
        eligibility=eligibility,
        priority=priority,
        reason=reason,
        status=status,
        affected_concepts=record.affected_concepts,
        affected_lanes=record.affected_lanes,
        notes="replay marker only; replay not executed",
    )


def create_replay_marker_from_episode(
    episode: EpisodeTrace,
    reason: ReplayReason | None = None,
    notes: str | None = None,
) -> ReplayReviewMarker:
    if episode.benchmark_only or episode.replay_status == EpisodeReplayStatus.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return mark_benchmark_only(episode)
    eligibility = replay_status_to_eligibility(episode.replay_status)
    if episode.replay_status == EpisodeReplayStatus.REQUIRES_HUMAN_REVIEW:
        status = ReplayMarkerStatus.REQUIRES_HUMAN_REVIEW
    elif episode.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE:
        status = ReplayMarkerStatus.PROPOSED
    else:
        status = ReplayMarkerStatus.REJECTED
    return ReplayReviewMarker(
        marker_id=f"replay-marker-{uuid4().hex}",
        trace_id=episode.source_trace_id,
        episode_id=episode.episode_id,
        feedback_id="",
        eligibility=eligibility,
        priority=classify_replay_priority(episode),
        reason=reason or classify_replay_reason(episode),
        status=status,
        affected_concepts=(),
        affected_lanes=(),
        notes=notes or "episode replay marker only; replay not executed",
    )


def classify_replay_reason(record_or_episode: FeedbackCaptureRecord | EpisodeTrace) -> ReplayReason:
    if isinstance(record_or_episode, EpisodeTrace):
        episode = record_or_episode
        if episode.benchmark_only:
            return ReplayReason.BENCHMARK_ONLY
        if episode.replay_status == EpisodeReplayStatus.REQUIRES_HUMAN_REVIEW:
            return ReplayReason.UNSAFE_ACTION_RISK
        if episode.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE:
            return ReplayReason.EPISODE_BOUNDARY_REVIEW
        return ReplayReason.UNKNOWN
    record = record_or_episode
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return ReplayReason.BENCHMARK_ONLY
    if record.polarity == FeedbackPolarity.CORRECTS:
        return ReplayReason.USER_CORRECTION
    if record.polarity == FeedbackPolarity.REJECTS:
        return ReplayReason.USER_REJECTION
    if record.polarity == FeedbackPolarity.ASKS_FOR_MORE_EVIDENCE:
        return ReplayReason.INSUFFICIENT_EVIDENCE
    if record.polarity == FeedbackPolarity.FLAGS_NOISE:
        return ReplayReason.SAME_TOPIC_NOISE
    if record.polarity == FeedbackPolarity.FLAGS_SAFETY_RISK:
        return ReplayReason.UNSAFE_ACTION_RISK
    if record.polarity == FeedbackPolarity.FLAGS_UNCERTAINTY:
        return ReplayReason.CONFIDENCE_MISMATCH
    return ReplayReason.UNKNOWN


def classify_replay_priority(record_or_episode: FeedbackCaptureRecord | EpisodeTrace) -> ReplayPriority:
    if isinstance(record_or_episode, EpisodeTrace):
        if record_or_episode.human_review_required:
            return ReplayPriority.CRITICAL
        if record_or_episode.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE:
            return ReplayPriority.MEDIUM
        return ReplayPriority.LOW
    record = record_or_episode
    if record.severity == FeedbackSeverity.CRITICAL:
        return ReplayPriority.CRITICAL
    if record.severity == FeedbackSeverity.HIGH:
        return ReplayPriority.HIGH
    if record.severity == FeedbackSeverity.MEDIUM:
        return ReplayPriority.MEDIUM
    return ReplayPriority.LOW


def should_queue_for_replay(record_or_episode: FeedbackCaptureRecord | EpisodeTrace) -> bool:
    if isinstance(record_or_episode, EpisodeTrace):
        return record_or_episode.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE and not record_or_episode.benchmark_only
    record = record_or_episode
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return False
    if record.human_review_required:
        return False
    return record.proposed_disposition in {
        FeedbackDisposition.ELIGIBLE_FOR_REPLAY,
        FeedbackDisposition.PRUNING_REVIEW_CANDIDATE,
    }


def mark_benchmark_only(record_or_episode: FeedbackCaptureRecord | EpisodeTrace) -> ReplayReviewMarker:
    if isinstance(record_or_episode, EpisodeTrace):
        return ReplayReviewMarker(
            marker_id=f"replay-marker-{uuid4().hex}",
            trace_id=record_or_episode.source_trace_id,
            episode_id=record_or_episode.episode_id,
            feedback_id="",
            eligibility=ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN,
            priority=ReplayPriority.LOW,
            reason=ReplayReason.BENCHMARK_ONLY,
            status=ReplayMarkerStatus.BENCHMARK_ONLY_DO_NOT_TRAIN,
            affected_concepts=(),
            affected_lanes=(),
            notes="benchmark-only episode must not become training material",
        )
    record = record_or_episode
    return ReplayReviewMarker(
        marker_id=f"replay-marker-{uuid4().hex}",
        trace_id=record.trace_id,
        episode_id=record.episode_id,
        feedback_id=record.feedback_id,
        eligibility=ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN,
        priority=ReplayPriority.LOW,
        reason=ReplayReason.BENCHMARK_ONLY,
        status=ReplayMarkerStatus.BENCHMARK_ONLY_DO_NOT_TRAIN,
        affected_concepts=record.affected_concepts,
        affected_lanes=record.affected_lanes,
        notes="benchmark-only feedback must not become training material",
    )


def _lane_value(lane: RuntimeLane | str) -> str:
    return lane.value if isinstance(lane, RuntimeLane) else str(lane)
