from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V15A_INVARIANT_FLAGS: dict[str, bool] = {
    "v15_integration_enabled": False,
    "integration_gates_open": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
    "recall_bridge_active": False,
    "canonical_memory_active": False,
    "training_enabled": False,
    "training_dataset_export_enabled": False,
    "provider_calls_enabled": False,
    "specialist_routing_enabled": False,
    "action_execution_enabled": False,
    "dry_run_execution_active": False,
    "tool_calls_enabled": False,
    "canonical_write_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class IntegrationTargetType(str, Enum):
    HYB1_RUNTIME_VARIANT = "hyb1_runtime_variant"
    RECALL_BRIDGE = "recall_bridge"
    CANONICAL_MEMORY_STORE = "canonical_memory_store"
    STRUCTURAL_SEMANTIC_ADAPTER = "structural_semantic_adapter"
    RAW_EXPERIENCE_ADAPTER = "raw_experience_adapter"
    ACTIVE_SPECIALIST_ROUTING = "active_specialist_routing"
    EXECUTION_AUTHORIZATION = "execution_authorization"
    ACTION_LEDGER = "action_ledger"
    DRY_RUN_ACTION_EXECUTION = "dry_run_action_execution"
    TRAINING_DATASET_EXPORT = "training_dataset_export"
    OFFLINE_EVALUATION_HARNESS = "offline_evaluation_harness"
    TINY_TRAINING_EXPERIMENT = "tiny_training_experiment"


class IntegrationPrerequisiteType(str, Enum):
    SAFETY_CLOSURE_REQUIRED = "safety_closure_required"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    ROLLBACK_PLAN_REQUIRED = "rollback_plan_required"
    BASELINE_COMPARISON_REQUIRED = "baseline_comparison_required"
    EVALUATION_REQUIRED = "evaluation_required"
    INVARIANT_REVIEW_REQUIRED = "invariant_review_required"
    BLOCKED_BY_DEFAULT = "blocked_by_default"


class IntegrationGateStatus(str, Enum):
    CLOSED_BY_DEFAULT = "closed_by_default"
    MISSING_PREREQUISITES = "missing_prerequisites"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    ROLLBACK_REQUIRED = "rollback_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_TRIAL_DESIGN = "eligible_for_future_trial_design"


class IntegrationRequestedMode(str, Enum):
    INSPECT_ONLY = "inspect_only"
    FUTURE_TRIAL_DESIGN = "future_trial_design"
    DRY_RUN_REVIEW = "dry_run_review"
    REJECT = "reject"


class IntegrationGateDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    KEEP_CLOSED = "keep_closed"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REQUIRES_ROLLBACK_PLAN = "requires_rollback_plan"
    REQUIRES_SAFETY_CLOSURE = "requires_safety_closure"
    ELIGIBLE_FOR_FUTURE_TRIAL_DESIGN = "eligible_for_future_trial_design"


@dataclass(frozen=True)
class IntegrationGateTarget:
    target_id: str
    target_name: str
    target_type: IntegrationTargetType
    source_phase: str
    target_summary: str
    integration_allowed: bool = False
    gate_open: bool = False
    active: bool = False
    default_change_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class IntegrationPrerequisite:
    prerequisite_id: str
    target_id: str
    prerequisite_type: IntegrationPrerequisiteType
    rationale: str
    required_reference_id: str = ""
    satisfied: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class IntegrationSafetyGate:
    safety_gate_id: str
    target_id: str
    invariant_requirements: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]
    gate_status: IntegrationGateStatus
    gate_open: bool = False
    activation_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class IntegrationActivationRequest:
    request_id: str
    target_id: str
    requested_mode: IntegrationRequestedMode
    requester_summary: str
    justification: str
    human_approval_present: bool = False
    dry_run_only: bool = True
    activation_requested: bool = False
    activation_applied: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class IntegrationGateDecision:
    decision_id: str
    target_id: str
    outcome: IntegrationGateDecisionOutcome
    rationale: str
    request_id: str = ""
    applied: bool = False
    gate_opened: bool = False
    activation_enabled: bool = False
    default_changed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class IntegrationRollbackRequirement:
    rollback_requirement_id: str
    target_id: str
    rollback_strategy: str
    required_before_activation: bool = True
    rollback_ready: bool = False
    rollback_executed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class IntegrationGateAuditRecord:
    audit_id: str
    target_id: str
    prerequisite_ids: tuple[str, ...]
    audit_summary: str
    decision_id: str = ""
    safety_gate_id: str = ""
    generated_for_review_only: bool = True
    gate_opened: bool = False
    activation_enabled: bool = False
    default_changed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class IntegrationGateReportEntry:
    report_entry_id: str
    target_id: str
    prerequisite_summary: str
    safety_summary: str
    activation_request_summary: str
    decision_summary: str
    rollback_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_integration_gate_target(
    *, target_name: str, target_type: IntegrationTargetType, source_phase: str, target_summary: str
) -> IntegrationGateTarget:
    return IntegrationGateTarget(
        target_id=_stable_id("integration-target", target_name, target_type.value, source_phase, target_summary),
        target_name=target_name,
        target_type=target_type,
        source_phase=source_phase,
        target_summary=target_summary,
    )


def create_integration_prerequisite(
    *, target: IntegrationGateTarget, prerequisite_type: IntegrationPrerequisiteType, rationale: str, required_reference_id: str = ""
) -> IntegrationPrerequisite:
    return IntegrationPrerequisite(
        prerequisite_id=_stable_id("integration-prerequisite", target.target_id, prerequisite_type.value, rationale, required_reference_id),
        target_id=target.target_id,
        prerequisite_type=prerequisite_type,
        rationale=rationale,
        required_reference_id=required_reference_id,
    )


def create_integration_safety_gate(
    *,
    target: IntegrationGateTarget,
    invariant_requirements: tuple[str, ...],
    unresolved_gaps: tuple[str, ...],
    blocked_capabilities: tuple[str, ...],
    gate_status: IntegrationGateStatus = IntegrationGateStatus.CLOSED_BY_DEFAULT,
) -> IntegrationSafetyGate:
    return IntegrationSafetyGate(
        safety_gate_id=_stable_id("integration-safety-gate", target.target_id, invariant_requirements, unresolved_gaps, blocked_capabilities, gate_status.value),
        target_id=target.target_id,
        invariant_requirements=tuple(invariant_requirements),
        unresolved_gaps=tuple(unresolved_gaps),
        blocked_capabilities=tuple(blocked_capabilities),
        gate_status=gate_status,
    )


def create_integration_activation_request(
    *, target: IntegrationGateTarget, requested_mode: IntegrationRequestedMode, requester_summary: str, justification: str
) -> IntegrationActivationRequest:
    return IntegrationActivationRequest(
        request_id=_stable_id("integration-request", target.target_id, requested_mode.value, requester_summary, justification),
        target_id=target.target_id,
        requested_mode=requested_mode,
        requester_summary=requester_summary,
        justification=justification,
    )


def create_integration_gate_decision(
    *, target: IntegrationGateTarget, outcome: IntegrationGateDecisionOutcome, rationale: str, request: IntegrationActivationRequest | None = None
) -> IntegrationGateDecision:
    return IntegrationGateDecision(
        decision_id=_stable_id("integration-decision", target.target_id, outcome.value, rationale, request.request_id if request else ""),
        target_id=target.target_id,
        outcome=outcome,
        rationale=rationale,
        request_id=request.request_id if request else "",
    )


def create_integration_rollback_requirement(*, target: IntegrationGateTarget, rollback_strategy: str) -> IntegrationRollbackRequirement:
    return IntegrationRollbackRequirement(
        rollback_requirement_id=_stable_id("integration-rollback", target.target_id, rollback_strategy),
        target_id=target.target_id,
        rollback_strategy=rollback_strategy,
    )


def create_integration_gate_audit_record(
    *,
    target: IntegrationGateTarget,
    prerequisite_ids: tuple[str, ...],
    audit_summary: str,
    decision: IntegrationGateDecision | None = None,
    safety_gate: IntegrationSafetyGate | None = None,
) -> IntegrationGateAuditRecord:
    return IntegrationGateAuditRecord(
        audit_id=_stable_id(
            "integration-audit",
            target.target_id,
            prerequisite_ids,
            audit_summary,
            decision.decision_id if decision else "",
            safety_gate.safety_gate_id if safety_gate else "",
        ),
        target_id=target.target_id,
        prerequisite_ids=tuple(prerequisite_ids),
        audit_summary=audit_summary,
        decision_id=decision.decision_id if decision else "",
        safety_gate_id=safety_gate.safety_gate_id if safety_gate else "",
    )


def create_integration_gate_report_entry(
    *,
    target: IntegrationGateTarget,
    prerequisite_summary: str,
    safety_summary: str,
    activation_request_summary: str,
    decision_summary: str,
    rollback_summary: str,
    unresolved_gaps: tuple[str, ...],
    recommended_next_review_step: str,
) -> IntegrationGateReportEntry:
    return IntegrationGateReportEntry(
        report_entry_id=_stable_id(
            "integration-report-entry",
            target.target_id,
            prerequisite_summary,
            safety_summary,
            activation_request_summary,
            decision_summary,
            rollback_summary,
            unresolved_gaps,
            recommended_next_review_step,
        ),
        target_id=target.target_id,
        prerequisite_summary=prerequisite_summary,
        safety_summary=safety_summary,
        activation_request_summary=activation_request_summary,
        decision_summary=decision_summary,
        rollback_summary=rollback_summary,
        unresolved_gaps=tuple(unresolved_gaps),
        recommended_next_review_step=recommended_next_review_step,
    )


def create_closed_integration_targets() -> tuple[IntegrationGateTarget, ...]:
    specs = (
        ("HYB1 runtime variant", IntegrationTargetType.HYB1_RUNTIME_VARIANT, "V1.4U/V1.4V"),
        ("recall bridge", IntegrationTargetType.RECALL_BRIDGE, "V1.4K"),
        ("canonical memory store", IntegrationTargetType.CANONICAL_MEMORY_STORE, "V1.4F"),
        ("structural semantic adapter", IntegrationTargetType.STRUCTURAL_SEMANTIC_ADAPTER, "V1.4L"),
        ("raw experience adapter", IntegrationTargetType.RAW_EXPERIENCE_ADAPTER, "V1.4M"),
        ("active specialist routing", IntegrationTargetType.ACTIVE_SPECIALIST_ROUTING, "V1.4N"),
        ("execution authorization", IntegrationTargetType.EXECUTION_AUTHORIZATION, "V1.4O"),
        ("action ledger", IntegrationTargetType.ACTION_LEDGER, "V1.4P"),
        ("dry-run action execution", IntegrationTargetType.DRY_RUN_ACTION_EXECUTION, "V1.4Q"),
        ("training dataset export", IntegrationTargetType.TRAINING_DATASET_EXPORT, "V1.4R"),
        ("offline evaluation harness", IntegrationTargetType.OFFLINE_EVALUATION_HARNESS, "V1.4S"),
        ("tiny training experiment", IntegrationTargetType.TINY_TRAINING_EXPERIMENT, "V1.4T"),
    )
    return tuple(create_integration_gate_target(target_name=name, target_type=target_type, source_phase=phase, target_summary="closed by default") for name, target_type, phase in specs)


def validate_integration_target_closed(target: IntegrationGateTarget) -> bool:
    return not any((target.integration_allowed, target.gate_open, target.active, target.default_change_allowed))


def validate_prerequisite_unsatisfied(prerequisite: IntegrationPrerequisite) -> bool:
    return prerequisite.satisfied is False


def validate_safety_gate_closed(gate: IntegrationSafetyGate) -> bool:
    return not any((gate.gate_open, gate.activation_allowed))


def validate_activation_request_inert(request: IntegrationActivationRequest) -> bool:
    return request.dry_run_only and not any((request.human_approval_present, request.activation_requested, request.activation_applied))


def validate_gate_decision_closed(decision: IntegrationGateDecision) -> bool:
    return not any((decision.applied, decision.gate_opened, decision.activation_enabled, decision.default_changed))


def validate_rollback_requirement_inert(requirement: IntegrationRollbackRequirement) -> bool:
    return requirement.required_before_activation and not any((requirement.rollback_ready, requirement.rollback_executed))


def validate_audit_record_review_only(audit: IntegrationGateAuditRecord) -> bool:
    return audit.generated_for_review_only and not any((audit.gate_opened, audit.activation_enabled, audit.default_changed))


def validate_report_entry_review_only(entry: IntegrationGateReportEntry) -> bool:
    return entry.generated_for_review_only


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
    normalized = "|".join(_normalize_part(part) for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
