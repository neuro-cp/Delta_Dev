from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_feedback import FeedbackCaptureRecord, FeedbackPolarity
from orchestration.runtime.v14_feedback_to_pruning import PruningReviewDecision, PruningReviewProposal
from orchestration.runtime.v14_lanes import RuntimeLane


RUNTIME_V14G_INVARIANT_FLAGS: dict[str, bool] = {
    "pruning_enabled": False,
    "canonical_pruning_enabled": False,
    "projection_application_enabled": False,
    "live_memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "canonical_write_enabled": False,
    "active_store_enabled": False,
    "training_enabled": False,
    "provider_calls_enabled": False,
    "scheduler_enabled": False,
    "active_replay_enabled": False,
    "live_routing_enabled": False,
    "execution_enabled": False,
    "runtime_defaults_changed": False,
    "global_concept_deletion_enabled": False,
    "activation_integration_enabled": False,
    "attention_integration_enabled": False,
}


class PruningProjectionSignalType(str, Enum):
    NEGATIVE_FEEDBACK = "negative_feedback"
    CONTRADICTION = "contradiction"
    LOW_CONFIDENCE = "low_confidence"
    STALE_EVIDENCE = "stale_evidence"
    UNSAFE_EVIDENCE_USE = "unsafe_evidence_use"
    PROVENANCE_GAP = "provenance_gap"
    REPLAY_CONFLICT = "replay_conflict"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    CANONICAL_STORE_BLOCKED = "canonical_store_blocked"
    SAME_TOPIC_NOISE = "same_topic_noise"


class PruningProjectionIntent(str, Enum):
    DAMPEN_TEMPORARILY = "dampen_temporarily"
    QUARANTINE_FOR_REVIEW = "quarantine_for_review"
    EXCLUDE_FROM_HYPOTHETICAL_ANSWER = "exclude_from_hypothetical_answer"
    REQUIRE_HUMAN_REVIEW = "require_human_review"
    DEFER_TO_REPLAY_REVIEW = "defer_to_replay_review"
    REJECT_PROJECTION = "reject_projection"


class PruningProjectionDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    PROJECTION_ONLY = "projection_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_PROJECTION = "eligible_for_future_projection"


class PruningProjectionEffect(str, Enum):
    DAMPEN = "dampen"
    QUARANTINE = "quarantine"
    EXCLUDE_IN_LANE = "exclude_in_lane"
    REQUIRE_REVIEW = "require_review"
    DEFER = "defer"


class PruningProjectionReviewFinding(str, Enum):
    USEFUL_TEMPORARY_DAMPENING_SIGNAL = "useful_temporary_dampening_signal"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICT_REQUIRES_REPLAY = "conflict_requires_replay"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT_PROJECTION = "reject_projection"


@dataclass(frozen=True)
class PruningProjectionScope:
    scope_id: str
    lane: RuntimeLane | str
    projection_context_id: str
    source_reference_ids: tuple[str, ...] = ()
    applies_globally: bool = False
    canonical_scope: bool = False
    runtime_recall_scope: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def lane_value(self) -> str:
        return self.lane.value if isinstance(self.lane, RuntimeLane) else str(self.lane)

    def as_dict(self) -> dict[str, object]:
        return {
            "scope_id": self.scope_id,
            "lane": self.lane_value(),
            "projection_context_id": self.projection_context_id,
            "source_reference_ids": list(self.source_reference_ids),
            "applies_globally": self.applies_globally,
            "canonical_scope": self.canonical_scope,
            "runtime_recall_scope": self.runtime_recall_scope,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PruningProjectionSignal:
    signal_id: str
    source_reference_id: str
    signal_type: PruningProjectionSignalType
    severity: float = 0.0
    rationale: str = ""
    evidence_refs: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_severity(self) -> float:
        return max(0.0, min(1.0, float(self.severity)))

    def as_dict(self) -> dict[str, object]:
        return {
            "signal_id": self.signal_id,
            "source_reference_id": self.source_reference_id,
            "signal_type": self.signal_type.value,
            "severity": self.normalized_severity(),
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PruningProjectionRequest:
    request_id: str
    scope: PruningProjectionScope
    signals: tuple[PruningProjectionSignal, ...]
    requested_intent: PruningProjectionIntent
    source_artifacts: tuple[str, ...] = ()
    created_from_refs: tuple[str, ...] = ()
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "scope": self.scope.as_dict(),
            "signals": [signal.as_dict() for signal in self.signals],
            "requested_intent": self.requested_intent.value,
            "source_artifacts": list(self.source_artifacts),
            "created_from_refs": list(self.created_from_refs),
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PruningProjectionDecision:
    decision_id: str
    request_id: str
    outcome: PruningProjectionDecisionOutcome
    rationale: str
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14G_INVARIANT_FLAGS))
    reversible: bool = True
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "reversible": self.reversible,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class TemporaryPruningProjection:
    projection_id: str
    decision_id: str
    scope: PruningProjectionScope
    affected_source_references: tuple[str, ...]
    projection_effect: PruningProjectionEffect
    projection_strength: float = 0.0
    session_boundary: str = ""
    reversible: bool = True
    applied: bool = False
    active: bool = False
    canonical_mutation: bool = False
    runtime_recall_mutation: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_strength(self) -> float:
        return max(0.0, min(1.0, float(self.projection_strength)))

    def as_dict(self) -> dict[str, object]:
        return {
            "projection_id": self.projection_id,
            "decision_id": self.decision_id,
            "scope": self.scope.as_dict(),
            "affected_source_references": list(self.affected_source_references),
            "projection_effect": self.projection_effect.value,
            "projection_strength": self.normalized_strength(),
            "session_boundary": self.session_boundary,
            "reversible": self.reversible,
            "applied": self.applied,
            "active": self.active,
            "canonical_mutation": self.canonical_mutation,
            "runtime_recall_mutation": self.runtime_recall_mutation,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PruningProjectionPlan:
    plan_id: str
    request_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    projection_ids: tuple[str, ...] = ()
    pruning_enabled: bool = False
    canonical_pruning_enabled: bool = False
    live_memory_mutation_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    projection_application_enabled: bool = False
    canonical_write_enabled: bool = False
    active_store_enabled: bool = False
    training_enabled: bool = False
    provider_calls_enabled: bool = False
    scheduler_enabled: bool = False
    runtime_defaults_changed: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14G_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "request_ids": list(self.request_ids),
            "decision_ids": list(self.decision_ids),
            "projection_ids": list(self.projection_ids),
            "pruning_enabled": self.pruning_enabled,
            "canonical_pruning_enabled": self.canonical_pruning_enabled,
            "live_memory_mutation_enabled": self.live_memory_mutation_enabled,
            "runtime_recall_mutation_enabled": self.runtime_recall_mutation_enabled,
            "projection_application_enabled": self.projection_application_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "active_store_enabled": self.active_store_enabled,
            "training_enabled": self.training_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PruningProjectionReviewResult:
    review_id: str
    request_id: str
    findings: tuple[PruningProjectionReviewFinding, ...] = ()
    useful_signal_count: int = 0
    insufficient_evidence_count: int = 0
    conflict_count: int = 0
    human_review_required: bool = False
    projection_recommended: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rationale: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "request_id": self.request_id,
            "findings": [finding.value for finding in self.findings],
            "useful_signal_count": self.useful_signal_count,
            "insufficient_evidence_count": self.insufficient_evidence_count,
            "conflict_count": self.conflict_count,
            "human_review_required": self.human_review_required,
            "projection_recommended": self.projection_recommended,
            "applied": self.applied,
            "created_at": self.created_at,
            "rationale": self.rationale,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PruningProjectionRollbackPlan:
    rollback_id: str
    projection_id: str
    rollback_reason: str
    required_evidence_or_approval: tuple[str, ...] = ()
    reversible: bool = True
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "rollback_id": self.rollback_id,
            "projection_id": self.projection_id,
            "rollback_reason": self.rollback_reason,
            "required_evidence_or_approval": list(self.required_evidence_or_approval),
            "reversible": self.reversible,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_projection_scope(
    *,
    lane: RuntimeLane | str,
    projection_context_id: str,
    source_reference_ids: tuple[str, ...] = (),
    notes: str = "",
) -> PruningProjectionScope:
    lane_value = lane.value if isinstance(lane, RuntimeLane) else str(lane)
    source_refs = tuple(sorted(source_reference_ids))
    return PruningProjectionScope(
        scope_id=_stable_id("projection-scope", (lane_value, projection_context_id, *source_refs)),
        lane=lane,
        projection_context_id=projection_context_id,
        source_reference_ids=source_refs,
        notes=notes or "lane-scoped temporary projection scope; not global concept judgment",
    )


def create_projection_signal(
    *,
    source_reference_id: str,
    signal_type: PruningProjectionSignalType,
    severity: float = 0.0,
    rationale: str = "",
    evidence_refs: tuple[str, ...] = (),
) -> PruningProjectionSignal:
    refs = tuple(sorted(evidence_refs))
    return PruningProjectionSignal(
        signal_id=_stable_id("projection-signal", (source_reference_id, signal_type.value, *refs, rationale)),
        source_reference_id=source_reference_id,
        signal_type=signal_type,
        severity=severity,
        rationale=rationale,
        evidence_refs=refs,
        notes="projection signal only; source record is not mutated",
    )


def create_projection_signal_from_pruning_proposal(proposal: PruningReviewProposal) -> PruningProjectionSignal:
    return create_projection_signal(
        source_reference_id=proposal.proposal_id,
        signal_type=_signal_type_from_pruning_proposal(proposal),
        severity=proposal.normalized_confidence(),
        rationale=f"{proposal.failure_type.value}:{proposal.corrective_action.value}:{proposal.decision.value}",
        evidence_refs=tuple(ref for ref in (proposal.feedback_id, proposal.trace_id, proposal.episode_id, proposal.concept_id) if ref),
    )


def create_projection_signal_from_feedback(record: FeedbackCaptureRecord) -> PruningProjectionSignal:
    return create_projection_signal(
        source_reference_id=record.feedback_id,
        signal_type=_signal_type_from_feedback(record),
        severity=_severity_from_feedback(record),
        rationale=f"{record.polarity.value}:{record.target.value}",
        evidence_refs=tuple(ref for ref in (record.trace_id, record.episode_id, *record.affected_concepts) if ref),
    )


def create_projection_request(
    *,
    scope: PruningProjectionScope,
    signals: tuple[PruningProjectionSignal, ...] | list[PruningProjectionSignal],
    requested_intent: PruningProjectionIntent,
    source_artifacts: tuple[str, ...] = (),
    created_from_refs: tuple[str, ...] = (),
    notes: str = "",
) -> PruningProjectionRequest:
    ordered_signals = tuple(sorted(signals, key=lambda signal: signal.signal_id))
    refs = tuple(sorted(created_from_refs))
    artifacts = tuple(sorted(source_artifacts))
    return PruningProjectionRequest(
        request_id=_stable_id(
            "projection-request",
            (scope.scope_id, requested_intent.value, *[signal.signal_id for signal in ordered_signals], *refs),
        ),
        scope=scope,
        signals=ordered_signals,
        requested_intent=requested_intent,
        source_artifacts=artifacts,
        created_from_refs=refs,
        notes=notes or "request is review-only; temporary projection is not applied",
    )


def review_projection_request(request: PruningProjectionRequest) -> PruningProjectionReviewResult:
    findings = _findings_for_request(request)
    useful = findings.count(PruningProjectionReviewFinding.USEFUL_TEMPORARY_DAMPENING_SIGNAL)
    insufficient = findings.count(PruningProjectionReviewFinding.INSUFFICIENT_EVIDENCE)
    conflicts = findings.count(PruningProjectionReviewFinding.CONFLICT_REQUIRES_REPLAY)
    human_review = PruningProjectionReviewFinding.HUMAN_REVIEW_REQUIRED in findings
    blocked = PruningProjectionReviewFinding.BLOCKED_BY_INVARIANT in findings
    rejected = PruningProjectionReviewFinding.REJECT_PROJECTION in findings
    recommended = useful > 0 and not human_review and not blocked and not rejected
    return PruningProjectionReviewResult(
        review_id=_stable_id("projection-review", (request.request_id, *[finding.value for finding in findings])),
        request_id=request.request_id,
        findings=findings,
        useful_signal_count=useful,
        insufficient_evidence_count=insufficient,
        conflict_count=conflicts,
        human_review_required=human_review,
        projection_recommended=recommended,
        rationale=_review_rationale(findings, recommended),
        notes="review result only; no projection is applied",
    )


def decide_projection_request(
    request: PruningProjectionRequest,
    review: PruningProjectionReviewResult,
    *,
    invariant_block: bool = False,
    reject: bool = False,
    defer: bool = False,
    require_human_review: bool = False,
    eligible_for_future_projection: bool = False,
) -> PruningProjectionDecision:
    if invariant_block:
        outcome = PruningProjectionDecisionOutcome.BLOCKED_BY_INVARIANT
        rationale = "A V1.4G invariant blocks temporary projection."
    elif require_human_review or review.human_review_required:
        outcome = PruningProjectionDecisionOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Human review is required before any future temporary projection."
    elif reject or request.requested_intent == PruningProjectionIntent.REJECT_PROJECTION:
        outcome = PruningProjectionDecisionOutcome.REJECT
        rationale = "Temporary projection request rejected; no effect is applied."
    elif defer or review.insufficient_evidence_count > 0 or review.conflict_count > 0:
        outcome = PruningProjectionDecisionOutcome.DEFER
        rationale = "Projection request needs replay, evidence, or conflict review."
    elif eligible_for_future_projection:
        outcome = PruningProjectionDecisionOutcome.ELIGIBLE_FOR_FUTURE_PROJECTION
        rationale = "Request is eligible for future temporary projection review only."
    elif review.projection_recommended:
        outcome = PruningProjectionDecisionOutcome.PROJECTION_ONLY
        rationale = "Request can be represented as an inactive temporary projection only."
    else:
        outcome = PruningProjectionDecisionOutcome.REJECT
        rationale = "No useful temporary projection signal found."
    return PruningProjectionDecision(
        decision_id=_stable_id("projection-decision", (request.request_id, outcome.value, review.review_id)),
        request_id=request.request_id,
        outcome=outcome,
        rationale=rationale,
        reversible=outcome != PruningProjectionDecisionOutcome.BLOCKED_BY_INVARIANT,
        notes="decision is review-only; applied remains false",
    )


def create_temporary_pruning_projection(
    decision: PruningProjectionDecision,
    request: PruningProjectionRequest,
    *,
    projection_effect: PruningProjectionEffect | None = None,
    projection_strength: float | None = None,
    session_boundary: str = "current_session_only",
) -> TemporaryPruningProjection:
    effect = projection_effect or _effect_from_intent(request.requested_intent)
    strength = projection_strength if projection_strength is not None else _strength_from_request(request)
    affected_refs = tuple(sorted({signal.source_reference_id for signal in request.signals} | set(request.created_from_refs)))
    return TemporaryPruningProjection(
        projection_id=_stable_id("temporary-pruning-projection", (decision.decision_id, request.scope.scope_id, effect.value, *affected_refs)),
        decision_id=decision.decision_id,
        scope=request.scope,
        affected_source_references=affected_refs,
        projection_effect=effect,
        projection_strength=strength,
        session_boundary=session_boundary,
        reversible=decision.reversible,
        notes="inactive temporary projection record; projection is not applied in V1.4G",
    )


def create_projection_plan(
    *,
    requests: tuple[PruningProjectionRequest, ...] | list[PruningProjectionRequest] = (),
    decisions: tuple[PruningProjectionDecision, ...] | list[PruningProjectionDecision] = (),
    projections: tuple[TemporaryPruningProjection, ...] | list[TemporaryPruningProjection] = (),
    notes: str = "",
) -> PruningProjectionPlan:
    request_ids = tuple(sorted(request.request_id for request in requests))
    decision_ids = tuple(sorted(decision.decision_id for decision in decisions))
    projection_ids = tuple(sorted(projection.projection_id for projection in projections))
    return PruningProjectionPlan(
        plan_id=_stable_id("projection-plan", (*request_ids, *decision_ids, *projection_ids)),
        request_ids=request_ids,
        decision_ids=decision_ids,
        projection_ids=projection_ids,
        notes=notes or "plan is design-only; it cannot apply projections or schedule work",
    )


def create_projection_rollback_plan(
    projection: TemporaryPruningProjection,
    *,
    rollback_reason: str,
    required_evidence_or_approval: tuple[str, ...] = (),
) -> PruningProjectionRollbackPlan:
    approvals = tuple(sorted(required_evidence_or_approval))
    return PruningProjectionRollbackPlan(
        rollback_id=_stable_id("projection-rollback", (projection.projection_id, rollback_reason, *approvals)),
        projection_id=projection.projection_id,
        rollback_reason=rollback_reason,
        required_evidence_or_approval=approvals,
        reversible=projection.reversible,
        notes="rollback plan is inactive because V1.4G projections are inactive",
    )


def validate_projection_scope_lane_scoped(scope: PruningProjectionScope) -> bool:
    return not scope.applies_globally and not scope.canonical_scope and not scope.runtime_recall_scope


def validate_projection_request_review_only(request: PruningProjectionRequest) -> bool:
    return request.applied is False and validate_projection_scope_lane_scoped(request.scope)


def validate_projection_decision_review_only(decision: PruningProjectionDecision) -> bool:
    return decision.applied is False and all(value is False for value in decision.invariant_flags.values())


def validate_temporary_projection_inactive(projection: TemporaryPruningProjection) -> bool:
    return (
        projection.applied is False
        and projection.active is False
        and projection.canonical_mutation is False
        and projection.runtime_recall_mutation is False
        and validate_projection_scope_lane_scoped(projection.scope)
    )


def validate_projection_plan_inert(plan: PruningProjectionPlan) -> bool:
    return (
        plan.pruning_enabled is False
        and plan.canonical_pruning_enabled is False
        and plan.live_memory_mutation_enabled is False
        and plan.runtime_recall_mutation_enabled is False
        and plan.projection_application_enabled is False
        and plan.canonical_write_enabled is False
        and plan.active_store_enabled is False
        and plan.training_enabled is False
        and plan.provider_calls_enabled is False
        and plan.scheduler_enabled is False
        and plan.runtime_defaults_changed is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def validate_projection_review_result_not_applied(review: PruningProjectionReviewResult) -> bool:
    return review.applied is False


def validate_projection_rollback_not_applied(rollback: PruningProjectionRollbackPlan) -> bool:
    return rollback.applied is False


def _signal_type_from_pruning_proposal(proposal: PruningReviewProposal) -> PruningProjectionSignalType:
    if proposal.human_review_required or proposal.decision == PruningReviewDecision.REQUIRES_HUMAN_REVIEW:
        return PruningProjectionSignalType.HUMAN_REVIEW_REQUESTED
    if proposal.decision == PruningReviewDecision.PROPOSE_QUARANTINE_REVIEW:
        return PruningProjectionSignalType.UNSAFE_EVIDENCE_USE
    if proposal.decision == PruningReviewDecision.BENCHMARK_ONLY_NO_PRUNING:
        return PruningProjectionSignalType.PROVENANCE_GAP
    if proposal.decision == PruningReviewDecision.NO_PRUNING_REVIEW:
        return PruningProjectionSignalType.LOW_CONFIDENCE
    if proposal.failure_type.value == "same_topic_noise":
        return PruningProjectionSignalType.SAME_TOPIC_NOISE
    return PruningProjectionSignalType.NEGATIVE_FEEDBACK


def _signal_type_from_feedback(record: FeedbackCaptureRecord) -> PruningProjectionSignalType:
    if record.human_review_required:
        return PruningProjectionSignalType.HUMAN_REVIEW_REQUESTED
    if record.polarity == FeedbackPolarity.FLAGS_SAFETY_RISK:
        return PruningProjectionSignalType.UNSAFE_EVIDENCE_USE
    if record.polarity == FeedbackPolarity.FLAGS_NOISE:
        return PruningProjectionSignalType.SAME_TOPIC_NOISE
    if record.polarity == FeedbackPolarity.FLAGS_UNCERTAINTY:
        return PruningProjectionSignalType.LOW_CONFIDENCE
    return PruningProjectionSignalType.NEGATIVE_FEEDBACK


def _findings_for_request(request: PruningProjectionRequest) -> tuple[PruningProjectionReviewFinding, ...]:
    findings: list[PruningProjectionReviewFinding] = []
    if not validate_projection_scope_lane_scoped(request.scope):
        findings.append(PruningProjectionReviewFinding.BLOCKED_BY_INVARIANT)
    if request.requested_intent == PruningProjectionIntent.REJECT_PROJECTION:
        findings.append(PruningProjectionReviewFinding.REJECT_PROJECTION)
    if not request.signals:
        findings.append(PruningProjectionReviewFinding.INSUFFICIENT_EVIDENCE)
    for signal in request.signals:
        if signal.signal_type == PruningProjectionSignalType.HUMAN_REVIEW_REQUESTED:
            findings.append(PruningProjectionReviewFinding.HUMAN_REVIEW_REQUIRED)
        elif signal.signal_type in {
            PruningProjectionSignalType.CONTRADICTION,
            PruningProjectionSignalType.REPLAY_CONFLICT,
        }:
            findings.append(PruningProjectionReviewFinding.CONFLICT_REQUIRES_REPLAY)
        elif signal.normalized_severity() < 0.2:
            findings.append(PruningProjectionReviewFinding.INSUFFICIENT_EVIDENCE)
        else:
            findings.append(PruningProjectionReviewFinding.USEFUL_TEMPORARY_DAMPENING_SIGNAL)
    return tuple(_dedupe_preserve_order(findings or [PruningProjectionReviewFinding.REJECT_PROJECTION]))


def _review_rationale(findings: tuple[PruningProjectionReviewFinding, ...], recommended: bool) -> str:
    if recommended:
        return "Review found a useful temporary projection signal; no projection is applied."
    if PruningProjectionReviewFinding.BLOCKED_BY_INVARIANT in findings:
        return "Projection is blocked by lane-scope or safety invariants."
    if PruningProjectionReviewFinding.HUMAN_REVIEW_REQUIRED in findings:
        return "Projection requires human review before any future use."
    if PruningProjectionReviewFinding.CONFLICT_REQUIRES_REPLAY in findings:
        return "Projection should defer to replay/consolidation review."
    return "Projection is not justified by current evidence."


def _effect_from_intent(intent: PruningProjectionIntent) -> PruningProjectionEffect:
    if intent == PruningProjectionIntent.DAMPEN_TEMPORARILY:
        return PruningProjectionEffect.DAMPEN
    if intent == PruningProjectionIntent.QUARANTINE_FOR_REVIEW:
        return PruningProjectionEffect.QUARANTINE
    if intent == PruningProjectionIntent.EXCLUDE_FROM_HYPOTHETICAL_ANSWER:
        return PruningProjectionEffect.EXCLUDE_IN_LANE
    if intent == PruningProjectionIntent.REQUIRE_HUMAN_REVIEW:
        return PruningProjectionEffect.REQUIRE_REVIEW
    return PruningProjectionEffect.DEFER


def _strength_from_request(request: PruningProjectionRequest) -> float:
    if not request.signals:
        return 0.0
    return sum(signal.normalized_severity() for signal in request.signals) / len(request.signals)


def _severity_from_feedback(record: FeedbackCaptureRecord) -> float:
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


def _dedupe_preserve_order(values: list[PruningProjectionReviewFinding]) -> list[PruningProjectionReviewFinding]:
    seen: set[PruningProjectionReviewFinding] = set()
    output: list[PruningProjectionReviewFinding] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
