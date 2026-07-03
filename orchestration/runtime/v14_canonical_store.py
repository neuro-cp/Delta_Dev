from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_consolidation import (
    ConsolidationCandidate,
    ConsolidationDecision,
    ConsolidationDecisionOutcome,
)


RUNTIME_V14F_INVARIANT_FLAGS: dict[str, bool] = {
    "canonical_write_enabled": False,
    "active_store_enabled": False,
    "runtime_recall_enabled": False,
    "mutation_enabled": False,
    "training_enabled": False,
    "pruning_enabled": False,
    "provider_calls_enabled": False,
    "scheduler_enabled": False,
    "active_replay_enabled": False,
    "live_routing_enabled": False,
    "execution_enabled": False,
    "runtime_defaults_changed": False,
}


class CanonicalMemoryStatus(str, Enum):
    DRAFT_ONLY = "draft_only"
    INACTIVE = "inactive"
    PROPOSED = "proposed"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


class CanonicalStoreDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    DRAFT_ONLY = "draft_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_WRITE = "eligible_for_future_write"


@dataclass(frozen=True)
class CanonicalMemoryDraft:
    draft_id: str
    source_candidate_id: str
    source_decision_id: str
    content: str
    provenance_refs: tuple[str, ...] = ()
    confidence: float = 0.0
    evidence_state: str = "review_only"
    lane_scope: tuple[str, ...] = ()
    eligibility_notes: tuple[str, ...] = ()
    active: bool = False
    canonical_write_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "draft_id": self.draft_id,
            "source_candidate_id": self.source_candidate_id,
            "source_decision_id": self.source_decision_id,
            "content": self.content,
            "provenance_refs": list(self.provenance_refs),
            "confidence": self.normalized_confidence(),
            "evidence_state": self.evidence_state,
            "lane_scope": list(self.lane_scope),
            "eligibility_notes": list(self.eligibility_notes),
            "active": self.active,
            "canonical_write_enabled": self.canonical_write_enabled,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CanonicalMemoryRecord:
    record_id: str
    content: str
    provenance_refs: tuple[str, ...]
    confidence_state: float
    evidence_state: str
    revision_id: str
    created_from_candidate_id: str
    status: CanonicalMemoryStatus = CanonicalMemoryStatus.PROPOSED
    active: bool = False
    runtime_recall_enabled: bool = False
    canonical_write_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence_state)))

    def as_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "content": self.content,
            "provenance_refs": list(self.provenance_refs),
            "confidence_state": self.normalized_confidence(),
            "evidence_state": self.evidence_state,
            "revision_id": self.revision_id,
            "created_from_candidate_id": self.created_from_candidate_id,
            "status": self.status.value,
            "active": self.active,
            "runtime_recall_enabled": self.runtime_recall_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CanonicalStoreDecision:
    decision_id: str
    draft_id: str
    outcome: CanonicalStoreDecisionOutcome
    rationale: str
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14F_INVARIANT_FLAGS))
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "draft_id": self.draft_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CanonicalStorePlan:
    plan_id: str
    draft_ids: tuple[str, ...] = ()
    record_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    canonical_write_enabled: bool = False
    runtime_recall_enabled: bool = False
    active_store_enabled: bool = False
    mutation_enabled: bool = False
    training_enabled: bool = False
    pruning_enabled: bool = False
    provider_calls_enabled: bool = False
    scheduler_enabled: bool = False
    runtime_defaults_changed: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14F_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "draft_ids": list(self.draft_ids),
            "record_ids": list(self.record_ids),
            "decision_ids": list(self.decision_ids),
            "canonical_write_enabled": self.canonical_write_enabled,
            "runtime_recall_enabled": self.runtime_recall_enabled,
            "active_store_enabled": self.active_store_enabled,
            "mutation_enabled": self.mutation_enabled,
            "training_enabled": self.training_enabled,
            "pruning_enabled": self.pruning_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_canonical_memory_draft(
    candidate: ConsolidationCandidate,
    decision: ConsolidationDecision,
    *,
    content: str | None = None,
    lane_scope: tuple[str, ...] = (),
    eligibility_notes: tuple[str, ...] = (),
) -> CanonicalMemoryDraft:
    provenance = _provenance_from_candidate(candidate)
    return CanonicalMemoryDraft(
        draft_id=_stable_id(
            "canonical-draft",
            (candidate.candidate_id, decision.decision_id, content or candidate.summary, *provenance),
        ),
        source_candidate_id=candidate.candidate_id,
        source_decision_id=decision.decision_id,
        content=content or candidate.summary,
        provenance_refs=provenance,
        confidence=candidate.normalized_confidence(),
        evidence_state=_evidence_state_from_decision(decision),
        lane_scope=lane_scope,
        eligibility_notes=eligibility_notes or _eligibility_notes(candidate, decision),
        notes="draft only; not active memory and not written to a canonical store",
    )


def create_inactive_canonical_memory_record(
    draft: CanonicalMemoryDraft,
    *,
    status: CanonicalMemoryStatus = CanonicalMemoryStatus.PROPOSED,
) -> CanonicalMemoryRecord:
    revision_id = _stable_id("canonical-revision", (draft.draft_id, "initial-inactive"))
    return CanonicalMemoryRecord(
        record_id=_stable_id("canonical-record", (draft.draft_id, draft.content)),
        content=draft.content,
        provenance_refs=draft.provenance_refs,
        confidence_state=draft.normalized_confidence(),
        evidence_state=draft.evidence_state,
        revision_id=revision_id,
        created_from_candidate_id=draft.source_candidate_id,
        status=status,
        notes="record shape only; inactive and disconnected from runtime recall",
    )


def decide_canonical_store(
    draft: CanonicalMemoryDraft,
    *,
    require_human_review: bool = False,
    invariant_block: bool = False,
    reject: bool = False,
    defer: bool = False,
    eligible_for_future_write: bool = False,
) -> CanonicalStoreDecision:
    if invariant_block:
        outcome = CanonicalStoreDecisionOutcome.BLOCKED_BY_INVARIANT
        rationale = "A V1.4F invariant blocks any future canonical write."
    elif require_human_review:
        outcome = CanonicalStoreDecisionOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Human review is required before any future canonical write can be considered."
    elif reject:
        outcome = CanonicalStoreDecisionOutcome.REJECT
        rationale = "Draft rejected by store design review; no write is applied."
    elif defer:
        outcome = CanonicalStoreDecisionOutcome.DEFER
        rationale = "Draft needs more evidence before future canonical write review."
    elif eligible_for_future_write:
        outcome = CanonicalStoreDecisionOutcome.ELIGIBLE_FOR_FUTURE_WRITE
        rationale = "Draft is eligible for future write review only; V1.4F does not write it."
    else:
        outcome = CanonicalStoreDecisionOutcome.DRAFT_ONLY
        rationale = "Draft may remain as an inert canonical memory draft."
    return CanonicalStoreDecision(
        decision_id=_stable_id("canonical-store-decision", (draft.draft_id, outcome.value)),
        draft_id=draft.draft_id,
        outcome=outcome,
        rationale=rationale,
        notes="decision is review-only; applied remains false",
    )


def create_canonical_store_plan(
    *,
    drafts: tuple[CanonicalMemoryDraft, ...] | list[CanonicalMemoryDraft] = (),
    records: tuple[CanonicalMemoryRecord, ...] | list[CanonicalMemoryRecord] = (),
    decisions: tuple[CanonicalStoreDecision, ...] | list[CanonicalStoreDecision] = (),
    notes: str = "",
) -> CanonicalStorePlan:
    draft_ids = tuple(sorted(draft.draft_id for draft in drafts))
    record_ids = tuple(sorted(record.record_id for record in records))
    decision_ids = tuple(sorted(decision.decision_id for decision in decisions))
    return CanonicalStorePlan(
        plan_id=_stable_id("canonical-store-plan", (*draft_ids, *record_ids, *decision_ids)),
        draft_ids=draft_ids,
        record_ids=record_ids,
        decision_ids=decision_ids,
        notes=notes or "store plan is hypothetical; it cannot execute writes or schedule work",
    )


def validate_canonical_draft_inert(draft: CanonicalMemoryDraft) -> bool:
    return draft.active is False and draft.canonical_write_enabled is False


def validate_canonical_record_inactive(record: CanonicalMemoryRecord) -> bool:
    return (
        record.active is False
        and record.runtime_recall_enabled is False
        and record.canonical_write_enabled is False
        and record.status
        in {
            CanonicalMemoryStatus.DRAFT_ONLY,
            CanonicalMemoryStatus.INACTIVE,
            CanonicalMemoryStatus.PROPOSED,
            CanonicalMemoryStatus.REJECTED,
            CanonicalMemoryStatus.DEFERRED,
            CanonicalMemoryStatus.REQUIRES_HUMAN_REVIEW,
            CanonicalMemoryStatus.BLOCKED_BY_INVARIANT,
        }
    )


def validate_canonical_decision_review_only(decision: CanonicalStoreDecision) -> bool:
    return decision.applied is False and all(value is False for value in decision.invariant_flags.values())


def validate_canonical_store_plan_inert(plan: CanonicalStorePlan) -> bool:
    return (
        plan.canonical_write_enabled is False
        and plan.runtime_recall_enabled is False
        and plan.active_store_enabled is False
        and plan.mutation_enabled is False
        and plan.training_enabled is False
        and plan.pruning_enabled is False
        and plan.provider_calls_enabled is False
        and plan.scheduler_enabled is False
        and plan.runtime_defaults_changed is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def _provenance_from_candidate(candidate: ConsolidationCandidate) -> tuple[str, ...]:
    return tuple(
        ref
        for ref in (
            candidate.source_batch_id,
            candidate.source_review_id,
            *candidate.source_episode_ids,
            *candidate.source_feedback_ids,
            *candidate.source_replay_marker_ids,
            *candidate.source_pruning_proposal_ids,
        )
        if ref
    )


def _evidence_state_from_decision(decision: ConsolidationDecision) -> str:
    if decision.outcome == ConsolidationDecisionOutcome.CANDIDATE_ONLY:
        return "candidate_reviewed"
    if decision.outcome == ConsolidationDecisionOutcome.REQUIRES_HUMAN_REVIEW:
        return "requires_human_review"
    if decision.outcome == ConsolidationDecisionOutcome.BLOCKED_BY_INVARIANT:
        return "blocked_by_invariant"
    if decision.outcome == ConsolidationDecisionOutcome.REJECT:
        return "rejected"
    return "deferred"


def _eligibility_notes(
    candidate: ConsolidationCandidate,
    decision: ConsolidationDecision,
) -> tuple[str, ...]:
    return (
        f"candidate_kind={candidate.candidate_kind.value}",
        f"consolidation_decision={decision.outcome.value}",
        "canonical write disabled in V1.4F",
    )


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"
