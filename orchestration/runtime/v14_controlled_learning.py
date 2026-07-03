from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_canonical_store import CanonicalStoreDecision, CanonicalStoreDecisionOutcome
from orchestration.runtime.v14_consolidation import ConsolidationCandidate, ConsolidationDecision
from orchestration.runtime.v14_feedback import FeedbackCaptureRecord, FeedbackPolarity
from orchestration.runtime.v14_pruning_projection import (
    PruningProjectionReviewFinding,
    PruningProjectionReviewResult,
    TemporaryPruningProjection,
)
from orchestration.runtime.v14_replay import ReplayReviewFinding, ReplayReviewResult


RUNTIME_V14H_INVARIANT_FLAGS: dict[str, bool] = {
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "autonomous_learning_enabled": False,
    "background_learning_enabled": False,
    "training_dataset_export_enabled": False,
    "canonical_write_enabled": False,
    "active_store_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "pruning_enabled": False,
    "canonical_pruning_enabled": False,
    "projection_application_enabled": False,
    "provider_calls_enabled": False,
    "scheduler_enabled": False,
    "active_replay_enabled": False,
    "live_routing_enabled": False,
    "execution_enabled": False,
    "activation_integration_enabled": False,
    "attention_integration_enabled": False,
    "runtime_defaults_changed": False,
}


class LearningEligibilitySignalType(str, Enum):
    REPEATED_POSITIVE_FEEDBACK = "repeated_positive_feedback"
    REPEATED_NEGATIVE_FEEDBACK = "repeated_negative_feedback"
    CORRECTION_CONFIRMED = "correction_confirmed"
    CONTRADICTION_DETECTED = "contradiction_detected"
    REPLAY_SUPPORTED = "replay_supported"
    REPLAY_CONFLICTED = "replay_conflicted"
    CONSOLIDATION_CANDIDATE_SUPPORTED = "consolidation_candidate_supported"
    CANONICAL_STORE_ELIGIBLE = "canonical_store_eligible"
    CANONICAL_STORE_BLOCKED = "canonical_store_blocked"
    PRUNING_PROJECTION_SUPPORTED = "pruning_projection_supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PROVENANCE_GAP = "provenance_gap"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    SAFETY_BLOCKED = "safety_blocked"


class LearningSignalPolarity(str, Enum):
    SUPPORTS_LEARNING = "supports_learning"
    BLOCKS_LEARNING = "blocks_learning"
    REQUIRES_REVIEW = "requires_review"


class LearningSafetyStatus(str, Enum):
    SAFE_FOR_FUTURE_REVIEW = "safe_for_future_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT_LEARNING = "reject_learning"


class ControlledLearningDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    CANDIDATE_ONLY = "candidate_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_OFFLINE_REVIEW = "eligible_for_future_offline_review"


@dataclass(frozen=True)
class LearningEligibilitySignal:
    signal_id: str
    source_reference_id: str
    signal_type: LearningEligibilitySignalType
    polarity: LearningSignalPolarity
    weight: float = 0.0
    rationale: str = ""
    evidence_refs: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_weight(self) -> float:
        return max(0.0, min(1.0, float(self.weight)))

    def as_dict(self) -> dict[str, object]:
        return {
            "signal_id": self.signal_id,
            "source_reference_id": self.source_reference_id,
            "signal_type": self.signal_type.value,
            "polarity": self.polarity.value,
            "weight": self.normalized_weight(),
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class LearningEvidencePacket:
    packet_id: str
    source_reference_ids: tuple[str, ...]
    signals: tuple[LearningEligibilitySignal, ...]
    evidence_summary: str = ""
    provenance_summary: str = ""
    conflict_summary: str = ""
    missing_evidence_notes: tuple[str, ...] = ()
    human_review_notes: tuple[str, ...] = ()
    training_dataset_export_enabled: bool = False
    learning_active: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "packet_id": self.packet_id,
            "source_reference_ids": list(self.source_reference_ids),
            "signals": [signal.as_dict() for signal in self.signals],
            "evidence_summary": self.evidence_summary,
            "provenance_summary": self.provenance_summary,
            "conflict_summary": self.conflict_summary,
            "missing_evidence_notes": list(self.missing_evidence_notes),
            "human_review_notes": list(self.human_review_notes),
            "training_dataset_export_enabled": self.training_dataset_export_enabled,
            "learning_active": self.learning_active,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class LearningCandidate:
    candidate_id: str
    evidence_packet_id: str
    proposed_learning_scope: str
    proposed_change_summary: str
    source_artifact_references: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    confidence_state: float = 0.0
    rollback_requirement: str = "rollback_plan_required_before_activation"
    human_review_required: bool = False
    active: bool = False
    training_ready: bool = False
    applied: bool = False
    canonical_mutation: bool = False
    runtime_recall_mutation: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence_state)))

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "evidence_packet_id": self.evidence_packet_id,
            "proposed_learning_scope": self.proposed_learning_scope,
            "proposed_change_summary": self.proposed_change_summary,
            "source_artifact_references": list(self.source_artifact_references),
            "lane_scope": list(self.lane_scope),
            "confidence_state": self.normalized_confidence(),
            "rollback_requirement": self.rollback_requirement,
            "human_review_required": self.human_review_required,
            "active": self.active,
            "training_ready": self.training_ready,
            "applied": self.applied,
            "canonical_mutation": self.canonical_mutation,
            "runtime_recall_mutation": self.runtime_recall_mutation,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class LearningSafetyReview:
    review_id: str
    candidate_id: str
    safety_status: LearningSafetyStatus
    rationale: str
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14H_INVARIANT_FLAGS))
    required_before_training: tuple[str, ...] = ()
    training_approved: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "candidate_id": self.candidate_id,
            "safety_status": self.safety_status.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "required_before_training": list(self.required_before_training),
            "training_approved": self.training_approved,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ControlledLearningDecision:
    decision_id: str
    candidate_id: str
    outcome: ControlledLearningDecisionOutcome
    rationale: str
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14H_INVARIANT_FLAGS))
    training_enabled: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "training_enabled": self.training_enabled,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ControlledLearningPlan:
    plan_id: str
    candidate_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    training_enabled: bool = False
    fine_tuning_enabled: bool = False
    weight_update_enabled: bool = False
    autonomous_learning_enabled: bool = False
    background_learning_enabled: bool = False
    training_dataset_export_enabled: bool = False
    canonical_write_enabled: bool = False
    active_store_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    pruning_enabled: bool = False
    projection_application_enabled: bool = False
    provider_calls_enabled: bool = False
    scheduler_enabled: bool = False
    runtime_defaults_changed: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14H_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "candidate_ids": list(self.candidate_ids),
            "decision_ids": list(self.decision_ids),
            "training_enabled": self.training_enabled,
            "fine_tuning_enabled": self.fine_tuning_enabled,
            "weight_update_enabled": self.weight_update_enabled,
            "autonomous_learning_enabled": self.autonomous_learning_enabled,
            "background_learning_enabled": self.background_learning_enabled,
            "training_dataset_export_enabled": self.training_dataset_export_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "active_store_enabled": self.active_store_enabled,
            "runtime_recall_mutation_enabled": self.runtime_recall_mutation_enabled,
            "pruning_enabled": self.pruning_enabled,
            "projection_application_enabled": self.projection_application_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class LearningRollbackPlan:
    rollback_id: str
    candidate_id: str
    rollback_reason: str
    required_evidence_or_approval: tuple[str, ...] = ()
    reversible: bool = True
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "rollback_id": self.rollback_id,
            "candidate_id": self.candidate_id,
            "rollback_reason": self.rollback_reason,
            "required_evidence_or_approval": list(self.required_evidence_or_approval),
            "reversible": self.reversible,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_learning_signal(
    *,
    source_reference_id: str,
    signal_type: LearningEligibilitySignalType,
    polarity: LearningSignalPolarity,
    weight: float = 0.0,
    rationale: str = "",
    evidence_refs: tuple[str, ...] = (),
) -> LearningEligibilitySignal:
    refs = tuple(sorted(evidence_refs))
    return LearningEligibilitySignal(
        signal_id=_stable_id("learning-signal", (source_reference_id, signal_type.value, polarity.value, *refs, rationale)),
        source_reference_id=source_reference_id,
        signal_type=signal_type,
        polarity=polarity,
        weight=weight,
        rationale=rationale,
        evidence_refs=refs,
        notes="eligibility signal only; source artifact is not mutated",
    )


def create_learning_signal_from_feedback(record: FeedbackCaptureRecord) -> LearningEligibilitySignal:
    if record.human_review_required:
        signal_type = LearningEligibilitySignalType.HUMAN_REVIEW_REQUIRED
        polarity = LearningSignalPolarity.REQUIRES_REVIEW
    elif record.polarity == FeedbackPolarity.CONFIRMS:
        signal_type = LearningEligibilitySignalType.REPEATED_POSITIVE_FEEDBACK
        polarity = LearningSignalPolarity.SUPPORTS_LEARNING
    elif record.polarity == FeedbackPolarity.CORRECTS:
        signal_type = LearningEligibilitySignalType.CORRECTION_CONFIRMED
        polarity = LearningSignalPolarity.SUPPORTS_LEARNING
    elif record.polarity in {FeedbackPolarity.REJECTS, FeedbackPolarity.FLAGS_NOISE}:
        signal_type = LearningEligibilitySignalType.REPEATED_NEGATIVE_FEEDBACK
        polarity = LearningSignalPolarity.BLOCKS_LEARNING
    elif record.polarity == FeedbackPolarity.ASKS_FOR_MORE_EVIDENCE:
        signal_type = LearningEligibilitySignalType.INSUFFICIENT_EVIDENCE
        polarity = LearningSignalPolarity.BLOCKS_LEARNING
    else:
        signal_type = LearningEligibilitySignalType.PROVENANCE_GAP
        polarity = LearningSignalPolarity.REQUIRES_REVIEW
    return create_learning_signal(
        source_reference_id=record.feedback_id,
        signal_type=signal_type,
        polarity=polarity,
        weight=_feedback_weight(record),
        rationale=f"{record.polarity.value}:{record.target.value}",
        evidence_refs=tuple(ref for ref in (record.trace_id, record.episode_id, *record.affected_concepts) if ref),
    )


def create_learning_signals_from_replay_review(review: ReplayReviewResult) -> tuple[LearningEligibilitySignal, ...]:
    signals: list[LearningEligibilitySignal] = []
    for finding in review.findings:
        signal_type, polarity = _signal_from_replay_finding(finding)
        signals.append(
            create_learning_signal(
                source_reference_id=review.review_id,
                signal_type=signal_type,
                polarity=polarity,
                weight=0.7 if polarity == LearningSignalPolarity.SUPPORTS_LEARNING else 0.55,
                rationale=f"replay_finding={finding.value}",
                evidence_refs=(review.batch_id,),
            )
        )
    return tuple(signals)


def create_learning_signal_from_consolidation(
    candidate: ConsolidationCandidate,
    decision: ConsolidationDecision,
) -> LearningEligibilitySignal:
    return create_learning_signal(
        source_reference_id=candidate.candidate_id,
        signal_type=LearningEligibilitySignalType.CONSOLIDATION_CANDIDATE_SUPPORTED,
        polarity=LearningSignalPolarity.SUPPORTS_LEARNING,
        weight=candidate.normalized_confidence(),
        rationale=f"consolidation_decision={decision.outcome.value}",
        evidence_refs=tuple(ref for ref in (candidate.source_batch_id, candidate.source_review_id, decision.decision_id) if ref),
    )


def create_learning_signal_from_canonical_decision(decision: CanonicalStoreDecision) -> LearningEligibilitySignal:
    if decision.outcome == CanonicalStoreDecisionOutcome.ELIGIBLE_FOR_FUTURE_WRITE:
        signal_type = LearningEligibilitySignalType.CANONICAL_STORE_ELIGIBLE
        polarity = LearningSignalPolarity.SUPPORTS_LEARNING
    elif decision.outcome == CanonicalStoreDecisionOutcome.REQUIRES_HUMAN_REVIEW:
        signal_type = LearningEligibilitySignalType.HUMAN_REVIEW_REQUIRED
        polarity = LearningSignalPolarity.REQUIRES_REVIEW
    elif decision.outcome == CanonicalStoreDecisionOutcome.BLOCKED_BY_INVARIANT:
        signal_type = LearningEligibilitySignalType.CANONICAL_STORE_BLOCKED
        polarity = LearningSignalPolarity.BLOCKS_LEARNING
    else:
        signal_type = LearningEligibilitySignalType.INSUFFICIENT_EVIDENCE
        polarity = LearningSignalPolarity.BLOCKS_LEARNING
    return create_learning_signal(
        source_reference_id=decision.decision_id,
        signal_type=signal_type,
        polarity=polarity,
        weight=0.65,
        rationale=f"canonical_store_decision={decision.outcome.value}",
        evidence_refs=(decision.draft_id,),
    )


def create_learning_signal_from_projection_review(review: PruningProjectionReviewResult) -> LearningEligibilitySignal:
    if review.human_review_required:
        signal_type = LearningEligibilitySignalType.HUMAN_REVIEW_REQUIRED
        polarity = LearningSignalPolarity.REQUIRES_REVIEW
    elif PruningProjectionReviewFinding.CONFLICT_REQUIRES_REPLAY in review.findings:
        signal_type = LearningEligibilitySignalType.REPLAY_CONFLICTED
        polarity = LearningSignalPolarity.BLOCKS_LEARNING
    elif review.projection_recommended:
        signal_type = LearningEligibilitySignalType.PRUNING_PROJECTION_SUPPORTED
        polarity = LearningSignalPolarity.REQUIRES_REVIEW
    else:
        signal_type = LearningEligibilitySignalType.INSUFFICIENT_EVIDENCE
        polarity = LearningSignalPolarity.BLOCKS_LEARNING
    return create_learning_signal(
        source_reference_id=review.review_id,
        signal_type=signal_type,
        polarity=polarity,
        weight=0.55,
        rationale="temporary_pruning_projection_review",
        evidence_refs=(review.request_id,),
    )


def create_learning_evidence_packet(
    *,
    signals: tuple[LearningEligibilitySignal, ...] | list[LearningEligibilitySignal],
    source_reference_ids: tuple[str, ...] = (),
    evidence_summary: str = "",
    provenance_summary: str = "",
    conflict_summary: str = "",
    missing_evidence_notes: tuple[str, ...] = (),
    human_review_notes: tuple[str, ...] = (),
) -> LearningEvidencePacket:
    ordered_signals = tuple(sorted(signals, key=lambda signal: signal.signal_id))
    refs = tuple(sorted({*source_reference_ids, *[signal.source_reference_id for signal in ordered_signals]}))
    return LearningEvidencePacket(
        packet_id=_stable_id("learning-evidence-packet", (*refs, *[signal.signal_id for signal in ordered_signals])),
        source_reference_ids=refs,
        signals=ordered_signals,
        evidence_summary=evidence_summary or _summarize_evidence(ordered_signals),
        provenance_summary=provenance_summary or "packet preserves source references only",
        conflict_summary=conflict_summary or _summarize_conflicts(ordered_signals),
        missing_evidence_notes=tuple(sorted(missing_evidence_notes)),
        human_review_notes=tuple(sorted(human_review_notes)),
        notes="evidence packet is not a training dataset and does not activate learning",
    )


def create_learning_candidate(
    packet: LearningEvidencePacket,
    *,
    proposed_learning_scope: str,
    proposed_change_summary: str,
    lane_scope: tuple[str, ...] = (),
    rollback_requirement: str = "rollback_plan_required_before_activation",
) -> LearningCandidate:
    confidence = _candidate_confidence(packet)
    human_review = any(signal.polarity == LearningSignalPolarity.REQUIRES_REVIEW for signal in packet.signals)
    return LearningCandidate(
        candidate_id=_stable_id(
            "learning-candidate",
            (packet.packet_id, proposed_learning_scope, proposed_change_summary, *lane_scope),
        ),
        evidence_packet_id=packet.packet_id,
        proposed_learning_scope=proposed_learning_scope,
        proposed_change_summary=proposed_change_summary,
        source_artifact_references=packet.source_reference_ids,
        lane_scope=tuple(sorted(lane_scope)),
        confidence_state=confidence,
        rollback_requirement=rollback_requirement,
        human_review_required=human_review,
        notes="candidate only; no training, canonical mutation, or recall mutation is active",
    )


def review_learning_candidate(candidate: LearningCandidate, packet: LearningEvidencePacket) -> LearningSafetyReview:
    status, rationale, requirements = _classify_safety(candidate, packet)
    return LearningSafetyReview(
        review_id=_stable_id("learning-safety-review", (candidate.candidate_id, packet.packet_id, status.value)),
        candidate_id=candidate.candidate_id,
        safety_status=status,
        rationale=rationale,
        required_before_training=requirements,
        notes="safety review cannot approve active training in V1.4H",
    )


def decide_controlled_learning(
    candidate: LearningCandidate,
    review: LearningSafetyReview,
    *,
    reject: bool = False,
    defer: bool = False,
    require_human_review: bool = False,
    invariant_block: bool = False,
    eligible_for_future_offline_review: bool = False,
) -> ControlledLearningDecision:
    if invariant_block or review.safety_status == LearningSafetyStatus.BLOCKED_BY_INVARIANT:
        outcome = ControlledLearningDecisionOutcome.BLOCKED_BY_INVARIANT
        rationale = "A V1.4H invariant blocks learning."
    elif require_human_review or review.safety_status == LearningSafetyStatus.REQUIRES_HUMAN_REVIEW:
        outcome = ControlledLearningDecisionOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Human review is required before future offline learning review."
    elif reject or review.safety_status == LearningSafetyStatus.REJECT_LEARNING:
        outcome = ControlledLearningDecisionOutcome.REJECT
        rationale = "Learning candidate rejected; no training is triggered."
    elif defer or review.safety_status in {
        LearningSafetyStatus.INSUFFICIENT_EVIDENCE,
        LearningSafetyStatus.CONFLICTING_EVIDENCE,
    }:
        outcome = ControlledLearningDecisionOutcome.DEFER
        rationale = "Learning candidate needs more evidence, replay, or conflict review."
    elif eligible_for_future_offline_review:
        outcome = ControlledLearningDecisionOutcome.ELIGIBLE_FOR_FUTURE_OFFLINE_REVIEW
        rationale = "Candidate may proceed to future offline hypothesis review only."
    else:
        outcome = ControlledLearningDecisionOutcome.CANDIDATE_ONLY
        rationale = "Candidate remains inert controlled-learning design material."
    return ControlledLearningDecision(
        decision_id=_stable_id("controlled-learning-decision", (candidate.candidate_id, review.review_id, outcome.value)),
        candidate_id=candidate.candidate_id,
        outcome=outcome,
        rationale=rationale,
        notes="decision is review-only; training_enabled and applied remain false",
    )


def create_controlled_learning_plan(
    *,
    candidates: tuple[LearningCandidate, ...] | list[LearningCandidate] = (),
    decisions: tuple[ControlledLearningDecision, ...] | list[ControlledLearningDecision] = (),
    notes: str = "",
) -> ControlledLearningPlan:
    candidate_ids = tuple(sorted(candidate.candidate_id for candidate in candidates))
    decision_ids = tuple(sorted(decision.decision_id for decision in decisions))
    return ControlledLearningPlan(
        plan_id=_stable_id("controlled-learning-plan", (*candidate_ids, *decision_ids)),
        candidate_ids=candidate_ids,
        decision_ids=decision_ids,
        notes=notes or "controlled learning plan is design-only; it cannot train, schedule, or export data",
    )


def create_learning_rollback_plan(
    candidate: LearningCandidate,
    *,
    rollback_reason: str,
    required_evidence_or_approval: tuple[str, ...] = (),
    reversible: bool = True,
) -> LearningRollbackPlan:
    approvals = tuple(sorted(required_evidence_or_approval))
    return LearningRollbackPlan(
        rollback_id=_stable_id("learning-rollback-plan", (candidate.candidate_id, rollback_reason, *approvals)),
        candidate_id=candidate.candidate_id,
        rollback_reason=rollback_reason,
        required_evidence_or_approval=approvals,
        reversible=reversible,
        notes="rollback plan is inactive because controlled learning is inactive",
    )


def validate_signal_non_mutating(signal: LearningEligibilitySignal) -> bool:
    return bool(signal.signal_id) and bool(signal.source_reference_id)


def validate_evidence_packet_not_training_dataset(packet: LearningEvidencePacket) -> bool:
    return packet.training_dataset_export_enabled is False and packet.learning_active is False


def validate_learning_candidate_inactive(candidate: LearningCandidate) -> bool:
    return (
        candidate.active is False
        and candidate.training_ready is False
        and candidate.applied is False
        and candidate.canonical_mutation is False
        and candidate.runtime_recall_mutation is False
    )


def validate_safety_review_non_training(review: LearningSafetyReview) -> bool:
    return (
        review.training_approved is False
        and review.applied is False
        and all(value is False for value in review.invariant_flags.values())
    )


def validate_learning_decision_review_only(decision: ControlledLearningDecision) -> bool:
    return (
        decision.training_enabled is False
        and decision.applied is False
        and all(value is False for value in decision.invariant_flags.values())
    )


def validate_controlled_learning_plan_inert(plan: ControlledLearningPlan) -> bool:
    return (
        plan.training_enabled is False
        and plan.fine_tuning_enabled is False
        and plan.weight_update_enabled is False
        and plan.autonomous_learning_enabled is False
        and plan.background_learning_enabled is False
        and plan.training_dataset_export_enabled is False
        and plan.canonical_write_enabled is False
        and plan.active_store_enabled is False
        and plan.runtime_recall_mutation_enabled is False
        and plan.pruning_enabled is False
        and plan.projection_application_enabled is False
        and plan.provider_calls_enabled is False
        and plan.scheduler_enabled is False
        and plan.runtime_defaults_changed is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def validate_learning_rollback_not_applied(rollback: LearningRollbackPlan) -> bool:
    return rollback.applied is False


def _signal_from_replay_finding(
    finding: ReplayReviewFinding,
) -> tuple[LearningEligibilitySignalType, LearningSignalPolarity]:
    if finding in {ReplayReviewFinding.USEFUL_SIGNAL, ReplayReviewFinding.PRUNING_REVIEW_SIGNAL}:
        return LearningEligibilitySignalType.REPLAY_SUPPORTED, LearningSignalPolarity.SUPPORTS_LEARNING
    if finding == ReplayReviewFinding.CONFLICTING_EVIDENCE:
        return LearningEligibilitySignalType.REPLAY_CONFLICTED, LearningSignalPolarity.BLOCKS_LEARNING
    if finding == ReplayReviewFinding.SAFETY_BLOCKED:
        return LearningEligibilitySignalType.SAFETY_BLOCKED, LearningSignalPolarity.BLOCKS_LEARNING
    if finding == ReplayReviewFinding.HUMAN_REVIEW_NEEDED:
        return LearningEligibilitySignalType.HUMAN_REVIEW_REQUIRED, LearningSignalPolarity.REQUIRES_REVIEW
    return LearningEligibilitySignalType.INSUFFICIENT_EVIDENCE, LearningSignalPolarity.BLOCKS_LEARNING


def _classify_safety(
    candidate: LearningCandidate,
    packet: LearningEvidencePacket,
) -> tuple[LearningSafetyStatus, str, tuple[str, ...]]:
    if any(value is True for value in RUNTIME_V14H_INVARIANT_FLAGS.values()):
        return (
            LearningSafetyStatus.BLOCKED_BY_INVARIANT,
            "A forbidden V1.4H capability flag is enabled.",
            ("restore invariant flags",),
        )
    if candidate.human_review_required:
        return (
            LearningSafetyStatus.REQUIRES_HUMAN_REVIEW,
            "Candidate includes signals requiring human review.",
            ("human approval", "replay/consolidation review"),
        )
    signal_types = {signal.signal_type for signal in packet.signals}
    if LearningEligibilitySignalType.SAFETY_BLOCKED in signal_types:
        return (
            LearningSafetyStatus.BLOCKED_BY_INVARIANT,
            "Safety-blocked evidence cannot enter controlled learning.",
            ("safety review",),
        )
    if signal_types & {LearningEligibilitySignalType.CONTRADICTION_DETECTED, LearningEligibilitySignalType.REPLAY_CONFLICTED}:
        return (
            LearningSafetyStatus.CONFLICTING_EVIDENCE,
            "Conflicting evidence must be resolved before future learning review.",
            ("contradiction review", "replay review"),
        )
    support_count = sum(signal.polarity == LearningSignalPolarity.SUPPORTS_LEARNING for signal in packet.signals)
    block_count = sum(signal.polarity == LearningSignalPolarity.BLOCKS_LEARNING for signal in packet.signals)
    if support_count == 0 or block_count > support_count:
        return (
            LearningSafetyStatus.INSUFFICIENT_EVIDENCE,
            "Not enough positive evidence exists for future controlled-learning review.",
            ("additional evidence",),
        )
    return (
        LearningSafetyStatus.SAFE_FOR_FUTURE_REVIEW,
        "Candidate is safe for future offline review only; training remains disabled.",
        ("human approval", "rollback plan", "offline review packet"),
    )


def _candidate_confidence(packet: LearningEvidencePacket) -> float:
    support = sum(signal.normalized_weight() for signal in packet.signals if signal.polarity == LearningSignalPolarity.SUPPORTS_LEARNING)
    blockers = sum(signal.normalized_weight() for signal in packet.signals if signal.polarity == LearningSignalPolarity.BLOCKS_LEARNING)
    reviewers = sum(signal.normalized_weight() for signal in packet.signals if signal.polarity == LearningSignalPolarity.REQUIRES_REVIEW)
    return max(0.0, min(1.0, 0.35 + (0.2 * support) - (0.15 * blockers) - (0.1 * reviewers)))


def _summarize_evidence(signals: tuple[LearningEligibilitySignal, ...]) -> str:
    support_count = sum(signal.polarity == LearningSignalPolarity.SUPPORTS_LEARNING for signal in signals)
    block_count = sum(signal.polarity == LearningSignalPolarity.BLOCKS_LEARNING for signal in signals)
    review_count = sum(signal.polarity == LearningSignalPolarity.REQUIRES_REVIEW for signal in signals)
    return f"supports={support_count}; blocks={block_count}; requires_review={review_count}"


def _summarize_conflicts(signals: tuple[LearningEligibilitySignal, ...]) -> str:
    conflicts = [signal.signal_type.value for signal in signals if signal.signal_type in {
        LearningEligibilitySignalType.CONTRADICTION_DETECTED,
        LearningEligibilitySignalType.REPLAY_CONFLICTED,
        LearningEligibilitySignalType.SAFETY_BLOCKED,
    }]
    return "none" if not conflicts else ";".join(sorted(conflicts))


def _feedback_weight(record: FeedbackCaptureRecord) -> float:
    return {
        "low": 0.25,
        "medium": 0.55,
        "high": 0.75,
        "critical": 0.95,
        "unknown": 0.1,
    }[record.severity.value]


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"
