from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from orchestration.runtime.v14_feedback import (
    FeedbackCaptureRecord,
    FeedbackDisposition,
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackTarget,
)
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_pruning import (
    CorrectiveAction,
    PruningFailureType,
    is_reversible_action,
    propose_pruning_record,
    should_require_human_review,
)


class PruningReviewDecision(str, Enum):
    NO_PRUNING_REVIEW = "no_pruning_review"
    PROPOSE_DAMPEN_REVIEW = "propose_dampen_review"
    PROPOSE_LANE_BLOCK_REVIEW = "propose_lane_block_review"
    PROPOSE_REQUIRE_CONTEXT_REVIEW = "propose_require_context_review"
    PROPOSE_QUARANTINE_REVIEW = "propose_quarantine_review"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BENCHMARK_ONLY_NO_PRUNING = "benchmark_only_no_pruning"


@dataclass(frozen=True)
class PruningReviewProposal:
    proposal_id: str
    feedback_id: str
    trace_id: str
    episode_id: str
    concept_id: str
    affected_lane: RuntimeLane
    failure_type: PruningFailureType
    corrective_action: CorrectiveAction
    decision: PruningReviewDecision
    confidence: float = 0.0
    reversible: bool = True
    human_review_required: bool = False
    source_feedback_text: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "feedback_id": self.feedback_id,
            "trace_id": self.trace_id,
            "episode_id": self.episode_id,
            "concept_id": self.concept_id,
            "affected_lane": self.affected_lane.value,
            "failure_type": self.failure_type.value,
            "corrective_action": self.corrective_action.value,
            "decision": self.decision.value,
            "confidence": self.normalized_confidence(),
            "reversible": self.reversible,
            "human_review_required": self.human_review_required,
            "source_feedback_text": self.source_feedback_text,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def feedback_to_pruning_review_proposals(record: FeedbackCaptureRecord) -> list[PruningReviewProposal]:
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return []
    if not should_create_pruning_review(record):
        return []

    failure_type = classify_pruning_failure_type(record)
    action = choose_corrective_action_for_feedback(record)
    decision = _decision_for_action(record, action)
    lane = _first_lane_or_default(record)
    confidence = _confidence_for_feedback(record)
    human_review = (
        record.human_review_required
        or should_require_human_review(failure_type, action)
        or decision in {PruningReviewDecision.REQUIRES_HUMAN_REVIEW, PruningReviewDecision.PROPOSE_QUARANTINE_REVIEW}
    )

    proposals: list[PruningReviewProposal] = []
    for concept_id in record.affected_concepts:
        proposals.append(
            PruningReviewProposal(
                proposal_id=f"pruning-review-{uuid4().hex}",
                feedback_id=record.feedback_id,
                trace_id=record.trace_id,
                episode_id=record.episode_id,
                concept_id=concept_id,
                affected_lane=lane,
                failure_type=failure_type,
                corrective_action=action,
                decision=decision,
                confidence=confidence,
                reversible=is_reversible_action(action),
                human_review_required=human_review,
                source_feedback_text=record.feedback_text,
                notes="review proposal only; no pruning action executed",
            )
        )
    return proposals


def classify_pruning_failure_type(record: FeedbackCaptureRecord) -> PruningFailureType:
    text = f"{record.feedback_text} {record.notes}".lower()
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return PruningFailureType.BENCHMARK_ARTIFACT
    if any(token in text for token in ("false", "corrupt", "invalid concept")):
        return PruningFailureType.FALSE_OR_CORRUPT_CONCEPT
    if record.polarity == FeedbackPolarity.FLAGS_NOISE:
        return PruningFailureType.SAME_TOPIC_NOISE
    if record.target == FeedbackTarget.PLANNING_LANE:
        return PruningFailureType.PLANNING_DRIFT
    if record.target == FeedbackTarget.REASONING_LANE:
        return PruningFailureType.REASONING_DRIFT
    if record.target == FeedbackTarget.RESPONSE_LANE:
        return PruningFailureType.RESPONSE_DRIFT
    if "generic" in text or "anchor" in text:
        return PruningFailureType.GENERIC_ANCHOR_DOMINANCE
    return PruningFailureType.WRONG_EVIDENCE_ROLE


def choose_corrective_action_for_feedback(record: FeedbackCaptureRecord) -> CorrectiveAction:
    failure_type = classify_pruning_failure_type(record)
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return CorrectiveAction.NO_ACTION
    if failure_type == PruningFailureType.FALSE_OR_CORRUPT_CONCEPT:
        return CorrectiveAction.QUARANTINE
    if record.severity == FeedbackSeverity.CRITICAL:
        return CorrectiveAction.REVIEW_REQUIRED
    if record.polarity == FeedbackPolarity.FLAGS_NOISE:
        return CorrectiveAction.REQUIRE_CONTEXT if record.severity in {FeedbackSeverity.LOW, FeedbackSeverity.MEDIUM} else CorrectiveAction.DAMPEN
    if record.severity == FeedbackSeverity.HIGH:
        return CorrectiveAction.DAMPEN
    return CorrectiveAction.NO_ACTION


def should_create_pruning_review(record: FeedbackCaptureRecord) -> bool:
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return False
    if not record.affected_concepts:
        return False
    if record.polarity == FeedbackPolarity.FLAGS_NOISE:
        return True
    if record.severity in {FeedbackSeverity.HIGH, FeedbackSeverity.CRITICAL} and record.polarity in {
        FeedbackPolarity.CORRECTS,
        FeedbackPolarity.REJECTS,
        FeedbackPolarity.FLAGS_SAFETY_RISK,
    }:
        return True
    text = f"{record.feedback_text} {record.notes}".lower()
    return any(token in text for token in ("false", "corrupt", "invalid concept"))


def validate_pruning_proposal_non_mutating(proposal: PruningReviewProposal) -> bool:
    return proposal.decision.value.endswith("_review") or proposal.decision in {
        PruningReviewDecision.NO_PRUNING_REVIEW,
        PruningReviewDecision.REQUIRES_HUMAN_REVIEW,
        PruningReviewDecision.BENCHMARK_ONLY_NO_PRUNING,
    }


def _decision_for_action(record: FeedbackCaptureRecord, action: CorrectiveAction) -> PruningReviewDecision:
    if record.proposed_disposition == FeedbackDisposition.BENCHMARK_ONLY_DO_NOT_TRAIN:
        return PruningReviewDecision.BENCHMARK_ONLY_NO_PRUNING
    if action == CorrectiveAction.DAMPEN:
        return PruningReviewDecision.PROPOSE_DAMPEN_REVIEW
    if action == CorrectiveAction.LANE_BLOCK:
        return PruningReviewDecision.PROPOSE_LANE_BLOCK_REVIEW
    if action == CorrectiveAction.REQUIRE_CONTEXT:
        return PruningReviewDecision.PROPOSE_REQUIRE_CONTEXT_REVIEW
    if action == CorrectiveAction.QUARANTINE:
        return PruningReviewDecision.PROPOSE_QUARANTINE_REVIEW
    if action == CorrectiveAction.REVIEW_REQUIRED:
        return PruningReviewDecision.REQUIRES_HUMAN_REVIEW
    return PruningReviewDecision.NO_PRUNING_REVIEW


def _first_lane_or_default(record: FeedbackCaptureRecord) -> RuntimeLane:
    if not record.affected_lanes:
        return RuntimeLane.REASONING
    lane = record.affected_lanes[0]
    if isinstance(lane, RuntimeLane):
        return lane
    try:
        return RuntimeLane(str(lane))
    except ValueError:
        return RuntimeLane.REASONING


def _confidence_for_feedback(record: FeedbackCaptureRecord) -> float:
    return {
        FeedbackSeverity.LOW: 0.3,
        FeedbackSeverity.MEDIUM: 0.55,
        FeedbackSeverity.HIGH: 0.75,
        FeedbackSeverity.CRITICAL: 0.95,
        FeedbackSeverity.UNKNOWN: 0.2,
    }[record.severity]


def _unused_pruning_record_example(record: FeedbackCaptureRecord) -> object:
    """Keep import compatibility visible without creating live pruning actions."""

    if not record.affected_concepts:
        return None
    return propose_pruning_record(
        concept_id=record.affected_concepts[0],
        failure_context_hash=record.trace_id,
        failure_type=classify_pruning_failure_type(record),
        affected_lane=_first_lane_or_default(record),
        corrective_action=choose_corrective_action_for_feedback(record),
        evidence_snapshot=record.evidence_snapshot,
        confidence=_confidence_for_feedback(record),
        source_report="runtime_v14d_feedback_capture_scaffold",
    )
