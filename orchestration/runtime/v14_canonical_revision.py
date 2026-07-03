from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from orchestration.runtime.v14_canonical_store import (
    CanonicalMemoryRecord,
    CanonicalStoreDecision,
)


@dataclass(frozen=True)
class CanonicalRevisionRecord:
    revision_id: str
    target_record_id: str
    prior_record_id: str = ""
    change_rationale: str = ""
    source_refs: tuple[str, ...] = ()
    decision_id: str = ""
    rollback_plan_id: str = ""
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "revision_id": self.revision_id,
            "target_record_id": self.target_record_id,
            "prior_record_id": self.prior_record_id,
            "change_rationale": self.change_rationale,
            "source_refs": list(self.source_refs),
            "decision_id": self.decision_id,
            "rollback_plan_id": self.rollback_plan_id,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CanonicalRollbackPlan:
    rollback_plan_id: str
    target_record_id: str
    rollback_reason: str
    required_evidence_or_approval: tuple[str, ...] = ()
    reversible: bool = True
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "rollback_plan_id": self.rollback_plan_id,
            "target_record_id": self.target_record_id,
            "rollback_reason": self.rollback_reason,
            "required_evidence_or_approval": list(self.required_evidence_or_approval),
            "reversible": self.reversible,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_canonical_revision_record(
    record: CanonicalMemoryRecord,
    decision: CanonicalStoreDecision,
    *,
    prior_record_id: str = "",
    change_rationale: str = "",
    rollback_plan_id: str = "",
) -> CanonicalRevisionRecord:
    return CanonicalRevisionRecord(
        revision_id=_stable_id("canonical-revision-record", (record.record_id, decision.decision_id, prior_record_id)),
        target_record_id=record.record_id,
        prior_record_id=prior_record_id,
        change_rationale=change_rationale or decision.rationale,
        source_refs=record.provenance_refs,
        decision_id=decision.decision_id,
        rollback_plan_id=rollback_plan_id,
        notes="revision ledger shape only; not persisted or applied",
    )


def create_canonical_rollback_plan(
    record: CanonicalMemoryRecord,
    *,
    rollback_reason: str,
    required_evidence_or_approval: tuple[str, ...] = (),
    reversible: bool = True,
) -> CanonicalRollbackPlan:
    return CanonicalRollbackPlan(
        rollback_plan_id=_stable_id(
            "canonical-rollback-plan",
            (record.record_id, rollback_reason, *required_evidence_or_approval),
        ),
        target_record_id=record.record_id,
        rollback_reason=rollback_reason,
        required_evidence_or_approval=required_evidence_or_approval,
        reversible=reversible,
        notes="rollback plan only; rollback is not executed",
    )


def validate_revision_record_not_applied(revision: CanonicalRevisionRecord) -> bool:
    return revision.applied is False


def validate_rollback_plan_not_applied(plan: CanonicalRollbackPlan) -> bool:
    return plan.applied is False


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"
