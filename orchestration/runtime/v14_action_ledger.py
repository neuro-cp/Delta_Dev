from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14P_INVARIANT_FLAGS: dict[str, bool] = {
    "action_ledger_enabled": False,
    "active_ledger_enabled": False,
    "ledger_persistence_enabled": False,
    "action_execution_enabled": False,
    "dry_run_execution_enabled": False,
    "side_effects_enabled": False,
    "tool_calls_enabled": False,
    "provider_calls_enabled": False,
    "autonomous_approval_enabled": False,
    "human_approval_required_for_risky_actions": True,
    "authorization_required_before_ledger": True,
    "ledger_required_before_execution": True,
    "rollback_execution_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class ActionLedgerStatus(str, Enum):
    DRAFT = "draft"
    REVIEW_ONLY = "review_only"
    BLOCKED_MISSING_AUTHORIZATION = "blocked_missing_authorization"
    BLOCKED_MISSING_APPROVAL = "blocked_missing_approval"
    ELIGIBLE_FOR_FUTURE_DRY_RUN = "eligible_for_future_dry_run"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ActionLedgerOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    REVIEW_ONLY = "review_only"
    LEDGER_ENTRY_ONLY = "ledger_entry_only"
    BLOCKED_MISSING_AUTHORIZATION = "blocked_missing_authorization"
    BLOCKED_MISSING_HUMAN_APPROVAL = "blocked_missing_human_approval"
    ELIGIBLE_FOR_FUTURE_DRY_RUN = "eligible_for_future_dry_run"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


@dataclass(frozen=True)
class ActionLedgerEntry:
    ledger_entry_id: str
    action_intent_id: str
    authorization_decision_id: str = ""
    risk_assessment_id: str = ""
    dry_run_plan_id: str = ""
    source_reference_ids: tuple[str, ...] = ()
    ledger_status: ActionLedgerStatus = ActionLedgerStatus.DRAFT
    action_summary: str = ""
    side_effect_boundary: str = "no side effects permitted"
    human_approval_required: bool = True
    human_approval_present: bool = False
    active: bool = False
    persisted_to_active_ledger: bool = False
    action_executed: bool = False
    side_effects_created: bool = False
    tool_called: bool = False
    provider_called: bool = False
    autonomous_approval_used: bool = False
    memory_mutated: bool = False
    runtime_recall_mutated: bool = False
    training_triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "ledger_entry_id": self.ledger_entry_id,
            "action_intent_id": self.action_intent_id,
            "authorization_decision_id": self.authorization_decision_id,
            "risk_assessment_id": self.risk_assessment_id,
            "dry_run_plan_id": self.dry_run_plan_id,
            "source_reference_ids": list(self.source_reference_ids),
            "ledger_status": self.ledger_status.value,
            "action_summary": self.action_summary,
            "side_effect_boundary": self.side_effect_boundary,
            "human_approval_required": self.human_approval_required,
            "human_approval_present": self.human_approval_present,
            "active": self.active,
            "persisted_to_active_ledger": self.persisted_to_active_ledger,
            "action_executed": self.action_executed,
            "side_effects_created": self.side_effects_created,
            "tool_called": self.tool_called,
            "provider_called": self.provider_called,
            "autonomous_approval_used": self.autonomous_approval_used,
            "memory_mutated": self.memory_mutated,
            "runtime_recall_mutated": self.runtime_recall_mutated,
            "training_triggered": self.training_triggered,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ActionLedgerPlan:
    ledger_plan_id: str
    ledger_entry_ids: tuple[str, ...] = ()
    required_before_execution: bool = True
    append_only_required: bool = True
    immutable_audit_required: bool = True
    rollback_reference_required: bool = True
    active_ledger_enabled: bool = False
    ledger_persistence_enabled: bool = False
    action_execution_enabled: bool = False
    side_effects_enabled: bool = False
    scheduler_enabled: bool = False
    background_queue_enabled: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14P_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "ledger_plan_id": self.ledger_plan_id,
            "ledger_entry_ids": list(self.ledger_entry_ids),
            "required_before_execution": self.required_before_execution,
            "append_only_required": self.append_only_required,
            "immutable_audit_required": self.immutable_audit_required,
            "rollback_reference_required": self.rollback_reference_required,
            "active_ledger_enabled": self.active_ledger_enabled,
            "ledger_persistence_enabled": self.ledger_persistence_enabled,
            "action_execution_enabled": self.action_execution_enabled,
            "side_effects_enabled": self.side_effects_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "background_queue_enabled": self.background_queue_enabled,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ActionAuditTrace:
    audit_trace_id: str
    ledger_entry_id: str
    source_reference_ids: tuple[str, ...] = ()
    authorization_reference_ids: tuple[str, ...] = ()
    risk_reference_ids: tuple[str, ...] = ()
    decision_reference_ids: tuple[str, ...] = ()
    trace_summary: str = ""
    generated_for_review_only: bool = True
    persisted_to_active_ledger: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "audit_trace_id": self.audit_trace_id,
            "ledger_entry_id": self.ledger_entry_id,
            "source_reference_ids": list(self.source_reference_ids),
            "authorization_reference_ids": list(self.authorization_reference_ids),
            "risk_reference_ids": list(self.risk_reference_ids),
            "decision_reference_ids": list(self.decision_reference_ids),
            "trace_summary": self.trace_summary,
            "generated_for_review_only": self.generated_for_review_only,
            "persisted_to_active_ledger": self.persisted_to_active_ledger,
            "applied": self.applied,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ActionRollbackReference:
    rollback_reference_id: str
    ledger_entry_id: str
    rollback_possible: bool = False
    rollback_strategy: str = "no rollback strategy executable in V1.4P"
    rollback_requires_human_approval: bool = True
    rollback_target_reference: str = ""
    rollback_executed: bool = False
    side_effect_reversal_executed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "rollback_reference_id": self.rollback_reference_id,
            "ledger_entry_id": self.ledger_entry_id,
            "rollback_possible": self.rollback_possible,
            "rollback_strategy": self.rollback_strategy,
            "rollback_requires_human_approval": self.rollback_requires_human_approval,
            "rollback_target_reference": self.rollback_target_reference,
            "rollback_executed": self.rollback_executed,
            "side_effect_reversal_executed": self.side_effect_reversal_executed,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ActionLedgerDecision:
    decision_id: str
    ledger_entry_id: str
    outcome: ActionLedgerOutcome
    rationale: str
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14P_INVARIANT_FLAGS))
    applied: bool = False
    ledger_written: bool = False
    action_executed: bool = False
    side_effects_created: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "ledger_entry_id": self.ledger_entry_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "ledger_written": self.ledger_written,
            "action_executed": self.action_executed,
            "side_effects_created": self.side_effects_created,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ActionLedgerReportEntry:
    report_entry_id: str
    ledger_entry_id: str
    decision_id: str
    audit_trace_id: str = ""
    rollback_reference_id: str = ""
    ledger_summary: str = ""
    audit_summary: str = ""
    rollback_summary: str = ""
    decision_summary: str = ""
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = "design dry-run action execution without side effects"
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "ledger_entry_id": self.ledger_entry_id,
            "audit_trace_id": self.audit_trace_id,
            "rollback_reference_id": self.rollback_reference_id,
            "decision_id": self.decision_id,
            "ledger_summary": self.ledger_summary,
            "audit_summary": self.audit_summary,
            "rollback_summary": self.rollback_summary,
            "decision_summary": self.decision_summary,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
        }


def create_action_ledger_entry(
    *,
    action_intent_id: str,
    authorization_decision_id: str = "",
    risk_assessment_id: str = "",
    dry_run_plan_id: str = "",
    source_reference_ids: tuple[str, ...] = (),
    ledger_status: ActionLedgerStatus | None = None,
    action_summary: str = "",
    side_effect_boundary: str = "no side effects permitted",
    human_approval_required: bool = True,
) -> ActionLedgerEntry:
    status = ledger_status or _status_for_inputs(authorization_decision_id, human_approval_required)
    ledger_entry_id = _stable_id(
        "action-ledger-entry",
        action_intent_id,
        authorization_decision_id,
        risk_assessment_id,
        dry_run_plan_id,
        ",".join(source_reference_ids),
        status.value,
        action_summary,
    )
    return ActionLedgerEntry(
        ledger_entry_id=ledger_entry_id,
        action_intent_id=action_intent_id,
        authorization_decision_id=authorization_decision_id,
        risk_assessment_id=risk_assessment_id,
        dry_run_plan_id=dry_run_plan_id,
        source_reference_ids=tuple(source_reference_ids),
        ledger_status=status,
        action_summary=action_summary.strip(),
        side_effect_boundary=side_effect_boundary.strip(),
        human_approval_required=human_approval_required,
    )


def create_action_ledger_plan(entries: tuple[ActionLedgerEntry, ...]) -> ActionLedgerPlan:
    ledger_entry_ids = tuple(entry.ledger_entry_id for entry in entries)
    ledger_plan_id = _stable_id("action-ledger-plan", ",".join(ledger_entry_ids))
    return ActionLedgerPlan(ledger_plan_id=ledger_plan_id, ledger_entry_ids=ledger_entry_ids)


def create_action_audit_trace(
    entry: ActionLedgerEntry,
    *,
    authorization_reference_ids: tuple[str, ...] = (),
    risk_reference_ids: tuple[str, ...] = (),
    decision_reference_ids: tuple[str, ...] = (),
    trace_summary: str = "",
) -> ActionAuditTrace:
    audit_trace_id = _stable_id(
        "action-audit-trace",
        entry.ledger_entry_id,
        ",".join(entry.source_reference_ids),
        ",".join(authorization_reference_ids),
        ",".join(risk_reference_ids),
        ",".join(decision_reference_ids),
        trace_summary,
    )
    return ActionAuditTrace(
        audit_trace_id=audit_trace_id,
        ledger_entry_id=entry.ledger_entry_id,
        source_reference_ids=entry.source_reference_ids,
        authorization_reference_ids=tuple(authorization_reference_ids),
        risk_reference_ids=tuple(risk_reference_ids),
        decision_reference_ids=tuple(decision_reference_ids),
        trace_summary=trace_summary.strip(),
    )


def create_action_rollback_reference(
    entry: ActionLedgerEntry,
    *,
    rollback_possible: bool = False,
    rollback_strategy: str = "no rollback strategy executable in V1.4P",
    rollback_target_reference: str = "",
) -> ActionRollbackReference:
    rollback_reference_id = _stable_id(
        "action-rollback-reference",
        entry.ledger_entry_id,
        rollback_possible,
        rollback_strategy,
        rollback_target_reference,
    )
    return ActionRollbackReference(
        rollback_reference_id=rollback_reference_id,
        ledger_entry_id=entry.ledger_entry_id,
        rollback_possible=rollback_possible,
        rollback_strategy=rollback_strategy.strip(),
        rollback_target_reference=rollback_target_reference.strip(),
    )


def decide_action_ledger(entry: ActionLedgerEntry) -> ActionLedgerDecision:
    if _invariants_drifted():
        outcome = ActionLedgerOutcome.BLOCKED_BY_INVARIANT
        rationale = "action ledger invariant flags are not in the design-only baseline"
    elif not entry.authorization_decision_id:
        outcome = ActionLedgerOutcome.BLOCKED_MISSING_AUTHORIZATION
        rationale = "authorization decision is required before ledger eligibility"
    elif entry.human_approval_required and not entry.human_approval_present:
        outcome = ActionLedgerOutcome.BLOCKED_MISSING_HUMAN_APPROVAL
        rationale = "human approval is required before any future execution path"
    elif entry.ledger_status == ActionLedgerStatus.REJECTED:
        outcome = ActionLedgerOutcome.REJECT
        rationale = "ledger entry was rejected for future action review"
    elif entry.ledger_status == ActionLedgerStatus.DEFERRED:
        outcome = ActionLedgerOutcome.DEFER
        rationale = "ledger entry is deferred for future review"
    elif entry.ledger_status == ActionLedgerStatus.ELIGIBLE_FOR_FUTURE_DRY_RUN:
        outcome = ActionLedgerOutcome.ELIGIBLE_FOR_FUTURE_DRY_RUN
        rationale = "eligible only for future dry-run ledger review"
    else:
        outcome = ActionLedgerOutcome.LEDGER_ENTRY_ONLY
        rationale = "ledger entry is inert and not persisted to an active ledger"
    decision_id = _stable_id("action-ledger-decision", entry.ledger_entry_id, outcome.value, rationale)
    return ActionLedgerDecision(
        decision_id=decision_id,
        ledger_entry_id=entry.ledger_entry_id,
        outcome=outcome,
        rationale=rationale,
    )


def create_action_ledger_report_entry(
    *,
    entry: ActionLedgerEntry,
    audit_trace: ActionAuditTrace,
    rollback_reference: ActionRollbackReference,
    decision: ActionLedgerDecision,
    unresolved_gaps: tuple[str, ...] = (),
) -> ActionLedgerReportEntry:
    report_entry_id = _stable_id(
        "action-ledger-report-entry",
        entry.ledger_entry_id,
        audit_trace.audit_trace_id,
        rollback_reference.rollback_reference_id,
        decision.decision_id,
    )
    return ActionLedgerReportEntry(
        report_entry_id=report_entry_id,
        ledger_entry_id=entry.ledger_entry_id,
        audit_trace_id=audit_trace.audit_trace_id,
        rollback_reference_id=rollback_reference.rollback_reference_id,
        decision_id=decision.decision_id,
        ledger_summary=f"{entry.ledger_status.value}: {entry.action_summary}",
        audit_summary=audit_trace.trace_summary,
        rollback_summary=rollback_reference.rollback_strategy,
        decision_summary=f"{decision.outcome.value}: {decision.rationale}",
        unresolved_gaps=tuple(unresolved_gaps),
    )


def validate_action_ledger_entry_inactive(entry: ActionLedgerEntry) -> bool:
    return (
        entry.human_approval_present is False
        and not any(
            (
                entry.active,
                entry.persisted_to_active_ledger,
                entry.action_executed,
                entry.side_effects_created,
                entry.tool_called,
                entry.provider_called,
                entry.autonomous_approval_used,
                entry.memory_mutated,
                entry.runtime_recall_mutated,
                entry.training_triggered,
            )
        )
    )


def validate_action_ledger_plan_inert(plan: ActionLedgerPlan) -> bool:
    return (
        plan.required_before_execution
        and plan.append_only_required
        and plan.immutable_audit_required
        and plan.rollback_reference_required
        and not any(
            (
                plan.active_ledger_enabled,
                plan.ledger_persistence_enabled,
                plan.action_execution_enabled,
                plan.side_effects_enabled,
                plan.scheduler_enabled,
                plan.background_queue_enabled,
            )
        )
        and _invariant_flags_safe(plan.invariant_flags)
    )


def validate_action_audit_trace_review_only(trace: ActionAuditTrace) -> bool:
    return trace.generated_for_review_only and not any((trace.persisted_to_active_ledger, trace.applied))


def validate_action_rollback_reference_inert(reference: ActionRollbackReference) -> bool:
    return reference.rollback_requires_human_approval and not any(
        (reference.rollback_executed, reference.side_effect_reversal_executed)
    )


def validate_action_ledger_decision_inert(decision: ActionLedgerDecision) -> bool:
    return (
        not any((decision.applied, decision.ledger_written, decision.action_executed, decision.side_effects_created))
        and _invariant_flags_safe(decision.invariant_flags)
    )


def validate_action_ledger_report_entry_review_only(entry: ActionLedgerReportEntry) -> bool:
    return entry.generated_for_review_only


def _status_for_inputs(authorization_decision_id: str, human_approval_required: bool) -> ActionLedgerStatus:
    if not authorization_decision_id:
        return ActionLedgerStatus.BLOCKED_MISSING_AUTHORIZATION
    if human_approval_required:
        return ActionLedgerStatus.BLOCKED_MISSING_APPROVAL
    return ActionLedgerStatus.REVIEW_ONLY


def _invariant_flags_safe(flags: dict[str, bool]) -> bool:
    return (
        flags.get("human_approval_required_for_risky_actions") is True
        and flags.get("authorization_required_before_ledger") is True
        and flags.get("ledger_required_before_execution") is True
        and all(
            value is False
            for key, value in flags.items()
            if key
            not in {
                "human_approval_required_for_risky_actions",
                "authorization_required_before_ledger",
                "ledger_required_before_execution",
            }
        )
    )


def _invariants_drifted() -> bool:
    return not _invariant_flags_safe(RUNTIME_V14P_INVARIANT_FLAGS)


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
