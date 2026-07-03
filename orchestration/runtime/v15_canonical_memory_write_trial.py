from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V15H_CANONICAL_WRITE_TRIAL_FLAGS: dict[str, bool] = {
    "canonical_memory_write_trial_design_enabled": True,
    "write_trial_report_enabled": True,
    "write_enabled": False,
    "canonical_write_executed": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "recall_activation_enabled": False,
    "rollback_executed": False,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "training_enabled": False,
    "dataset_export_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class CanonicalMemoryWriteOutcome(str, Enum):
    DESIGN_ONLY = "design_only"
    BLOCKED_APPROVAL_ABSENT = "blocked_approval_absent"
    ELIGIBLE_FOR_FUTURE_EXPLICIT_WRITE_TRIAL = "eligible_for_future_explicit_write_trial"
    REJECT = "reject"


@dataclass(frozen=True)
class CanonicalMemoryWriteCandidate:
    write_candidate_id: str
    memory_candidate_id: str
    proposed_memory_text: str
    provenance_reference_ids: tuple[str, ...]
    eligible_for_future_write_trial: bool = True
    active_canonical_record: bool = False
    write_enabled: bool = False
    canonical_write_executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryWriteApprovalGate:
    approval_gate_id: str
    write_candidate_id: str
    required_actor: str = "human_operator"
    explicit_approval_required: bool = True
    approval_present: bool = False
    satisfied: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryWriteSafetyReview:
    safety_review_id: str
    write_candidate_id: str
    safety_status: str
    required_before_write: tuple[str, ...]
    approved: bool = False
    write_safe_now: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryWritePlan:
    write_plan_id: str
    write_candidate_id: str
    plan_summary: str
    design_only: bool = True
    write_enabled: bool = False
    canonical_write_executed: bool = False
    recall_activation_enabled: bool = False
    training_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryRollbackReference:
    rollback_reference_id: str
    write_candidate_id: str
    rollback_summary: str
    rollback_executable_now: bool = False
    rollback_executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryWriteDecision:
    decision_id: str
    write_candidate_id: str
    outcome: CanonicalMemoryWriteOutcome
    rationale: str
    applied: bool = False
    canonical_write_triggered: bool = False
    recall_triggered: bool = False
    training_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryWriteAuditRecord:
    audit_id: str
    write_candidate_id: str
    decision_id: str
    audit_summary: str
    generated_for_review_only: bool = True
    canonical_write_executed: bool = False
    memory_mutated: bool = False
    recall_mutated: bool = False
    rollback_executed: bool = False
    training_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryWriteTrialReportEntry:
    report_entry_id: str
    write_candidate_id: str
    candidate_summary: str
    approval_summary: str
    safety_summary: str
    rollback_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def build_canonical_memory_write_trial_design(memory_candidate_id: str, proposed_memory_text: str, provenance_reference_ids: tuple[str, ...]) -> dict[str, object]:
    candidate = CanonicalMemoryWriteCandidate(
        write_candidate_id=_stable_id("canonical-write-candidate", memory_candidate_id, proposed_memory_text, provenance_reference_ids),
        memory_candidate_id=memory_candidate_id,
        proposed_memory_text=proposed_memory_text,
        provenance_reference_ids=provenance_reference_ids,
    )
    approval = CanonicalMemoryWriteApprovalGate(
        approval_gate_id=_stable_id("canonical-write-approval", candidate.write_candidate_id),
        write_candidate_id=candidate.write_candidate_id,
    )
    safety = CanonicalMemoryWriteSafetyReview(
        safety_review_id=_stable_id("canonical-write-safety", candidate.write_candidate_id),
        write_candidate_id=candidate.write_candidate_id,
        safety_status="blocked_until_explicit_human_approval_and_future_write_phase",
        required_before_write=(
            "explicit human approval",
            "audit trace",
            "rollback reference",
            "canonical write gate opened in a future phase",
            "recall activation separately authorized after write",
        ),
    )
    plan = CanonicalMemoryWritePlan(
        write_plan_id=_stable_id("canonical-write-plan", candidate.write_candidate_id),
        write_candidate_id=candidate.write_candidate_id,
        plan_summary="Design-only plan for a future explicitly approved local canonical memory write trial.",
    )
    rollback = CanonicalMemoryRollbackReference(
        rollback_reference_id=_stable_id("canonical-rollback-ref", candidate.write_candidate_id),
        write_candidate_id=candidate.write_candidate_id,
        rollback_summary="Rollback reference is documented but not executable in V1.5H.",
    )
    decision = CanonicalMemoryWriteDecision(
        decision_id=_stable_id("canonical-write-decision", candidate.write_candidate_id),
        write_candidate_id=candidate.write_candidate_id,
        outcome=CanonicalMemoryWriteOutcome.BLOCKED_APPROVAL_ABSENT,
        rationale="V1.5H is design-only; approval is absent and canonical writes remain disabled.",
    )
    audit = CanonicalMemoryWriteAuditRecord(
        audit_id=_stable_id("canonical-write-audit", candidate.write_candidate_id, decision.decision_id),
        write_candidate_id=candidate.write_candidate_id,
        decision_id=decision.decision_id,
        audit_summary="Canonical memory write trial design created without write, recall mutation, rollback execution, or training.",
    )
    entry = CanonicalMemoryWriteTrialReportEntry(
        report_entry_id=_stable_id("canonical-write-entry", candidate.write_candidate_id),
        write_candidate_id=candidate.write_candidate_id,
        candidate_summary=proposed_memory_text,
        approval_summary="explicit human approval required and absent",
        safety_summary=safety.safety_status,
        rollback_summary=rollback.rollback_summary,
        decision_summary=decision.outcome.value,
        unresolved_gaps=("approval absent", "write gate closed", "recall activation closed"),
        recommended_next_review_step="explicit user-approved write trial or recall bridge limited trial design",
    )
    return {
        "write_candidate": candidate.as_dict(),
        "approval_gate": approval.as_dict(),
        "safety_review": safety.as_dict(),
        "write_plan": plan.as_dict(),
        "rollback_reference": rollback.as_dict(),
        "decision": decision.as_dict(),
        "audit_record": audit.as_dict(),
        "report_entry": entry.as_dict(),
        "invariant_flags": dict(RUNTIME_V15H_CANONICAL_WRITE_TRIAL_FLAGS),
    }


def sample_canonical_memory_write_trial_design() -> dict[str, object]:
    return build_canonical_memory_write_trial_design(
        "memory-candidate-hyb1-dormant-review",
        "HYB1 remains dormant and environment-gated; Model B remains the default runtime baseline.",
        ("feedback-interaction-sample", "memory-candidate-sample"),
    )


def validate_canonical_memory_write_trial_safe(data: dict[str, object]) -> bool:
    candidate = data["write_candidate"]
    approval = data["approval_gate"]
    plan = data["write_plan"]
    rollback = data["rollback_reference"]
    decision = data["decision"]
    audit = data["audit_record"]
    flags = data["invariant_flags"]
    return (
        candidate["write_enabled"] is False
        and candidate["canonical_write_executed"] is False
        and approval["approval_present"] is False
        and approval["satisfied"] is False
        and plan["design_only"] is True
        and plan["write_enabled"] is False
        and plan["canonical_write_executed"] is False
        and plan["recall_activation_enabled"] is False
        and plan["training_enabled"] is False
        and rollback["rollback_executable_now"] is False
        and rollback["rollback_executed"] is False
        and decision["applied"] is False
        and decision["canonical_write_triggered"] is False
        and decision["recall_triggered"] is False
        and decision["training_triggered"] is False
        and audit["canonical_write_executed"] is False
        and audit["memory_mutated"] is False
        and audit["recall_mutated"] is False
        and audit["rollback_executed"] is False
        and audit["training_triggered"] is False
        and flags["canonical_memory_write_trial_design_enabled"] is True
        and flags["write_trial_report_enabled"] is True
        and all(value is False for key, value in flags.items() if key not in {"canonical_memory_write_trial_design_enabled", "write_trial_report_enabled"})
    )


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, tuple):
            values[key] = [item.value if isinstance(item, Enum) else item for item in value]
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(_normalize_part(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
