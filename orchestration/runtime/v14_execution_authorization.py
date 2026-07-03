from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14O_INVARIANT_FLAGS: dict[str, bool] = {
    "execution_authorization_enabled": False,
    "action_execution_enabled": False,
    "dry_run_execution_enabled": False,
    "side_effects_enabled": False,
    "tool_calls_enabled": False,
    "provider_calls_enabled": False,
    "autonomous_approval_enabled": False,
    "human_approval_required_for_risky_actions": True,
    "action_ledger_required_before_execution": True,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class ActionIntentKind(str, Enum):
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    DELETE_RECORD = "delete_record"
    SEND_MESSAGE = "send_message"
    CALL_TOOL = "call_tool"
    CALL_PROVIDER = "call_provider"
    FILE_OPERATION = "file_operation"
    NETWORK_OPERATION = "network_operation"
    DATABASE_OPERATION = "database_operation"
    UNKNOWN = "unknown"


class ExecutionRiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class RequestedExecutionMode(str, Enum):
    REJECT = "reject"
    REVIEW_ONLY = "review_only"
    DRY_RUN_ONLY = "dry_run_only"
    FUTURE_HUMAN_APPROVED_EXECUTION = "future_human_approved_execution"


class ExecutionApprovalType(str, Enum):
    NO_APPROVAL_NEEDED_FOR_REVIEW = "no_approval_needed_for_review"
    HUMAN_REQUIRED = "human_required"
    ADMIN_REQUIRED = "admin_required"
    BLOCKED_NO_APPROVAL_POSSIBLE = "blocked_no_approval_possible"


class ExecutionAuthorizationOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    REVIEW_ONLY = "review_only"
    DRY_RUN_ONLY = "dry_run_only"
    REQUIRES_HUMAN_APPROVAL = "requires_human_approval"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_ACTION_LEDGER_REVIEW = "eligible_for_future_action_ledger_review"


@dataclass(frozen=True)
class ActionIntent:
    intent_id: str
    intent_kind: ActionIntentKind
    description: str
    target_reference: str = ""
    requested_mode: RequestedExecutionMode = RequestedExecutionMode.REVIEW_ONLY
    lane_scope: tuple[str, ...] = ()
    source_trace_ids: tuple[str, ...] = ()
    active: bool = False
    executable: bool = False
    side_effects_allowed: bool = False
    tool_calls_allowed: bool = False
    provider_calls_allowed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "intent_id": self.intent_id,
            "intent_kind": self.intent_kind.value,
            "description": self.description,
            "target_reference": self.target_reference,
            "requested_mode": self.requested_mode.value,
            "lane_scope": list(self.lane_scope),
            "source_trace_ids": list(self.source_trace_ids),
            "active": self.active,
            "executable": self.executable,
            "side_effects_allowed": self.side_effects_allowed,
            "tool_calls_allowed": self.tool_calls_allowed,
            "provider_calls_allowed": self.provider_calls_allowed,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ExecutionRiskAssessment:
    assessment_id: str
    intent_id: str
    risk_level: ExecutionRiskLevel
    risk_factors: tuple[str, ...] = ()
    reversible: bool = False
    side_effect_potential: bool = False
    requires_action_ledger: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "intent_id": self.intent_id,
            "risk_level": self.risk_level.value,
            "risk_factors": list(self.risk_factors),
            "reversible": self.reversible,
            "side_effect_potential": self.side_effect_potential,
            "requires_action_ledger": self.requires_action_ledger,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionAuthorizationRequest:
    request_id: str
    intent_id: str
    assessment_id: str
    requested_mode: RequestedExecutionMode = RequestedExecutionMode.REVIEW_ONLY
    human_approval_present: bool = False
    autonomous_approval_allowed: bool = False
    action_ledger_reference: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "intent_id": self.intent_id,
            "assessment_id": self.assessment_id,
            "requested_mode": self.requested_mode.value,
            "human_approval_present": self.human_approval_present,
            "autonomous_approval_allowed": self.autonomous_approval_allowed,
            "action_ledger_reference": self.action_ledger_reference,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionApprovalRequirement:
    requirement_id: str
    request_id: str
    approval_type: ExecutionApprovalType
    rationale: str
    satisfied: bool = False
    human_approval_required: bool = True
    admin_approval_required: bool = False
    action_ledger_required: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "request_id": self.request_id,
            "approval_type": self.approval_type.value,
            "rationale": self.rationale,
            "satisfied": self.satisfied,
            "human_approval_required": self.human_approval_required,
            "admin_approval_required": self.admin_approval_required,
            "action_ledger_required": self.action_ledger_required,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionAuthorizationDecision:
    decision_id: str
    request_id: str
    requirement_id: str
    outcome: ExecutionAuthorizationOutcome
    rationale: str
    applied: bool = False
    execution_authorized: bool = False
    action_executed: bool = False
    dry_run_executed: bool = False
    side_effects_performed: bool = False
    tool_called: bool = False
    provider_called: bool = False
    memory_mutated: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14O_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "requirement_id": self.requirement_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "applied": self.applied,
            "execution_authorized": self.execution_authorized,
            "action_executed": self.action_executed,
            "dry_run_executed": self.dry_run_executed,
            "side_effects_performed": self.side_effects_performed,
            "tool_called": self.tool_called,
            "provider_called": self.provider_called,
            "memory_mutated": self.memory_mutated,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionDryRunPlan:
    dry_run_plan_id: str
    intent_id: str
    decision_id: str
    planned_steps: tuple[str, ...] = ()
    dry_run_enabled: bool = False
    real_execution_enabled: bool = False
    side_effects_enabled: bool = False
    requires_action_ledger: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "dry_run_plan_id": self.dry_run_plan_id,
            "intent_id": self.intent_id,
            "decision_id": self.decision_id,
            "planned_steps": list(self.planned_steps),
            "dry_run_enabled": self.dry_run_enabled,
            "real_execution_enabled": self.real_execution_enabled,
            "side_effects_enabled": self.side_effects_enabled,
            "requires_action_ledger": self.requires_action_ledger,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionAuthorizationTrace:
    trace_id: str
    intent_id: str
    assessment_id: str
    request_id: str
    requirement_id: str
    decision_id: str
    dry_run_plan_id: str
    generated_for_review_only: bool = True
    applied: bool = False
    execution_authorized: bool = False
    action_executed: bool = False
    side_effects_performed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "intent_id": self.intent_id,
            "assessment_id": self.assessment_id,
            "request_id": self.request_id,
            "requirement_id": self.requirement_id,
            "decision_id": self.decision_id,
            "dry_run_plan_id": self.dry_run_plan_id,
            "generated_for_review_only": self.generated_for_review_only,
            "applied": self.applied,
            "execution_authorized": self.execution_authorized,
            "action_executed": self.action_executed,
            "side_effects_performed": self.side_effects_performed,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionAuthorizationReportEntry:
    report_entry_id: str
    trace_id: str
    intent_summary: str
    risk_summary: str
    approval_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = "design action ledger before execution can be considered"
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "trace_id": self.trace_id,
            "intent_summary": self.intent_summary,
            "risk_summary": self.risk_summary,
            "approval_summary": self.approval_summary,
            "decision_summary": self.decision_summary,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
        }


def create_action_intent(
    *,
    intent_kind: ActionIntentKind,
    description: str,
    target_reference: str = "",
    requested_mode: RequestedExecutionMode = RequestedExecutionMode.REVIEW_ONLY,
    lane_scope: tuple[str, ...] = (),
    source_trace_ids: tuple[str, ...] = (),
    notes: str = "",
) -> ActionIntent:
    intent_id = _stable_id(
        "action-intent",
        intent_kind.value,
        description,
        target_reference,
        requested_mode.value,
        ",".join(lane_scope),
        ",".join(source_trace_ids),
    )
    return ActionIntent(
        intent_id=intent_id,
        intent_kind=intent_kind,
        description=description.strip(),
        target_reference=target_reference.strip(),
        requested_mode=requested_mode,
        lane_scope=tuple(lane_scope),
        source_trace_ids=tuple(source_trace_ids),
        notes=notes,
    )


def assess_execution_risk(intent: ActionIntent) -> ExecutionRiskAssessment:
    risk_level = _risk_for_intent(intent.intent_kind)
    risk_factors = _risk_factors_for_intent(intent.intent_kind)
    assessment_id = _stable_id("execution-risk-assessment", intent.intent_id, risk_level.value, ",".join(risk_factors))
    return ExecutionRiskAssessment(
        assessment_id=assessment_id,
        intent_id=intent.intent_id,
        risk_level=risk_level,
        risk_factors=risk_factors,
        reversible=risk_level in {ExecutionRiskLevel.NONE, ExecutionRiskLevel.LOW},
        side_effect_potential=risk_level in {ExecutionRiskLevel.MEDIUM, ExecutionRiskLevel.HIGH, ExecutionRiskLevel.BLOCKED},
    )


def create_execution_authorization_request(
    intent: ActionIntent,
    assessment: ExecutionRiskAssessment,
    *,
    action_ledger_reference: str = "",
) -> ExecutionAuthorizationRequest:
    request_id = _stable_id(
        "execution-authorization-request",
        intent.intent_id,
        assessment.assessment_id,
        intent.requested_mode.value,
        action_ledger_reference,
    )
    return ExecutionAuthorizationRequest(
        request_id=request_id,
        intent_id=intent.intent_id,
        assessment_id=assessment.assessment_id,
        requested_mode=intent.requested_mode,
        action_ledger_reference=action_ledger_reference,
    )


def create_execution_approval_requirement(
    request: ExecutionAuthorizationRequest,
    assessment: ExecutionRiskAssessment,
) -> ExecutionApprovalRequirement:
    approval_type = _approval_for_risk(assessment.risk_level)
    requirement_id = _stable_id("execution-approval-requirement", request.request_id, approval_type.value, assessment.risk_level.value)
    return ExecutionApprovalRequirement(
        requirement_id=requirement_id,
        request_id=request.request_id,
        approval_type=approval_type,
        rationale=_approval_rationale(approval_type, assessment),
        human_approval_required=approval_type in {ExecutionApprovalType.HUMAN_REQUIRED, ExecutionApprovalType.ADMIN_REQUIRED},
        admin_approval_required=approval_type == ExecutionApprovalType.ADMIN_REQUIRED,
    )


def decide_execution_authorization(
    request: ExecutionAuthorizationRequest,
    requirement: ExecutionApprovalRequirement,
) -> ExecutionAuthorizationDecision:
    if _bool_invariants_drifted():
        outcome = ExecutionAuthorizationOutcome.BLOCKED_BY_INVARIANT
        rationale = "runtime invariant flags are not in the scaffold baseline state"
    elif request.requested_mode == RequestedExecutionMode.REJECT:
        outcome = ExecutionAuthorizationOutcome.REJECT
        rationale = "intent requested rejection"
    elif request.requested_mode == RequestedExecutionMode.REVIEW_ONLY:
        outcome = ExecutionAuthorizationOutcome.REVIEW_ONLY
        rationale = "review-only authorization record; no execution may occur"
    elif request.requested_mode == RequestedExecutionMode.DRY_RUN_ONLY:
        outcome = ExecutionAuthorizationOutcome.DRY_RUN_ONLY
        rationale = "dry-run execution is designed but disabled"
    elif requirement.satisfied and request.human_approval_present and request.action_ledger_reference:
        outcome = ExecutionAuthorizationOutcome.ELIGIBLE_FOR_FUTURE_ACTION_LEDGER_REVIEW
        rationale = "future execution would still require action ledger review"
    else:
        outcome = ExecutionAuthorizationOutcome.REQUIRES_HUMAN_APPROVAL
        rationale = "execution requires explicit human approval and action ledger support"
    decision_id = _stable_id("execution-authorization-decision", request.request_id, requirement.requirement_id, outcome.value)
    return ExecutionAuthorizationDecision(
        decision_id=decision_id,
        request_id=request.request_id,
        requirement_id=requirement.requirement_id,
        outcome=outcome,
        rationale=rationale,
    )


def create_execution_dry_run_plan(
    intent: ActionIntent,
    decision: ExecutionAuthorizationDecision,
    *,
    planned_steps: tuple[str, ...] = (),
) -> ExecutionDryRunPlan:
    dry_run_plan_id = _stable_id("execution-dry-run-plan", intent.intent_id, decision.decision_id, ",".join(planned_steps))
    return ExecutionDryRunPlan(
        dry_run_plan_id=dry_run_plan_id,
        intent_id=intent.intent_id,
        decision_id=decision.decision_id,
        planned_steps=tuple(planned_steps),
    )


def create_execution_authorization_trace(
    *,
    intent: ActionIntent,
    assessment: ExecutionRiskAssessment,
    request: ExecutionAuthorizationRequest,
    requirement: ExecutionApprovalRequirement,
    decision: ExecutionAuthorizationDecision,
    dry_run_plan: ExecutionDryRunPlan,
) -> ExecutionAuthorizationTrace:
    trace_id = _stable_id(
        "execution-authorization-trace",
        intent.intent_id,
        assessment.assessment_id,
        request.request_id,
        requirement.requirement_id,
        decision.decision_id,
        dry_run_plan.dry_run_plan_id,
    )
    return ExecutionAuthorizationTrace(
        trace_id=trace_id,
        intent_id=intent.intent_id,
        assessment_id=assessment.assessment_id,
        request_id=request.request_id,
        requirement_id=requirement.requirement_id,
        decision_id=decision.decision_id,
        dry_run_plan_id=dry_run_plan.dry_run_plan_id,
    )


def create_execution_authorization_report_entry(
    *,
    trace: ExecutionAuthorizationTrace,
    intent: ActionIntent,
    assessment: ExecutionRiskAssessment,
    requirement: ExecutionApprovalRequirement,
    decision: ExecutionAuthorizationDecision,
    unresolved_gaps: tuple[str, ...] = (),
) -> ExecutionAuthorizationReportEntry:
    report_entry_id = _stable_id("execution-authorization-report-entry", trace.trace_id, decision.decision_id)
    return ExecutionAuthorizationReportEntry(
        report_entry_id=report_entry_id,
        trace_id=trace.trace_id,
        intent_summary=f"{intent.intent_kind.value}: {intent.description}",
        risk_summary=f"{assessment.risk_level.value}: {', '.join(assessment.risk_factors)}",
        approval_summary=f"{requirement.approval_type.value}: {requirement.rationale}",
        decision_summary=f"{decision.outcome.value}: {decision.rationale}",
        unresolved_gaps=tuple(unresolved_gaps),
    )


def validate_action_intent_inert(intent: ActionIntent) -> bool:
    return not any(
        (
            intent.active,
            intent.executable,
            intent.side_effects_allowed,
            intent.tool_calls_allowed,
            intent.provider_calls_allowed,
        )
    )


def validate_execution_risk_assessment_review_only(assessment: ExecutionRiskAssessment) -> bool:
    return assessment.requires_action_ledger


def validate_execution_authorization_request_inert(request: ExecutionAuthorizationRequest) -> bool:
    return not any((request.human_approval_present, request.autonomous_approval_allowed))


def validate_execution_approval_requirement_unsatisfied(requirement: ExecutionApprovalRequirement) -> bool:
    return requirement.action_ledger_required and not requirement.satisfied


def validate_execution_authorization_decision_inert(decision: ExecutionAuthorizationDecision) -> bool:
    return (
        not any(
            (
                decision.applied,
                decision.execution_authorized,
                decision.action_executed,
                decision.dry_run_executed,
                decision.side_effects_performed,
                decision.tool_called,
                decision.provider_called,
                decision.memory_mutated,
            )
        )
        and decision.invariant_flags["human_approval_required_for_risky_actions"] is True
        and decision.invariant_flags["action_ledger_required_before_execution"] is True
        and all(
            value is False
            for key, value in decision.invariant_flags.items()
            if key not in {"human_approval_required_for_risky_actions", "action_ledger_required_before_execution"}
        )
    )


def validate_execution_dry_run_plan_inert(plan: ExecutionDryRunPlan) -> bool:
    return plan.requires_action_ledger and not any((plan.dry_run_enabled, plan.real_execution_enabled, plan.side_effects_enabled))


def validate_execution_trace_review_only(trace: ExecutionAuthorizationTrace) -> bool:
    return trace.generated_for_review_only and not any(
        (trace.applied, trace.execution_authorized, trace.action_executed, trace.side_effects_performed)
    )


def validate_execution_report_entry_review_only(entry: ExecutionAuthorizationReportEntry) -> bool:
    return entry.generated_for_review_only


def _risk_for_intent(intent_kind: ActionIntentKind) -> ExecutionRiskLevel:
    if intent_kind in {ActionIntentKind.UNKNOWN, ActionIntentKind.DELETE_RECORD}:
        return ExecutionRiskLevel.BLOCKED
    if intent_kind in {
        ActionIntentKind.CALL_TOOL,
        ActionIntentKind.CALL_PROVIDER,
        ActionIntentKind.FILE_OPERATION,
        ActionIntentKind.NETWORK_OPERATION,
        ActionIntentKind.DATABASE_OPERATION,
    }:
        return ExecutionRiskLevel.HIGH
    if intent_kind in {ActionIntentKind.CREATE_RECORD, ActionIntentKind.UPDATE_RECORD, ActionIntentKind.SEND_MESSAGE}:
        return ExecutionRiskLevel.MEDIUM
    return ExecutionRiskLevel.LOW


def _risk_factors_for_intent(intent_kind: ActionIntentKind) -> tuple[str, ...]:
    mapping = {
        ActionIntentKind.CREATE_RECORD: ("memory_or_store_write_possible",),
        ActionIntentKind.UPDATE_RECORD: ("mutation_possible",),
        ActionIntentKind.DELETE_RECORD: ("destructive_mutation", "rollback_required"),
        ActionIntentKind.SEND_MESSAGE: ("external_visibility",),
        ActionIntentKind.CALL_TOOL: ("tool_side_effects",),
        ActionIntentKind.CALL_PROVIDER: ("provider_call", "network_use"),
        ActionIntentKind.FILE_OPERATION: ("filesystem_side_effects",),
        ActionIntentKind.NETWORK_OPERATION: ("network_side_effects",),
        ActionIntentKind.DATABASE_OPERATION: ("database_side_effects",),
        ActionIntentKind.UNKNOWN: ("unknown_action_shape",),
    }
    return mapping[intent_kind]


def _approval_for_risk(risk_level: ExecutionRiskLevel) -> ExecutionApprovalType:
    if risk_level == ExecutionRiskLevel.NONE:
        return ExecutionApprovalType.NO_APPROVAL_NEEDED_FOR_REVIEW
    if risk_level in {ExecutionRiskLevel.LOW, ExecutionRiskLevel.MEDIUM}:
        return ExecutionApprovalType.HUMAN_REQUIRED
    if risk_level == ExecutionRiskLevel.HIGH:
        return ExecutionApprovalType.ADMIN_REQUIRED
    return ExecutionApprovalType.BLOCKED_NO_APPROVAL_POSSIBLE


def _approval_rationale(approval_type: ExecutionApprovalType, assessment: ExecutionRiskAssessment) -> str:
    if approval_type == ExecutionApprovalType.NO_APPROVAL_NEEDED_FOR_REVIEW:
        return "review-only assessment has no execution path"
    if approval_type == ExecutionApprovalType.HUMAN_REQUIRED:
        return "human approval would be required before any future action"
    if approval_type == ExecutionApprovalType.ADMIN_REQUIRED:
        return "high-risk side effects would require elevated approval"
    return f"blocked risk level: {assessment.risk_level.value}"


def _bool_invariants_drifted() -> bool:
    return any(
        value is True
        for key, value in RUNTIME_V14O_INVARIANT_FLAGS.items()
        if key not in {"human_approval_required_for_risky_actions", "action_ledger_required_before_execution"}
    ) or not all(
        RUNTIME_V14O_INVARIANT_FLAGS[key] is True
        for key in {"human_approval_required_for_risky_actions", "action_ledger_required_before_execution"}
    )


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
