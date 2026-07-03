from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from orchestration.runtime.v14_lanes import RuntimeLane


class TraceAnswerMode(str, Enum):
    DIRECT_ANSWER = "direct_answer"
    BEST_GUESS = "best_guess"
    WEAK_GUESS = "weak_guess"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ROUTED_TO_SPECIALIST = "routed_to_specialist"
    ABSTAINED = "abstained"


class TraceEvidenceUse(str, Enum):
    RETRIEVED = "retrieved"
    ACTIVATED = "activated"
    ATTENDED = "attended"
    CITABLE_USED = "citable_used"
    PLANNING_USED = "planning_used"
    RESPONSE_USED = "response_used"
    IGNORED = "ignored"
    BLOCKED = "blocked"
    ROUTED_EXTERNAL = "routed_external"


class TraceRiskFlag(str, Enum):
    WEAK_EVIDENCE = "weak_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    SAME_TOPIC_NOISE = "same_topic_noise"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    UNSAFE_ACTION = "unsafe_action"
    OUTSIDE_DOMAIN = "outside_domain"
    SPECIALIST_NEEDED = "specialist_needed"
    OVERCONFIDENCE_RISK = "overconfidence_risk"
    NONE = "none"


class FeedbackSignalType(str, Enum):
    USER_CONFIRMED = "user_confirmed"
    USER_CORRECTED = "user_corrected"
    USER_REJECTED = "user_rejected"
    USER_REQUESTED_MORE_EVIDENCE = "user_requested_more_evidence"
    MODEL_SELF_FLAGGED_UNCERTAINTY = "model_self_flagged_uncertainty"
    SPECIALIST_DISAGREED = "specialist_disagreed"
    UNSAFE_OR_ACTIONABLE_RISK = "unsafe_or_actionable_risk"
    UNKNOWN = "unknown"


class ReplayEligibility(str, Enum):
    NOT_ELIGIBLE = "not_eligible"
    ELIGIBLE_FOR_REVIEW = "eligible_for_review"
    ELIGIBLE_FOR_REPLAY = "eligible_for_replay"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BENCHMARK_ONLY_DO_NOT_TRAIN = "benchmark_only_do_not_train"


@dataclass(frozen=True)
class EvidenceUseTrace:
    concept_id: str
    evidence_use: TraceEvidenceUse
    lane: RuntimeLane | str
    reason: str
    confidence: float = 0.0
    blocked_reason: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        lane_value = self.lane.value if isinstance(self.lane, RuntimeLane) else str(self.lane)
        return {
            "concept_id": self.concept_id,
            "evidence_use": self.evidence_use.value,
            "lane": lane_value,
            "reason": self.reason,
            "confidence": self.normalized_confidence(),
            "blocked_reason": self.blocked_reason,
        }


@dataclass(frozen=True)
class AnswerTrace:
    trace_id: str
    question: str
    answer_mode: TraceAnswerMode
    evidence_traces: tuple[EvidenceUseTrace, ...] = ()
    risk_flags: tuple[TraceRiskFlag, ...] = (TraceRiskFlag.NONE,)
    confidence: float = 0.0
    uncertainty_reason: str = ""
    specialist_route_domain: str = ""
    specialist_called: bool = False
    final_answer_summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "question": self.question,
            "answer_mode": self.answer_mode.value,
            "evidence_traces": [trace.as_dict() for trace in self.evidence_traces],
            "risk_flags": [flag.value for flag in self.risk_flags],
            "confidence": self.normalized_confidence(),
            "uncertainty_reason": self.uncertainty_reason,
            "specialist_route_domain": self.specialist_route_domain,
            "specialist_called": self.specialist_called,
            "final_answer_summary": self.final_answer_summary,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class FeedbackEventDraft:
    trace_id: str
    signal_type: FeedbackSignalType
    feedback_text: str = ""
    affected_concepts: tuple[str, ...] = ()
    proposed_replay_eligibility: ReplayEligibility = ReplayEligibility.NOT_ELIGIBLE
    proposed_pruning_review: bool = False
    human_review_required: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "signal_type": self.signal_type.value,
            "feedback_text": self.feedback_text,
            "affected_concepts": list(self.affected_concepts),
            "proposed_replay_eligibility": self.proposed_replay_eligibility.value,
            "proposed_pruning_review": self.proposed_pruning_review,
            "human_review_required": self.human_review_required,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ReplayCandidateMarker:
    trace_id: str
    eligibility: ReplayEligibility
    reason: str
    priority: float = 0.0
    source_feedback_signal: FeedbackSignalType = FeedbackSignalType.UNKNOWN
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def normalized_priority(self) -> float:
        return max(0.0, min(1.0, float(self.priority)))

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "eligibility": self.eligibility.value,
            "reason": self.reason,
            "priority": self.normalized_priority(),
            "source_feedback_signal": self.source_feedback_signal.value,
            "created_at": self.created_at,
        }


def create_answer_trace(
    *,
    question: str,
    answer_mode: TraceAnswerMode,
    confidence: float = 0.0,
    risk_flags: tuple[TraceRiskFlag, ...] | None = None,
    uncertainty_reason: str = "",
    specialist_route_domain: str = "",
    specialist_called: bool = False,
    final_answer_summary: str = "",
    trace_id: str | None = None,
) -> AnswerTrace:
    flags = risk_flags if risk_flags is not None else (TraceRiskFlag.NONE,)
    return AnswerTrace(
        trace_id=trace_id or f"trace-{uuid4().hex}",
        question=question,
        answer_mode=answer_mode,
        risk_flags=flags,
        confidence=confidence,
        uncertainty_reason=uncertainty_reason,
        specialist_route_domain=specialist_route_domain,
        specialist_called=specialist_called,
        final_answer_summary=final_answer_summary,
    )


def add_evidence_trace(
    trace: AnswerTrace,
    *,
    concept_id: str,
    evidence_use: TraceEvidenceUse,
    lane: RuntimeLane | str,
    reason: str,
    confidence: float = 0.0,
    blocked_reason: str = "",
) -> AnswerTrace:
    evidence_trace = EvidenceUseTrace(
        concept_id=concept_id,
        evidence_use=evidence_use,
        lane=lane,
        reason=reason,
        confidence=confidence,
        blocked_reason=blocked_reason,
    )
    return replace(trace, evidence_traces=(*trace.evidence_traces, evidence_trace))


def classify_replay_eligibility(
    *,
    signal_type: FeedbackSignalType = FeedbackSignalType.UNKNOWN,
    risk_flags: tuple[TraceRiskFlag, ...] = (),
    benchmark_only: bool = False,
    human_review_required: bool = False,
) -> ReplayEligibility:
    if benchmark_only:
        return ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN
    if human_review_required or TraceRiskFlag.UNSAFE_ACTION in risk_flags:
        return ReplayEligibility.REQUIRES_HUMAN_REVIEW
    if signal_type in {
        FeedbackSignalType.USER_CORRECTED,
        FeedbackSignalType.USER_REJECTED,
        FeedbackSignalType.USER_REQUESTED_MORE_EVIDENCE,
        FeedbackSignalType.SPECIALIST_DISAGREED,
    }:
        return ReplayEligibility.ELIGIBLE_FOR_REVIEW
    if signal_type in {FeedbackSignalType.USER_CONFIRMED, FeedbackSignalType.MODEL_SELF_FLAGGED_UNCERTAINTY}:
        return ReplayEligibility.ELIGIBLE_FOR_REPLAY
    return ReplayEligibility.NOT_ELIGIBLE


def create_feedback_event_draft(
    *,
    trace_id: str,
    signal_type: FeedbackSignalType,
    feedback_text: str = "",
    affected_concepts: tuple[str, ...] = (),
    risk_flags: tuple[TraceRiskFlag, ...] = (),
    benchmark_only: bool = False,
    human_review_required: bool = False,
) -> FeedbackEventDraft:
    eligibility = classify_replay_eligibility(
        signal_type=signal_type,
        risk_flags=risk_flags,
        benchmark_only=benchmark_only,
        human_review_required=human_review_required,
    )
    return FeedbackEventDraft(
        trace_id=trace_id,
        signal_type=signal_type,
        feedback_text=feedback_text,
        affected_concepts=affected_concepts,
        proposed_replay_eligibility=eligibility,
        proposed_pruning_review=signal_type in {FeedbackSignalType.USER_CORRECTED, FeedbackSignalType.USER_REJECTED},
        human_review_required=eligibility == ReplayEligibility.REQUIRES_HUMAN_REVIEW,
    )


def mark_trace_for_replay(
    trace: AnswerTrace,
    *,
    eligibility: ReplayEligibility,
    reason: str,
    priority: float = 0.0,
    source_feedback_signal: FeedbackSignalType = FeedbackSignalType.UNKNOWN,
) -> ReplayCandidateMarker:
    return ReplayCandidateMarker(
        trace_id=trace.trace_id,
        eligibility=eligibility,
        reason=reason,
        priority=priority,
        source_feedback_signal=source_feedback_signal,
    )


def summarize_trace_for_report(trace: AnswerTrace) -> dict[str, object]:
    evidence_counts: dict[str, int] = {}
    for evidence_trace in trace.evidence_traces:
        key = evidence_trace.evidence_use.value
        evidence_counts[key] = evidence_counts.get(key, 0) + 1
    return {
        "trace_id": trace.trace_id,
        "answer_mode": trace.answer_mode.value,
        "confidence": trace.normalized_confidence(),
        "risk_flags": [flag.value for flag in trace.risk_flags],
        "specialist_called": trace.specialist_called,
        "evidence_trace_count": len(trace.evidence_traces),
        "evidence_use_counts": evidence_counts,
        "non_mutating": validate_trace_is_non_mutating(trace),
    }


def validate_trace_is_non_mutating(trace: AnswerTrace | FeedbackEventDraft | ReplayCandidateMarker) -> bool:
    payload = trace.as_dict()
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
    }
    return not any(key in payload for key in forbidden_keys)
