from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14K_INVARIANT_FLAGS: dict[str, bool] = {
    "recall_bridge_enabled": False,
    "live_recall_enabled": False,
    "activation_integration_enabled": False,
    "attention_integration_enabled": False,
    "evidence_selection_integration_enabled": False,
    "canonical_write_enabled": False,
    "active_store_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "pruning_enabled": False,
    "canonical_pruning_enabled": False,
    "projection_application_enabled": False,
    "provider_calls_enabled": False,
    "specialist_routing_enabled": False,
    "scheduler_enabled": False,
    "active_replay_enabled": False,
    "live_routing_enabled": False,
    "execution_enabled": False,
    "runtime_defaults_changed": False,
}


class RecallBridgeSourceType(str, Enum):
    CANONICAL_MEMORY_DRAFT = "canonical_memory_draft"
    CANONICAL_MEMORY_RECORD = "canonical_memory_record"
    CONSOLIDATION_CANDIDATE = "consolidation_candidate"
    HYPOTHESIS_ARBITRATION_REPORT = "hypothesis_arbitration_report"
    SPECIALIST_MERGE_REPORT = "specialist_merge_report"
    LEARNING_CANDIDATE = "learning_candidate"
    PRUNING_PROJECTION_RECORD = "pruning_projection_record"
    REPLAY_REVIEW_RESULT = "replay_review_result"


class RecallBridgeEligibilityOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    CANDIDATE_ONLY = "candidate_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REQUIRES_REPLAY_REVIEW = "requires_replay_review"
    REQUIRES_HYPOTHESIS_ARBITRATION = "requires_hypothesis_arbitration"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_RECALL_REVIEW = "eligible_for_future_recall_review"


class RecallBridgeSafetyStatus(str, Enum):
    SAFE_FOR_FUTURE_REVIEW = "safe_for_future_review"
    INSUFFICIENT_PROVENANCE = "insufficient_provenance"
    LANE_SCOPE_MISMATCH = "lane_scope_mismatch"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT = "reject"


@dataclass(frozen=True)
class RecallBridgeSource:
    source_id: str
    source_type: RecallBridgeSourceType
    source_reference_id: str
    lane_scope: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    confidence_state: float = 0.0
    active: bool = False
    recall_enabled: bool = False
    canonical_mutation_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return _clamp(self.confidence_state)

    def as_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "source_reference_id": self.source_reference_id,
            "lane_scope": list(self.lane_scope),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "confidence_state": self.normalized_confidence(),
            "active": self.active,
            "recall_enabled": self.recall_enabled,
            "canonical_mutation_enabled": self.canonical_mutation_enabled,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RecallBridgeQuery:
    query_id: str
    query_text: str
    normalized_query: str
    lane_scope: tuple[str, ...] = ()
    source_constraints: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    safety_requirements: tuple[str, ...] = ()
    live_execution: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "query_id": self.query_id,
            "query_text": self.query_text,
            "normalized_query": self.normalized_query,
            "lane_scope": list(self.lane_scope),
            "source_constraints": list(self.source_constraints),
            "evidence_requirements": list(self.evidence_requirements),
            "safety_requirements": list(self.safety_requirements),
            "live_execution": self.live_execution,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RecallBridgeCandidate:
    candidate_id: str
    query_id: str
    source_id: str
    source_reference_id: str
    match_rationale: str = ""
    evidence_score: float = 0.0
    provenance_score: float = 0.0
    lane_fit_score: float = 0.0
    uncertainty_score: float = 1.0
    blocked_reason: str = ""
    retrieved: bool = False
    active_in_context: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_readiness(self) -> float:
        return _clamp(
            (self.evidence_score * 0.35)
            + (self.provenance_score * 0.3)
            + (self.lane_fit_score * 0.25)
            - (self.uncertainty_score * 0.15)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "query_id": self.query_id,
            "source_id": self.source_id,
            "source_reference_id": self.source_reference_id,
            "match_rationale": self.match_rationale,
            "evidence_score": _clamp(self.evidence_score),
            "provenance_score": _clamp(self.provenance_score),
            "lane_fit_score": _clamp(self.lane_fit_score),
            "uncertainty_score": _clamp(self.uncertainty_score),
            "readiness_score": self.normalized_readiness(),
            "blocked_reason": self.blocked_reason,
            "retrieved": self.retrieved,
            "active_in_context": self.active_in_context,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RecallBridgeEligibilityDecision:
    decision_id: str
    candidate_id: str
    outcome: RecallBridgeEligibilityOutcome
    rationale: str
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14K_INVARIANT_FLAGS))
    applied: bool = False
    recall_activated: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "recall_activated": self.recall_activated,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RecallBridgeSafetyReview:
    review_id: str
    candidate_id: str
    safety_status: RecallBridgeSafetyStatus
    rationale: str
    required_before_live_recall: tuple[str, ...] = ()
    blocked_by_invariants: bool = False
    live_recall_approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "candidate_id": self.candidate_id,
            "safety_status": self.safety_status.value,
            "rationale": self.rationale,
            "required_before_live_recall": list(self.required_before_live_recall),
            "blocked_by_invariants": self.blocked_by_invariants,
            "live_recall_approved": self.live_recall_approved,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RecallBridgeTrace:
    trace_id: str
    query_id: str
    candidate_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    safety_review_ids: tuple[str, ...] = ()
    source_reference_ids: tuple[str, ...] = ()
    generated_for_review_only: bool = True
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "query_id": self.query_id,
            "candidate_ids": list(self.candidate_ids),
            "decision_ids": list(self.decision_ids),
            "safety_review_ids": list(self.safety_review_ids),
            "source_reference_ids": list(self.source_reference_ids),
            "generated_for_review_only": self.generated_for_review_only,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RecallBridgePlan:
    plan_id: str
    source_ids: tuple[str, ...] = ()
    query_ids: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    trace_ids: tuple[str, ...] = ()
    recall_bridge_enabled: bool = False
    live_recall_enabled: bool = False
    activation_integration_enabled: bool = False
    attention_integration_enabled: bool = False
    evidence_selection_integration_enabled: bool = False
    canonical_write_enabled: bool = False
    active_store_enabled: bool = False
    memory_mutation_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    training_enabled: bool = False
    provider_calls_enabled: bool = False
    specialist_routing_enabled: bool = False
    scheduler_enabled: bool = False
    execution_enabled: bool = False
    runtime_defaults_changed: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14K_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "source_ids": list(self.source_ids),
            "query_ids": list(self.query_ids),
            "candidate_ids": list(self.candidate_ids),
            "decision_ids": list(self.decision_ids),
            "trace_ids": list(self.trace_ids),
            "recall_bridge_enabled": self.recall_bridge_enabled,
            "live_recall_enabled": self.live_recall_enabled,
            "activation_integration_enabled": self.activation_integration_enabled,
            "attention_integration_enabled": self.attention_integration_enabled,
            "evidence_selection_integration_enabled": self.evidence_selection_integration_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "active_store_enabled": self.active_store_enabled,
            "memory_mutation_enabled": self.memory_mutation_enabled,
            "runtime_recall_mutation_enabled": self.runtime_recall_mutation_enabled,
            "training_enabled": self.training_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "specialist_routing_enabled": self.specialist_routing_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "execution_enabled": self.execution_enabled,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RecallBridgeReportEntry:
    report_entry_id: str
    trace_id: str
    query_id: str
    candidate_summary: str
    decision_summary: str
    safety_summary: str
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = ""
    generated_for_review_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "trace_id": self.trace_id,
            "query_id": self.query_id,
            "candidate_summary": self.candidate_summary,
            "decision_summary": self.decision_summary,
            "safety_summary": self.safety_summary,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_recall_bridge_source(
    *,
    source_type: RecallBridgeSourceType,
    source_reference_id: str,
    lane_scope: tuple[str, ...] | list[str] = (),
    provenance_reference_ids: tuple[str, ...] | list[str] = (),
    confidence_state: float = 0.0,
    notes: str = "",
) -> RecallBridgeSource:
    source_id = _stable_id("recall-bridge-source", source_type.value, source_reference_id, lane_scope, provenance_reference_ids)
    return RecallBridgeSource(
        source_id=source_id,
        source_type=source_type,
        source_reference_id=source_reference_id,
        lane_scope=tuple(lane_scope),
        provenance_reference_ids=tuple(provenance_reference_ids),
        confidence_state=confidence_state,
        notes=notes or "source is inert and disconnected from live recall",
    )


def create_recall_bridge_query(
    *,
    query_text: str,
    normalized_query: str = "",
    lane_scope: tuple[str, ...] | list[str] = (),
    source_constraints: tuple[str, ...] | list[str] = (),
    evidence_requirements: tuple[str, ...] | list[str] = (),
    safety_requirements: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> RecallBridgeQuery:
    normalized = normalized_query or " ".join(query_text.lower().split())
    query_id = _stable_id("recall-bridge-query", normalized, lane_scope, source_constraints, evidence_requirements, safety_requirements)
    return RecallBridgeQuery(
        query_id=query_id,
        query_text=query_text,
        normalized_query=normalized,
        lane_scope=tuple(lane_scope),
        source_constraints=tuple(source_constraints),
        evidence_requirements=tuple(evidence_requirements),
        safety_requirements=tuple(safety_requirements),
        notes=notes or "query is hypothetical; no recall execution is performed",
    )


def create_recall_bridge_candidate(
    *,
    query: RecallBridgeQuery,
    source: RecallBridgeSource,
    match_rationale: str = "",
    evidence_score: float = 0.0,
    provenance_score: float | None = None,
    lane_fit_score: float | None = None,
    uncertainty_score: float = 1.0,
    blocked_reason: str = "",
    notes: str = "",
) -> RecallBridgeCandidate:
    provenance = provenance_score if provenance_score is not None else _provenance_score(source)
    lane_fit = lane_fit_score if lane_fit_score is not None else _lane_fit_score(query, source)
    candidate_id = _stable_id("recall-bridge-candidate", query.query_id, source.source_id, match_rationale, evidence_score, provenance, lane_fit)
    return RecallBridgeCandidate(
        candidate_id=candidate_id,
        query_id=query.query_id,
        source_id=source.source_id,
        source_reference_id=source.source_reference_id,
        match_rationale=match_rationale,
        evidence_score=evidence_score,
        provenance_score=provenance,
        lane_fit_score=lane_fit,
        uncertainty_score=uncertainty_score,
        blocked_reason=blocked_reason,
        notes=notes or "candidate is review-only; not retrieved or active in context",
    )


def review_recall_bridge_candidate(candidate: RecallBridgeCandidate) -> RecallBridgeSafetyReview:
    if any(value is True for value in RUNTIME_V14K_INVARIANT_FLAGS.values()):
        status = RecallBridgeSafetyStatus.BLOCKED_BY_INVARIANT
        rationale = "A V1.4K invariant blocks live recall."
        required = ("all recall bridge capability flags must remain false",)
        blocked = True
    elif candidate.blocked_reason:
        status = RecallBridgeSafetyStatus.REJECT
        rationale = candidate.blocked_reason
        required = ("resolve blocked reason",)
        blocked = False
    elif candidate.provenance_score < 0.25:
        status = RecallBridgeSafetyStatus.INSUFFICIENT_PROVENANCE
        rationale = "Candidate lacks enough provenance for future recall review."
        required = ("additional provenance",)
        blocked = False
    elif candidate.lane_fit_score < 0.25:
        status = RecallBridgeSafetyStatus.LANE_SCOPE_MISMATCH
        rationale = "Candidate lane scope does not fit the hypothetical query."
        required = ("lane-scope review",)
        blocked = False
    elif candidate.uncertainty_score > 0.8:
        status = RecallBridgeSafetyStatus.CONFLICTING_EVIDENCE
        rationale = "Candidate uncertainty is too high for future recall review."
        required = ("replay or hypothesis arbitration review",)
        blocked = False
    else:
        status = RecallBridgeSafetyStatus.SAFE_FOR_FUTURE_REVIEW
        rationale = "Candidate may be reviewed later; live recall remains disabled."
        required = ("explicit future recall activation phase",)
        blocked = False
    return RecallBridgeSafetyReview(
        review_id=_stable_id("recall-bridge-safety", candidate.candidate_id, status.value, rationale),
        candidate_id=candidate.candidate_id,
        safety_status=status,
        rationale=rationale,
        required_before_live_recall=required,
        blocked_by_invariants=blocked,
        notes="safety review does not approve live recall",
    )


def decide_recall_bridge_candidate(
    candidate: RecallBridgeCandidate,
    safety_review: RecallBridgeSafetyReview | None = None,
    *,
    require_human_review: bool = False,
    require_replay_review: bool = False,
    require_hypothesis_arbitration: bool = False,
    force_blocked: bool = False,
) -> RecallBridgeEligibilityDecision:
    review = safety_review or review_recall_bridge_candidate(candidate)
    if force_blocked or any(value is True for value in RUNTIME_V14K_INVARIANT_FLAGS.values()):
        outcome = RecallBridgeEligibilityOutcome.BLOCKED_BY_INVARIANT
        rationale = "Recall bridge is blocked by invariant; no live recall is permitted."
    elif require_human_review or review.safety_status == RecallBridgeSafetyStatus.HUMAN_REVIEW_REQUIRED:
        outcome = RecallBridgeEligibilityOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Candidate requires human review before future recall can be considered."
    elif require_replay_review or review.safety_status == RecallBridgeSafetyStatus.CONFLICTING_EVIDENCE:
        outcome = RecallBridgeEligibilityOutcome.REQUIRES_REPLAY_REVIEW
        rationale = "Candidate requires replay review before future recall can be considered."
    elif require_hypothesis_arbitration:
        outcome = RecallBridgeEligibilityOutcome.REQUIRES_HYPOTHESIS_ARBITRATION
        rationale = "Candidate requires report-only hypothesis arbitration."
    elif review.safety_status in {RecallBridgeSafetyStatus.INSUFFICIENT_PROVENANCE, RecallBridgeSafetyStatus.LANE_SCOPE_MISMATCH}:
        outcome = RecallBridgeEligibilityOutcome.DEFER
        rationale = review.rationale
    elif review.safety_status == RecallBridgeSafetyStatus.REJECT:
        outcome = RecallBridgeEligibilityOutcome.REJECT
        rationale = review.rationale
    elif candidate.normalized_readiness() >= 0.45:
        outcome = RecallBridgeEligibilityOutcome.ELIGIBLE_FOR_FUTURE_RECALL_REVIEW
        rationale = "Candidate is eligible for future recall review only; eligibility is not activation."
    else:
        outcome = RecallBridgeEligibilityOutcome.CANDIDATE_ONLY
        rationale = "Candidate may remain as report-only recall bridge material."
    return RecallBridgeEligibilityDecision(
        decision_id=_stable_id("recall-bridge-decision", candidate.candidate_id, outcome.value, review.review_id),
        candidate_id=candidate.candidate_id,
        outcome=outcome,
        rationale=rationale,
        notes="decision is not applied and does not activate recall",
    )


def create_recall_bridge_trace(
    *,
    query: RecallBridgeQuery,
    candidates: tuple[RecallBridgeCandidate, ...] | list[RecallBridgeCandidate] = (),
    decisions: tuple[RecallBridgeEligibilityDecision, ...] | list[RecallBridgeEligibilityDecision] = (),
    safety_reviews: tuple[RecallBridgeSafetyReview, ...] | list[RecallBridgeSafetyReview] = (),
    sources: tuple[RecallBridgeSource, ...] | list[RecallBridgeSource] = (),
    notes: str = "",
) -> RecallBridgeTrace:
    candidate_ids = tuple(sorted(candidate.candidate_id for candidate in candidates))
    decision_ids = tuple(sorted(decision.decision_id for decision in decisions))
    review_ids = tuple(sorted(review.review_id for review in safety_reviews))
    source_refs = tuple(sorted(source.source_reference_id for source in sources))
    trace_id = _stable_id("recall-bridge-trace", query.query_id, candidate_ids, decision_ids, review_ids, source_refs)
    return RecallBridgeTrace(
        trace_id=trace_id,
        query_id=query.query_id,
        candidate_ids=candidate_ids,
        decision_ids=decision_ids,
        safety_review_ids=review_ids,
        source_reference_ids=source_refs,
        notes=notes or "trace is generated for review only and is not applied",
    )


def create_recall_bridge_plan(
    *,
    sources: tuple[RecallBridgeSource, ...] | list[RecallBridgeSource] = (),
    queries: tuple[RecallBridgeQuery, ...] | list[RecallBridgeQuery] = (),
    candidates: tuple[RecallBridgeCandidate, ...] | list[RecallBridgeCandidate] = (),
    decisions: tuple[RecallBridgeEligibilityDecision, ...] | list[RecallBridgeEligibilityDecision] = (),
    traces: tuple[RecallBridgeTrace, ...] | list[RecallBridgeTrace] = (),
    notes: str = "",
) -> RecallBridgePlan:
    source_ids = tuple(sorted(source.source_id for source in sources))
    query_ids = tuple(sorted(query.query_id for query in queries))
    candidate_ids = tuple(sorted(candidate.candidate_id for candidate in candidates))
    decision_ids = tuple(sorted(decision.decision_id for decision in decisions))
    trace_ids = tuple(sorted(trace.trace_id for trace in traces))
    plan_id = _stable_id("recall-bridge-plan", source_ids, query_ids, candidate_ids, decision_ids, trace_ids)
    return RecallBridgePlan(
        plan_id=plan_id,
        source_ids=source_ids,
        query_ids=query_ids,
        candidate_ids=candidate_ids,
        decision_ids=decision_ids,
        trace_ids=trace_ids,
        notes=notes or "recall bridge plan is design-only; it cannot execute recall or schedule work",
    )


def create_recall_bridge_report_entry(
    *,
    trace: RecallBridgeTrace,
    candidates: tuple[RecallBridgeCandidate, ...] | list[RecallBridgeCandidate] = (),
    decisions: tuple[RecallBridgeEligibilityDecision, ...] | list[RecallBridgeEligibilityDecision] = (),
    safety_reviews: tuple[RecallBridgeSafetyReview, ...] | list[RecallBridgeSafetyReview] = (),
    unresolved_gaps: tuple[str, ...] | list[str] = (),
    recommended_next_review_step: str = "structural semantic adapter design",
    notes: str = "",
) -> RecallBridgeReportEntry:
    candidate_summary = f"{len(tuple(candidates))} candidate(s), none retrieved into runtime context"
    decision_summary = "; ".join(decision.outcome.value for decision in decisions) or "no decisions"
    safety_summary = "; ".join(review.safety_status.value for review in safety_reviews) or "no safety reviews"
    report_entry_id = _stable_id("recall-bridge-report-entry", trace.trace_id, candidate_summary, decision_summary, safety_summary)
    return RecallBridgeReportEntry(
        report_entry_id=report_entry_id,
        trace_id=trace.trace_id,
        query_id=trace.query_id,
        candidate_summary=candidate_summary,
        decision_summary=decision_summary,
        safety_summary=safety_summary,
        unresolved_gaps=tuple(unresolved_gaps),
        recommended_next_review_step=recommended_next_review_step,
        notes=notes or "report entry is review-only; no runtime state is mutated",
    )


def validate_recall_bridge_source_inert(source: RecallBridgeSource) -> bool:
    return source.active is False and source.recall_enabled is False and source.canonical_mutation_enabled is False


def validate_recall_bridge_query_inert(query: RecallBridgeQuery) -> bool:
    return query.live_execution is False


def validate_recall_bridge_candidate_not_retrieved(candidate: RecallBridgeCandidate) -> bool:
    return candidate.retrieved is False and candidate.active_in_context is False


def validate_recall_bridge_decision_review_only(decision: RecallBridgeEligibilityDecision) -> bool:
    return (
        decision.applied is False
        and decision.recall_activated is False
        and all(value is False for value in decision.invariant_flags.values())
    )


def validate_recall_bridge_safety_review_non_approving(review: RecallBridgeSafetyReview) -> bool:
    return review.live_recall_approved is False


def validate_recall_bridge_trace_review_only(trace: RecallBridgeTrace) -> bool:
    return trace.generated_for_review_only is True and trace.applied is False


def validate_recall_bridge_plan_inert(plan: RecallBridgePlan) -> bool:
    return (
        plan.recall_bridge_enabled is False
        and plan.live_recall_enabled is False
        and plan.activation_integration_enabled is False
        and plan.attention_integration_enabled is False
        and plan.evidence_selection_integration_enabled is False
        and plan.canonical_write_enabled is False
        and plan.active_store_enabled is False
        and plan.memory_mutation_enabled is False
        and plan.runtime_recall_mutation_enabled is False
        and plan.training_enabled is False
        and plan.provider_calls_enabled is False
        and plan.specialist_routing_enabled is False
        and plan.scheduler_enabled is False
        and plan.execution_enabled is False
        and plan.runtime_defaults_changed is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def validate_recall_bridge_report_entry_review_only(entry: RecallBridgeReportEntry) -> bool:
    return entry.generated_for_review_only is True


def _provenance_score(source: RecallBridgeSource) -> float:
    if not source.provenance_reference_ids:
        return 0.0
    return _clamp(min(1.0, len(set(source.provenance_reference_ids)) / 3.0))


def _lane_fit_score(query: RecallBridgeQuery, source: RecallBridgeSource) -> float:
    if not query.lane_scope:
        return 0.5
    if not source.lane_scope:
        return 0.0
    return 1.0 if set(query.lane_scope).intersection(source.lane_scope) else 0.0


def _stable_id(prefix: str, *parts: object) -> str:
    normalized = "|".join(_normalize_part(part) for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
