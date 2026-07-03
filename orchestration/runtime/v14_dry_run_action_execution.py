from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14Q_INVARIANT_FLAGS: dict[str, bool] = {
    "dry_run_execution_enabled": False,
    "real_action_execution_enabled": False,
    "action_execution_enabled": False,
    "side_effects_enabled": False,
    "tool_calls_enabled": False,
    "provider_calls_enabled": False,
    "file_mutation_enabled": False,
    "network_enabled": False,
    "database_mutation_enabled": False,
    "active_ledger_enabled": False,
    "ledger_persistence_enabled": False,
    "autonomous_approval_enabled": False,
    "human_approval_required_for_risky_actions": True,
    "authorization_required_before_execution": True,
    "ledger_required_before_execution": True,
    "rollback_execution_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class DryRunActionKind(str, Enum):
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


class DryRunRequestedMode(str, Enum):
    REVIEW_ONLY = "review_only"
    SIMULATE_STEPS = "simulate_steps"
    SIMULATE_RESULT = "simulate_result"
    REJECT = "reject"


class DryRunSideEffectRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class DryRunSimulatedStatus(str, Enum):
    SIMULATED_SUCCESS = "simulated_success"
    SIMULATED_BLOCKED_MISSING_AUTHORIZATION = "simulated_blocked_missing_authorization"
    SIMULATED_BLOCKED_MISSING_LEDGER = "simulated_blocked_missing_ledger"
    SIMULATED_BLOCKED_BY_INVARIANT = "simulated_blocked_by_invariant"
    SIMULATED_REQUIRES_HUMAN_REVIEW = "simulated_requires_human_review"
    SIMULATED_REJECTED = "simulated_rejected"
    SIMULATED_DEFERRED = "simulated_deferred"


@dataclass(frozen=True)
class DryRunAction:
    dry_run_action_id: str
    action_intent_id: str
    action_kind: DryRunActionKind
    action_summary: str
    source_reference_ids: tuple[str, ...] = ()
    ledger_entry_id: str = ""
    authorization_decision_id: str = ""
    active: bool = False
    real_execution_enabled: bool = False
    tool_calls_enabled: bool = False
    provider_calls_enabled: bool = False
    side_effects_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "dry_run_action_id": self.dry_run_action_id,
            "action_intent_id": self.action_intent_id,
            "action_kind": self.action_kind.value,
            "action_summary": self.action_summary,
            "source_reference_ids": list(self.source_reference_ids),
            "ledger_entry_id": self.ledger_entry_id,
            "authorization_decision_id": self.authorization_decision_id,
            "active": self.active,
            "real_execution_enabled": self.real_execution_enabled,
            "tool_calls_enabled": self.tool_calls_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "side_effects_enabled": self.side_effects_enabled,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DryRunExecutionInput:
    dry_run_input_id: str
    dry_run_action_id: str
    authorization_decision_id: str = ""
    ledger_entry_id: str = ""
    requested_mode: DryRunRequestedMode = DryRunRequestedMode.REVIEW_ONLY
    preconditions: tuple[str, ...] = ()
    missing_requirements: tuple[str, ...] = ()
    source_reference_ids: tuple[str, ...] = ()
    simulation_only: bool = True
    real_execution_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "dry_run_input_id": self.dry_run_input_id,
            "dry_run_action_id": self.dry_run_action_id,
            "authorization_decision_id": self.authorization_decision_id,
            "ledger_entry_id": self.ledger_entry_id,
            "requested_mode": self.requested_mode.value,
            "preconditions": list(self.preconditions),
            "missing_requirements": list(self.missing_requirements),
            "source_reference_ids": list(self.source_reference_ids),
            "simulation_only": self.simulation_only,
            "real_execution_enabled": self.real_execution_enabled,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DryRunExecutionStep:
    step_id: str
    dry_run_input_id: str
    step_order: int
    step_summary: str
    would_touch_target: str = ""
    side_effect_risk: DryRunSideEffectRisk = DryRunSideEffectRisk.NONE
    simulated: bool = True
    executed: bool = False
    side_effects_created: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "dry_run_input_id": self.dry_run_input_id,
            "step_order": self.step_order,
            "step_summary": self.step_summary,
            "would_touch_target": self.would_touch_target,
            "side_effect_risk": self.side_effect_risk.value,
            "simulated": self.simulated,
            "executed": self.executed,
            "side_effects_created": self.side_effects_created,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DryRunExecutionResult:
    result_id: str
    dry_run_input_id: str
    step_ids: tuple[str, ...] = ()
    simulated_status: DryRunSimulatedStatus = DryRunSimulatedStatus.SIMULATED_DEFERRED
    simulated_output_summary: str = ""
    blocked_reason: str = ""
    requires_human_review: bool = True
    requires_ledger: bool = True
    requires_authorization: bool = True
    simulated: bool = True
    real_result: bool = False
    action_executed: bool = False
    side_effects_created: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "result_id": self.result_id,
            "dry_run_input_id": self.dry_run_input_id,
            "step_ids": list(self.step_ids),
            "simulated_status": self.simulated_status.value,
            "simulated_output_summary": self.simulated_output_summary,
            "blocked_reason": self.blocked_reason,
            "requires_human_review": self.requires_human_review,
            "requires_ledger": self.requires_ledger,
            "requires_authorization": self.requires_authorization,
            "simulated": self.simulated,
            "real_result": self.real_result,
            "action_executed": self.action_executed,
            "side_effects_created": self.side_effects_created,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionSideEffectBoundary:
    boundary_id: str
    dry_run_action_id: str
    prohibited_side_effects: tuple[str, ...] = ()
    allowed_simulation_scope: str = "describe hypothetical steps only"
    external_systems_blocked: tuple[str, ...] = ()
    file_mutation_enabled: bool = False
    network_enabled: bool = False
    database_mutation_enabled: bool = False
    tool_calls_enabled: bool = False
    provider_calls_enabled: bool = False
    side_effects_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "boundary_id": self.boundary_id,
            "dry_run_action_id": self.dry_run_action_id,
            "prohibited_side_effects": list(self.prohibited_side_effects),
            "allowed_simulation_scope": self.allowed_simulation_scope,
            "external_systems_blocked": list(self.external_systems_blocked),
            "file_mutation_enabled": self.file_mutation_enabled,
            "network_enabled": self.network_enabled,
            "database_mutation_enabled": self.database_mutation_enabled,
            "tool_calls_enabled": self.tool_calls_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "side_effects_enabled": self.side_effects_enabled,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DryRunExecutionTrace:
    trace_id: str
    dry_run_action_id: str
    dry_run_input_id: str
    result_id: str
    boundary_id: str
    step_ids: tuple[str, ...] = ()
    source_reference_ids: tuple[str, ...] = ()
    generated_for_review_only: bool = True
    applied: bool = False
    persisted_to_active_ledger: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "dry_run_action_id": self.dry_run_action_id,
            "dry_run_input_id": self.dry_run_input_id,
            "step_ids": list(self.step_ids),
            "result_id": self.result_id,
            "boundary_id": self.boundary_id,
            "source_reference_ids": list(self.source_reference_ids),
            "generated_for_review_only": self.generated_for_review_only,
            "applied": self.applied,
            "persisted_to_active_ledger": self.persisted_to_active_ledger,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DryRunRollbackPlan:
    rollback_plan_id: str
    dry_run_action_id: str
    result_id: str = ""
    rollback_strategy: str = "rollback cannot execute in dry-run design"
    rollback_required_for_real_execution: bool = True
    rollback_possible: bool = False
    rollback_executed: bool = False
    side_effect_reversal_executed: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "rollback_plan_id": self.rollback_plan_id,
            "dry_run_action_id": self.dry_run_action_id,
            "result_id": self.result_id,
            "rollback_strategy": self.rollback_strategy,
            "rollback_required_for_real_execution": self.rollback_required_for_real_execution,
            "rollback_possible": self.rollback_possible,
            "rollback_executed": self.rollback_executed,
            "side_effect_reversal_executed": self.side_effect_reversal_executed,
            "applied": self.applied,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DryRunExecutionReportEntry:
    report_entry_id: str
    trace_id: str
    action_summary: str
    input_summary: str
    step_summary: str
    result_summary: str
    boundary_summary: str
    rollback_summary: str
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = "design minimal runtime UI/message console"
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "trace_id": self.trace_id,
            "action_summary": self.action_summary,
            "input_summary": self.input_summary,
            "step_summary": self.step_summary,
            "result_summary": self.result_summary,
            "boundary_summary": self.boundary_summary,
            "rollback_summary": self.rollback_summary,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
        }


def create_dry_run_action(
    *,
    action_intent_id: str,
    action_kind: DryRunActionKind,
    action_summary: str,
    source_reference_ids: tuple[str, ...] = (),
    ledger_entry_id: str = "",
    authorization_decision_id: str = "",
) -> DryRunAction:
    dry_run_action_id = _stable_id(
        "dry-run-action",
        action_intent_id,
        action_kind.value,
        action_summary,
        ",".join(source_reference_ids),
        ledger_entry_id,
        authorization_decision_id,
    )
    return DryRunAction(
        dry_run_action_id=dry_run_action_id,
        action_intent_id=action_intent_id,
        action_kind=action_kind,
        action_summary=action_summary.strip(),
        source_reference_ids=tuple(source_reference_ids),
        ledger_entry_id=ledger_entry_id,
        authorization_decision_id=authorization_decision_id,
    )


def create_dry_run_execution_input(
    action: DryRunAction,
    *,
    requested_mode: DryRunRequestedMode = DryRunRequestedMode.REVIEW_ONLY,
    preconditions: tuple[str, ...] = (),
    missing_requirements: tuple[str, ...] = (),
) -> DryRunExecutionInput:
    requirements = list(missing_requirements)
    if not action.authorization_decision_id:
        requirements.append("authorization_decision")
    if not action.ledger_entry_id:
        requirements.append("ledger_entry")
    dry_run_input_id = _stable_id(
        "dry-run-input",
        action.dry_run_action_id,
        requested_mode.value,
        ",".join(preconditions),
        ",".join(requirements),
    )
    return DryRunExecutionInput(
        dry_run_input_id=dry_run_input_id,
        dry_run_action_id=action.dry_run_action_id,
        authorization_decision_id=action.authorization_decision_id,
        ledger_entry_id=action.ledger_entry_id,
        requested_mode=requested_mode,
        preconditions=tuple(preconditions),
        missing_requirements=tuple(dict.fromkeys(requirements)),
        source_reference_ids=action.source_reference_ids,
    )


def create_dry_run_execution_step(
    execution_input: DryRunExecutionInput,
    *,
    step_order: int,
    step_summary: str,
    would_touch_target: str = "",
    side_effect_risk: DryRunSideEffectRisk = DryRunSideEffectRisk.NONE,
) -> DryRunExecutionStep:
    step_id = _stable_id(
        "dry-run-step",
        execution_input.dry_run_input_id,
        step_order,
        step_summary,
        would_touch_target,
        side_effect_risk.value,
    )
    return DryRunExecutionStep(
        step_id=step_id,
        dry_run_input_id=execution_input.dry_run_input_id,
        step_order=step_order,
        step_summary=step_summary.strip(),
        would_touch_target=would_touch_target.strip(),
        side_effect_risk=side_effect_risk,
    )


def create_dry_run_execution_result(
    execution_input: DryRunExecutionInput,
    steps: tuple[DryRunExecutionStep, ...],
) -> DryRunExecutionResult:
    status, blocked_reason = _status_for_input(execution_input)
    result_id = _stable_id(
        "dry-run-result",
        execution_input.dry_run_input_id,
        ",".join(step.step_id for step in steps),
        status.value,
        blocked_reason,
    )
    return DryRunExecutionResult(
        result_id=result_id,
        dry_run_input_id=execution_input.dry_run_input_id,
        step_ids=tuple(step.step_id for step in steps),
        simulated_status=status,
        simulated_output_summary=_summary_for_status(status),
        blocked_reason=blocked_reason,
    )


def create_execution_side_effect_boundary(action: DryRunAction) -> ExecutionSideEffectBoundary:
    prohibited = (
        "file_mutation",
        "network_call",
        "database_mutation",
        "tool_call",
        "provider_call",
        "external_side_effect",
    )
    boundary_id = _stable_id("dry-run-boundary", action.dry_run_action_id, ",".join(prohibited))
    return ExecutionSideEffectBoundary(
        boundary_id=boundary_id,
        dry_run_action_id=action.dry_run_action_id,
        prohibited_side_effects=prohibited,
        external_systems_blocked=("filesystem", "network", "database", "tools", "providers"),
    )


def create_dry_run_execution_trace(
    *,
    action: DryRunAction,
    execution_input: DryRunExecutionInput,
    steps: tuple[DryRunExecutionStep, ...],
    result: DryRunExecutionResult,
    boundary: ExecutionSideEffectBoundary,
) -> DryRunExecutionTrace:
    trace_id = _stable_id(
        "dry-run-trace",
        action.dry_run_action_id,
        execution_input.dry_run_input_id,
        ",".join(step.step_id for step in steps),
        result.result_id,
        boundary.boundary_id,
    )
    return DryRunExecutionTrace(
        trace_id=trace_id,
        dry_run_action_id=action.dry_run_action_id,
        dry_run_input_id=execution_input.dry_run_input_id,
        step_ids=tuple(step.step_id for step in steps),
        result_id=result.result_id,
        boundary_id=boundary.boundary_id,
        source_reference_ids=action.source_reference_ids,
    )


def create_dry_run_rollback_plan(
    action: DryRunAction,
    *,
    result_id: str = "",
    rollback_strategy: str = "rollback cannot execute in dry-run design",
    rollback_possible: bool = False,
) -> DryRunRollbackPlan:
    rollback_plan_id = _stable_id(
        "dry-run-rollback-plan",
        action.dry_run_action_id,
        result_id,
        rollback_strategy,
        rollback_possible,
    )
    return DryRunRollbackPlan(
        rollback_plan_id=rollback_plan_id,
        dry_run_action_id=action.dry_run_action_id,
        result_id=result_id,
        rollback_strategy=rollback_strategy.strip(),
        rollback_possible=rollback_possible,
    )


def create_dry_run_execution_report_entry(
    *,
    action: DryRunAction,
    execution_input: DryRunExecutionInput,
    steps: tuple[DryRunExecutionStep, ...],
    result: DryRunExecutionResult,
    boundary: ExecutionSideEffectBoundary,
    trace: DryRunExecutionTrace,
    rollback_plan: DryRunRollbackPlan,
    unresolved_gaps: tuple[str, ...] = (),
) -> DryRunExecutionReportEntry:
    report_entry_id = _stable_id("dry-run-report-entry", trace.trace_id, rollback_plan.rollback_plan_id, result.result_id)
    return DryRunExecutionReportEntry(
        report_entry_id=report_entry_id,
        trace_id=trace.trace_id,
        action_summary=action.action_summary,
        input_summary=f"{execution_input.requested_mode.value}; missing={','.join(execution_input.missing_requirements)}",
        step_summary="; ".join(step.step_summary for step in steps),
        result_summary=f"{result.simulated_status.value}: {result.simulated_output_summary}",
        boundary_summary=f"blocked={','.join(boundary.external_systems_blocked)}",
        rollback_summary=rollback_plan.rollback_strategy,
        unresolved_gaps=tuple(unresolved_gaps),
    )


def validate_dry_run_action_inactive(action: DryRunAction) -> bool:
    return not any(
        (
            action.active,
            action.real_execution_enabled,
            action.tool_calls_enabled,
            action.provider_calls_enabled,
            action.side_effects_enabled,
        )
    )


def validate_dry_run_execution_input_simulation_only(execution_input: DryRunExecutionInput) -> bool:
    return execution_input.simulation_only and not execution_input.real_execution_enabled


def validate_dry_run_execution_step_simulated(step: DryRunExecutionStep) -> bool:
    return step.simulated and not any((step.executed, step.side_effects_created))


def validate_dry_run_execution_result_simulated(result: DryRunExecutionResult) -> bool:
    return result.simulated and not any((result.real_result, result.action_executed, result.side_effects_created))


def validate_execution_side_effect_boundary_blocks_effects(boundary: ExecutionSideEffectBoundary) -> bool:
    return not any(
        (
            boundary.file_mutation_enabled,
            boundary.network_enabled,
            boundary.database_mutation_enabled,
            boundary.tool_calls_enabled,
            boundary.provider_calls_enabled,
            boundary.side_effects_enabled,
        )
    )


def validate_dry_run_execution_trace_review_only(trace: DryRunExecutionTrace) -> bool:
    return trace.generated_for_review_only and not any((trace.applied, trace.persisted_to_active_ledger))


def validate_dry_run_rollback_plan_inert(plan: DryRunRollbackPlan) -> bool:
    return plan.rollback_required_for_real_execution and not any(
        (plan.rollback_executed, plan.side_effect_reversal_executed, plan.applied)
    )


def validate_dry_run_execution_report_entry_review_only(entry: DryRunExecutionReportEntry) -> bool:
    return entry.generated_for_review_only


def invariant_flags_safe(flags: dict[str, bool]) -> bool:
    required_true = {
        "human_approval_required_for_risky_actions",
        "authorization_required_before_execution",
        "ledger_required_before_execution",
    }
    return all(flags.get(key) is True for key in required_true) and all(
        value is False for key, value in flags.items() if key not in required_true
    )


def _status_for_input(execution_input: DryRunExecutionInput) -> tuple[DryRunSimulatedStatus, str]:
    if not invariant_flags_safe(RUNTIME_V14Q_INVARIANT_FLAGS):
        return DryRunSimulatedStatus.SIMULATED_BLOCKED_BY_INVARIANT, "invariant drift"
    if execution_input.requested_mode == DryRunRequestedMode.REJECT:
        return DryRunSimulatedStatus.SIMULATED_REJECTED, "requested rejection"
    if "authorization_decision" in execution_input.missing_requirements:
        return DryRunSimulatedStatus.SIMULATED_BLOCKED_MISSING_AUTHORIZATION, "missing authorization"
    if "ledger_entry" in execution_input.missing_requirements:
        return DryRunSimulatedStatus.SIMULATED_BLOCKED_MISSING_LEDGER, "missing ledger entry"
    return DryRunSimulatedStatus.SIMULATED_REQUIRES_HUMAN_REVIEW, "human review required before any future execution"


def _summary_for_status(status: DryRunSimulatedStatus) -> str:
    mapping = {
        DryRunSimulatedStatus.SIMULATED_SUCCESS: "hypothetical steps could complete, but no real result was produced",
        DryRunSimulatedStatus.SIMULATED_BLOCKED_MISSING_AUTHORIZATION: "simulation blocked by missing authorization",
        DryRunSimulatedStatus.SIMULATED_BLOCKED_MISSING_LEDGER: "simulation blocked by missing ledger entry",
        DryRunSimulatedStatus.SIMULATED_BLOCKED_BY_INVARIANT: "simulation blocked by invariant drift",
        DryRunSimulatedStatus.SIMULATED_REQUIRES_HUMAN_REVIEW: "simulation requires human review",
        DryRunSimulatedStatus.SIMULATED_REJECTED: "simulation rejected",
        DryRunSimulatedStatus.SIMULATED_DEFERRED: "simulation deferred",
    }
    return mapping[status]


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
