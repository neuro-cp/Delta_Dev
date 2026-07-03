from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V15B_INVARIANT_FLAGS: dict[str, bool] = {
    "selective_activation_enabled": False,
    "activation_applied": False,
    "integration_gate_opened": False,
    "runtime_console_preview_selected": True,
    "provider_calls_enabled": False,
    "memory_mutation_enabled": False,
    "canonical_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
    "specialist_routing_enabled": False,
    "action_execution_enabled": False,
    "training_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class SelectiveActivationTargetType(str, Enum):
    RUNTIME_CONSOLE_MESSAGE_PREVIEW = "runtime_console_message_preview"
    RAW_EXPERIENCE_ADAPTER_PREVIEW = "raw_experience_adapter_preview"
    STRUCTURAL_SEMANTIC_ADAPTER_PREVIEW = "structural_semantic_adapter_preview"
    HYB1_RUNTIME_VARIANT = "hyb1_runtime_variant"
    RECALL_BRIDGE = "recall_bridge"
    CANONICAL_MEMORY_STORE = "canonical_memory_store"
    ACTIVE_SPECIALIST_ROUTING = "active_specialist_routing"
    ACTION_EXECUTION = "action_execution"
    TRAINING_DATASET_EXPORT = "training_dataset_export"
    PROVIDER_CALLING = "provider_calling"


class SelectiveActivationPrerequisiteType(str, Enum):
    SAFETY_CLOSURE_REQUIRED = "safety_closure_required"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    MANUAL_ONLY_REQUIRED = "manual_only_required"
    BLOCKED_BY_DEFAULT = "blocked_by_default"


class SelectiveActivationRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class SelectiveActivationDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    PLAN_ONLY = "plan_only"
    SELECTED_FOR_SINGLE_GATE_DRY_RUN_DESIGN = "selected_for_single_gate_dry_run_design"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


@dataclass(frozen=True)
class SelectiveActivationTarget:
    target_id: str
    target_name: str
    target_type: SelectiveActivationTargetType
    source_phase: str
    risk_level: SelectiveActivationRiskLevel
    selected_for_first_trial: bool
    activation_allowed: bool = False
    gate_open: bool = False
    active: bool = False
    default_change_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SelectiveActivationPrerequisite:
    prerequisite_id: str
    target_id: str
    prerequisite_type: SelectiveActivationPrerequisiteType
    rationale: str
    satisfied: bool
    required_before_activation: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SelectiveActivationRiskReview:
    risk_review_id: str
    target_id: str
    risk_level: SelectiveActivationRiskLevel
    allowed_trial_scope: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    safe_for_first_trial: bool
    human_review_required: bool

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SelectiveActivationPlan:
    activation_plan_id: str
    selected_target_id: str
    allowed_components: tuple[str, ...]
    blocked_components: tuple[str, ...]
    manual_only: bool = True
    local_only: bool = True
    deterministic_only: bool = True
    provider_calls_allowed: bool = False
    memory_writes_allowed: bool = False
    action_execution_allowed: bool = False
    hyb1_default_allowed: bool = False
    activation_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SelectiveActivationDecision:
    decision_id: str
    selected_target_id: str
    outcome: SelectiveActivationDecisionOutcome
    rationale: str
    applied: bool = False
    gate_opened: bool = False
    activation_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SelectiveActivationAuditRecord:
    audit_id: str
    activation_plan_id: str
    decision_id: str
    audit_summary: str
    generated_for_review_only: bool = True
    activation_applied: bool = False
    gate_opened: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SelectiveActivationReportEntry:
    report_entry_id: str
    selected_target_id: str
    plan_summary: str
    risk_summary: str
    decision_summary: str
    blocked_capability_summary: str
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_selective_activation_target(
    *, target_name: str, target_type: SelectiveActivationTargetType, source_phase: str, risk_level: SelectiveActivationRiskLevel, selected: bool = False
) -> SelectiveActivationTarget:
    return SelectiveActivationTarget(
        target_id=_stable_id("selective-target", target_name, target_type.value, source_phase, risk_level.value, selected),
        target_name=target_name,
        target_type=target_type,
        source_phase=source_phase,
        risk_level=risk_level,
        selected_for_first_trial=selected,
    )


def create_selective_activation_targets() -> tuple[SelectiveActivationTarget, ...]:
    specs = (
        ("runtime_console_message_preview", SelectiveActivationTargetType.RUNTIME_CONSOLE_MESSAGE_PREVIEW, "V1.4 console", SelectiveActivationRiskLevel.LOW, True),
        ("raw_experience_adapter_preview", SelectiveActivationTargetType.RAW_EXPERIENCE_ADAPTER_PREVIEW, "V1.4M", SelectiveActivationRiskLevel.LOW, False),
        ("structural_semantic_adapter_preview", SelectiveActivationTargetType.STRUCTURAL_SEMANTIC_ADAPTER_PREVIEW, "V1.4L", SelectiveActivationRiskLevel.LOW, False),
        ("hyb1_runtime_variant", SelectiveActivationTargetType.HYB1_RUNTIME_VARIANT, "V1.4U/V", SelectiveActivationRiskLevel.MEDIUM, False),
        ("recall_bridge", SelectiveActivationTargetType.RECALL_BRIDGE, "V1.4K", SelectiveActivationRiskLevel.HIGH, False),
        ("canonical_memory_store", SelectiveActivationTargetType.CANONICAL_MEMORY_STORE, "V1.4F", SelectiveActivationRiskLevel.HIGH, False),
        ("active_specialist_routing", SelectiveActivationTargetType.ACTIVE_SPECIALIST_ROUTING, "V1.4N", SelectiveActivationRiskLevel.HIGH, False),
        ("action_execution", SelectiveActivationTargetType.ACTION_EXECUTION, "V1.4O/Q", SelectiveActivationRiskLevel.BLOCKED, False),
        ("training_dataset_export", SelectiveActivationTargetType.TRAINING_DATASET_EXPORT, "V1.4R", SelectiveActivationRiskLevel.BLOCKED, False),
        ("provider_calling", SelectiveActivationTargetType.PROVIDER_CALLING, "runtime", SelectiveActivationRiskLevel.BLOCKED, False),
    )
    return tuple(create_selective_activation_target(target_name=n, target_type=t, source_phase=p, risk_level=r, selected=s) for n, t, p, r, s in specs)


def create_selective_activation_prerequisite(target: SelectiveActivationTarget) -> SelectiveActivationPrerequisite:
    return SelectiveActivationPrerequisite(
        prerequisite_id=_stable_id("selective-prereq", target.target_id, "manual-only"),
        target_id=target.target_id,
        prerequisite_type=SelectiveActivationPrerequisiteType.MANUAL_ONLY_REQUIRED,
        rationale="first live path must remain manual/local/deterministic",
        satisfied=target.selected_for_first_trial,
    )


def create_selective_activation_risk_review(target: SelectiveActivationTarget) -> SelectiveActivationRiskReview:
    return SelectiveActivationRiskReview(
        risk_review_id=_stable_id("selective-risk", target.target_id, target.risk_level.value),
        target_id=target.target_id,
        risk_level=target.risk_level,
        allowed_trial_scope=("manual console preview",) if target.selected_for_first_trial else (),
        blocked_capabilities=("provider_calls", "memory_writes", "actions", "training", "schedulers"),
        unresolved_gaps=() if target.selected_for_first_trial else ("not selected for first trial",),
        safe_for_first_trial=target.selected_for_first_trial,
        human_review_required=not target.selected_for_first_trial,
    )


def create_selective_activation_plan(selected_target: SelectiveActivationTarget) -> SelectiveActivationPlan:
    return SelectiveActivationPlan(
        activation_plan_id=_stable_id("selective-plan", selected_target.target_id),
        selected_target_id=selected_target.target_id,
        allowed_components=("manual runtime console message preview", "raw experience preview", "semantic adapter preview", "trace/safety output", "deterministic local response preview"),
        blocked_components=("provider_calls", "memory_writes", "action_execution", "hyb1_default_activation", "training", "specialist_routing", "schedulers"),
    )


def create_selective_activation_decision(plan: SelectiveActivationPlan) -> SelectiveActivationDecision:
    return SelectiveActivationDecision(
        decision_id=_stable_id("selective-decision", plan.activation_plan_id),
        selected_target_id=plan.selected_target_id,
        outcome=SelectiveActivationDecisionOutcome.SELECTED_FOR_SINGLE_GATE_DRY_RUN_DESIGN,
        rationale="runtime console message preview is the only first-trial candidate and remains plan-only",
    )


def create_selective_activation_audit(plan: SelectiveActivationPlan, decision: SelectiveActivationDecision) -> SelectiveActivationAuditRecord:
    return SelectiveActivationAuditRecord(
        audit_id=_stable_id("selective-audit", plan.activation_plan_id, decision.decision_id),
        activation_plan_id=plan.activation_plan_id,
        decision_id=decision.decision_id,
        audit_summary="activation plan only; no gate opened",
    )


def create_selective_activation_report_entry(plan: SelectiveActivationPlan, decision: SelectiveActivationDecision) -> SelectiveActivationReportEntry:
    return SelectiveActivationReportEntry(
        report_entry_id=_stable_id("selective-entry", plan.activation_plan_id, decision.decision_id),
        selected_target_id=plan.selected_target_id,
        plan_summary="manual/local/deterministic runtime console preview selected",
        risk_summary="lowest-risk target; all mutating capabilities blocked",
        decision_summary=decision.outcome.value,
        blocked_capability_summary=", ".join(plan.blocked_components),
        recommended_next_review_step="single-gate dry-run trial design",
    )


def validate_selective_target_closed(target: SelectiveActivationTarget) -> bool:
    return not any((target.activation_allowed, target.gate_open, target.active, target.default_change_allowed))


def validate_selective_plan_inert(plan: SelectiveActivationPlan) -> bool:
    return plan.manual_only and plan.local_only and plan.deterministic_only and not any(
        (plan.provider_calls_allowed, plan.memory_writes_allowed, plan.action_execution_allowed, plan.hyb1_default_allowed, plan.activation_enabled)
    )


def validate_selective_decision_inert(decision: SelectiveActivationDecision) -> bool:
    return not any((decision.applied, decision.gate_opened, decision.activation_enabled))


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
