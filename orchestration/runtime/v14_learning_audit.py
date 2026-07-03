from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from orchestration.runtime.v14_controlled_learning import (
    ControlledLearningDecision,
    LearningCandidate,
    LearningSafetyReview,
    RUNTIME_V14H_INVARIANT_FLAGS,
)


@dataclass(frozen=True)
class LearningAuditRecord:
    audit_id: str
    candidate_id: str
    decision_id: str
    review_id: str
    source_refs: tuple[str, ...] = ()
    rationale: str = ""
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14H_INVARIANT_FLAGS))
    applied: bool = False
    persisted_to_active_store: bool = False
    training_triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "audit_id": self.audit_id,
            "candidate_id": self.candidate_id,
            "decision_id": self.decision_id,
            "review_id": self.review_id,
            "source_refs": list(self.source_refs),
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "persisted_to_active_store": self.persisted_to_active_store,
            "training_triggered": self.training_triggered,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_learning_audit_record(
    candidate: LearningCandidate,
    review: LearningSafetyReview,
    decision: ControlledLearningDecision,
    *,
    source_refs: tuple[str, ...] = (),
    rationale: str = "",
) -> LearningAuditRecord:
    refs = tuple(sorted({*source_refs, *candidate.source_artifact_references}))
    return LearningAuditRecord(
        audit_id=_stable_id("learning-audit", (candidate.candidate_id, review.review_id, decision.decision_id, *refs)),
        candidate_id=candidate.candidate_id,
        review_id=review.review_id,
        decision_id=decision.decision_id,
        source_refs=refs,
        rationale=rationale or decision.rationale,
        notes="audit record is report-only; it is not persisted to an active store and triggers no training",
    )


def validate_learning_audit_record_report_only(record: LearningAuditRecord) -> bool:
    return (
        record.applied is False
        and record.persisted_to_active_store is False
        and record.training_triggered is False
        and all(value is False for value in record.invariant_flags.values())
    )


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"
