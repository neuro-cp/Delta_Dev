from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from orchestration.runtime.v14_trace import AnswerTrace, ReplayEligibility, TraceRiskFlag


class ObservationBoundary(str, Enum):
    USER_QUERY = "user_query"
    MODEL_ANSWER = "model_answer"
    USER_FEEDBACK = "user_feedback"
    MODEL_SELF_CHECK = "model_self_check"
    EVALUATOR_REPORT = "evaluator_report"
    BENCHMARK_CASE = "benchmark_case"
    SPECIALIST_DRAFT = "specialist_draft"
    EXTERNAL_OBSERVATION = "external_observation"
    UNKNOWN = "unknown"


class EpisodeBoundaryReason(str, Enum):
    NEW_QUESTION = "new_question"
    ANSWER_COMPLETED = "answer_completed"
    USER_CORRECTION = "user_correction"
    USER_REJECTION = "user_rejection"
    UNCERTAINTY_FLAGGED = "uncertainty_flagged"
    SAFETY_RISK_FLAGGED = "safety_risk_flagged"
    NOISE_DETECTED = "noise_detected"
    SPECIALIST_NEEDED = "specialist_needed"
    BENCHMARK_ONLY = "benchmark_only"
    MANUAL_BOUNDARY = "manual_boundary"
    UNKNOWN = "unknown"


class EpisodeReplayStatus(str, Enum):
    NOT_REPLAYABLE = "not_replayable"
    REPLAY_CANDIDATE = "replay_candidate"
    REPLAY_QUEUED = "replay_queued"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BENCHMARK_ONLY_DO_NOT_TRAIN = "benchmark_only_do_not_train"


class EpisodeReplayIntent(str, Enum):
    REVIEW_EVIDENCE_USE = "review_evidence_use"
    REVIEW_REASONING_LANE = "review_reasoning_lane"
    REVIEW_PLANNING_LANE = "review_planning_lane"
    REVIEW_RESPONSE_LANE = "review_response_lane"
    REVIEW_UNCERTAINTY = "review_uncertainty"
    REVIEW_NOISE = "review_noise"
    REVIEW_SAFETY = "review_safety"
    REVIEW_SPECIALIST_ROUTE = "review_specialist_route"
    NO_REPLAY = "no_replay"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EpisodeTrace:
    episode_id: str
    source_trace_id: str
    observation_boundary: ObservationBoundary
    boundary_reason: EpisodeBoundaryReason
    replay_status: EpisodeReplayStatus
    replay_intent: EpisodeReplayIntent
    question: str = ""
    answer_summary: str = ""
    evidence_trace_count: int = 0
    risk_flags: tuple[TraceRiskFlag, ...] = (TraceRiskFlag.NONE,)
    confidence: float = 0.0
    uncertainty_reason: str = ""
    attached_feedback_ids: tuple[str, ...] = ()
    attached_replay_marker_ids: tuple[str, ...] = ()
    benchmark_only: bool = False
    human_review_required: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "source_trace_id": self.source_trace_id,
            "observation_boundary": self.observation_boundary.value,
            "boundary_reason": self.boundary_reason.value,
            "replay_status": self.replay_status.value,
            "replay_intent": self.replay_intent.value,
            "question": self.question,
            "answer_summary": self.answer_summary,
            "evidence_trace_count": self.evidence_trace_count,
            "risk_flags": [flag.value for flag in self.risk_flags],
            "confidence": self.normalized_confidence(),
            "uncertainty_reason": self.uncertainty_reason,
            "attached_feedback_ids": list(self.attached_feedback_ids),
            "attached_replay_marker_ids": list(self.attached_replay_marker_ids),
            "benchmark_only": self.benchmark_only,
            "human_review_required": self.human_review_required,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_episode_from_answer_trace(
    answer_trace: AnswerTrace,
    boundary_reason: EpisodeBoundaryReason | None = None,
    benchmark_only: bool = False,
    notes: str | None = None,
) -> EpisodeTrace:
    reason = boundary_reason or _boundary_reason_from_trace(answer_trace, benchmark_only=benchmark_only)
    risk_flags = tuple(answer_trace.risk_flags)
    human_review = TraceRiskFlag.UNSAFE_ACTION in risk_flags
    episode = EpisodeTrace(
        episode_id=f"episode-{uuid4().hex}",
        source_trace_id=answer_trace.trace_id,
        observation_boundary=ObservationBoundary.BENCHMARK_CASE if benchmark_only else ObservationBoundary.MODEL_ANSWER,
        boundary_reason=reason,
        replay_status=EpisodeReplayStatus.NOT_REPLAYABLE,
        replay_intent=EpisodeReplayIntent.NO_REPLAY,
        question=answer_trace.question,
        answer_summary=answer_trace.final_answer_summary,
        evidence_trace_count=len(answer_trace.evidence_traces),
        risk_flags=risk_flags,
        confidence=answer_trace.normalized_confidence(),
        uncertainty_reason=answer_trace.uncertainty_reason,
        benchmark_only=benchmark_only,
        human_review_required=human_review,
        notes=notes or "episode trace is observational only; no replay executed",
    )
    return replace(
        episode,
        replay_status=classify_episode_replay_status(episode),
        replay_intent=classify_episode_replay_intent(episode),
    )


def attach_feedback_to_episode(episode: EpisodeTrace, feedback_id: str) -> EpisodeTrace:
    return replace(episode, attached_feedback_ids=(*episode.attached_feedback_ids, feedback_id))


def attach_replay_marker_to_episode(episode: EpisodeTrace, marker_id: str) -> EpisodeTrace:
    return replace(episode, attached_replay_marker_ids=(*episode.attached_replay_marker_ids, marker_id))


def classify_episode_replay_status(episode: EpisodeTrace) -> EpisodeReplayStatus:
    if episode.benchmark_only or episode.boundary_reason == EpisodeBoundaryReason.BENCHMARK_ONLY:
        return EpisodeReplayStatus.BENCHMARK_ONLY_DO_NOT_TRAIN
    if episode.human_review_required or TraceRiskFlag.UNSAFE_ACTION in episode.risk_flags:
        return EpisodeReplayStatus.REQUIRES_HUMAN_REVIEW
    if any(
        flag in episode.risk_flags
        for flag in (
            TraceRiskFlag.WEAK_EVIDENCE,
            TraceRiskFlag.CONFLICTING_EVIDENCE,
            TraceRiskFlag.SAME_TOPIC_NOISE,
            TraceRiskFlag.UNSUPPORTED_CLAIM,
            TraceRiskFlag.SPECIALIST_NEEDED,
            TraceRiskFlag.OVERCONFIDENCE_RISK,
        )
    ):
        return EpisodeReplayStatus.REPLAY_CANDIDATE
    return EpisodeReplayStatus.NOT_REPLAYABLE


def classify_episode_replay_intent(episode: EpisodeTrace) -> EpisodeReplayIntent:
    if episode.benchmark_only:
        return EpisodeReplayIntent.NO_REPLAY
    if TraceRiskFlag.UNSAFE_ACTION in episode.risk_flags:
        return EpisodeReplayIntent.REVIEW_SAFETY
    if TraceRiskFlag.SAME_TOPIC_NOISE in episode.risk_flags:
        return EpisodeReplayIntent.REVIEW_NOISE
    if TraceRiskFlag.SPECIALIST_NEEDED in episode.risk_flags:
        return EpisodeReplayIntent.REVIEW_SPECIALIST_ROUTE
    if TraceRiskFlag.WEAK_EVIDENCE in episode.risk_flags or TraceRiskFlag.CONFLICTING_EVIDENCE in episode.risk_flags:
        return EpisodeReplayIntent.REVIEW_EVIDENCE_USE
    if TraceRiskFlag.OVERCONFIDENCE_RISK in episode.risk_flags:
        return EpisodeReplayIntent.REVIEW_UNCERTAINTY
    return EpisodeReplayIntent.NO_REPLAY


def validate_episode_is_non_mutating(episode: EpisodeTrace) -> bool:
    payload = episode.as_dict()
    forbidden_keys = {
        "train",
        "trained",
        "prune",
        "pruned",
        "mutate",
        "mutated",
        "promote",
        "promoted",
        "delete",
        "deleted",
        "provider_called",
        "replay_executed",
    }
    return not any(key in payload for key in forbidden_keys)


def summarize_episode_for_report(episode: EpisodeTrace) -> dict[str, object]:
    return {
        "episode_id": episode.episode_id,
        "source_trace_id": episode.source_trace_id,
        "boundary_reason": episode.boundary_reason.value,
        "replay_status": episode.replay_status.value,
        "replay_intent": episode.replay_intent.value,
        "risk_flags": [flag.value for flag in episode.risk_flags],
        "benchmark_only": episode.benchmark_only,
        "human_review_required": episode.human_review_required,
        "feedback_count": len(episode.attached_feedback_ids),
        "replay_marker_count": len(episode.attached_replay_marker_ids),
        "non_mutating": validate_episode_is_non_mutating(episode),
    }


def replay_status_to_eligibility(status: EpisodeReplayStatus) -> ReplayEligibility:
    if status == EpisodeReplayStatus.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN
    if status == EpisodeReplayStatus.REQUIRES_HUMAN_REVIEW:
        return ReplayEligibility.REQUIRES_HUMAN_REVIEW
    if status in {EpisodeReplayStatus.REPLAY_CANDIDATE, EpisodeReplayStatus.REPLAY_QUEUED}:
        return ReplayEligibility.ELIGIBLE_FOR_REVIEW
    return ReplayEligibility.NOT_ELIGIBLE


def _boundary_reason_from_trace(answer_trace: AnswerTrace, *, benchmark_only: bool) -> EpisodeBoundaryReason:
    if benchmark_only:
        return EpisodeBoundaryReason.BENCHMARK_ONLY
    risk_flags = tuple(answer_trace.risk_flags)
    if TraceRiskFlag.UNSAFE_ACTION in risk_flags:
        return EpisodeBoundaryReason.SAFETY_RISK_FLAGGED
    if TraceRiskFlag.SAME_TOPIC_NOISE in risk_flags:
        return EpisodeBoundaryReason.NOISE_DETECTED
    if TraceRiskFlag.SPECIALIST_NEEDED in risk_flags:
        return EpisodeBoundaryReason.SPECIALIST_NEEDED
    if TraceRiskFlag.WEAK_EVIDENCE in risk_flags or TraceRiskFlag.CONFLICTING_EVIDENCE in risk_flags:
        return EpisodeBoundaryReason.UNCERTAINTY_FLAGGED
    return EpisodeBoundaryReason.ANSWER_COMPLETED
