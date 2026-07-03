from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


STARTER_DELTA_QUESTION = "What is DELTA's current replay and consolidation path?"

RUNTIME_V15C_INVARIANT_FLAGS: dict[str, bool] = {
    "single_gate_trial_enabled": False,
    "gate_opened": False,
    "trial_executed": False,
    "runtime_console_live_path_enabled": False,
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


class SingleGateTrialTargetType(str, Enum):
    RUNTIME_CONSOLE_MESSAGE_PREVIEW = "runtime_console_message_preview"


class SingleGateTrialDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    DESIGN_ONLY = "design_only"
    ELIGIBLE_FOR_FIRST_LIVE_CONSOLE_PATH = "eligible_for_first_live_console_path"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


@dataclass(frozen=True)
class SingleGateTrialTarget:
    trial_target_id: str
    target_name: str = "runtime_console_message_preview"
    target_type: SingleGateTrialTargetType = SingleGateTrialTargetType.RUNTIME_CONSOLE_MESSAGE_PREVIEW
    source_activation_plan_id: str = ""
    gate_open: bool = False
    active: bool = False
    trial_execution_enabled: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SingleGateTrialScope:
    scope_id: str
    trial_target_id: str
    allowed_path: tuple[str, ...]
    blocked_path: tuple[str, ...]
    manual_only: bool = True
    local_only: bool = True
    deterministic_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SingleGateTrialInputCase:
    input_case_id: str
    trial_target_id: str
    message: str
    expected_intent_summary: str
    expected_review_only_status: str
    expected_disabled_flags: tuple[str, ...]
    training_example: bool = False
    memory_candidate: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SingleGateTrialExpectedTrace:
    expected_trace_id: str
    input_case_id: str
    expected_experience_record: bool = True
    expected_semantic_preview: bool = True
    expected_safety_status: bool = True
    expected_response_preview: bool = True
    expected_memory_write: bool = False
    expected_provider_call: bool = False
    expected_action_execution: bool = False
    expected_training: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SingleGateTrialSafetyBoundary:
    boundary_id: str
    trial_target_id: str
    provider_calls_enabled: bool = False
    memory_mutation_enabled: bool = False
    canonical_write_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    hyb1_default_activation_enabled: bool = False
    specialist_routing_enabled: bool = False
    action_execution_enabled: bool = False
    training_enabled: bool = False
    scheduler_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SingleGateTrialDecision:
    decision_id: str
    trial_target_id: str
    outcome: SingleGateTrialDecisionOutcome
    rationale: str
    applied: bool = False
    gate_opened: bool = False
    trial_executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SingleGateTrialAuditRecord:
    audit_id: str
    trial_target_id: str
    decision_id: str
    audit_summary: str
    generated_for_review_only: bool = True
    gate_opened: bool = False
    trial_executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class SingleGateTrialReportEntry:
    report_entry_id: str
    trial_target_id: str
    scope_summary: str
    input_case_summary: str
    expected_trace_summary: str
    safety_boundary_summary: str
    decision_summary: str
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_single_gate_trial_target(source_activation_plan_id: str = "") -> SingleGateTrialTarget:
    return SingleGateTrialTarget(
        trial_target_id=_stable_id("single-gate-target", "runtime_console_message_preview", source_activation_plan_id),
        source_activation_plan_id=source_activation_plan_id,
    )


def create_single_gate_trial_scope(target: SingleGateTrialTarget) -> SingleGateTrialScope:
    return SingleGateTrialScope(
        scope_id=_stable_id("single-gate-scope", target.trial_target_id),
        trial_target_id=target.trial_target_id,
        allowed_path=("manual_message_input", "raw_experience_preview", "semantic_adapter_preview", "trace_summary", "safety_status", "deterministic_response_preview"),
        blocked_path=("provider_calls", "memory_writes", "recall_mutation", "canonical_writes", "hyb1_default_activation", "specialist_routing", "action_execution", "training", "background_ingestion"),
    )


def create_single_gate_trial_input_case(target: SingleGateTrialTarget, message: str = STARTER_DELTA_QUESTION) -> SingleGateTrialInputCase:
    return SingleGateTrialInputCase(
        input_case_id=_stable_id("single-gate-case", target.trial_target_id, message),
        trial_target_id=target.trial_target_id,
        message=message,
        expected_intent_summary="ask about DELTA replay and consolidation architecture",
        expected_review_only_status="preview only; no memory write",
        expected_disabled_flags=("provider_calls", "memory_mutation", "action_execution", "training"),
    )


def create_single_gate_expected_trace(case: SingleGateTrialInputCase) -> SingleGateTrialExpectedTrace:
    return SingleGateTrialExpectedTrace(expected_trace_id=_stable_id("single-gate-expected-trace", case.input_case_id), input_case_id=case.input_case_id)


def create_single_gate_safety_boundary(target: SingleGateTrialTarget) -> SingleGateTrialSafetyBoundary:
    return SingleGateTrialSafetyBoundary(boundary_id=_stable_id("single-gate-boundary", target.trial_target_id), trial_target_id=target.trial_target_id)


def create_single_gate_trial_decision(target: SingleGateTrialTarget) -> SingleGateTrialDecision:
    return SingleGateTrialDecision(
        decision_id=_stable_id("single-gate-decision", target.trial_target_id),
        trial_target_id=target.trial_target_id,
        outcome=SingleGateTrialDecisionOutcome.ELIGIBLE_FOR_FIRST_LIVE_CONSOLE_PATH,
        rationale="design-only trial target may proceed to first console-only path implementation",
    )


def create_single_gate_trial_audit(target: SingleGateTrialTarget, decision: SingleGateTrialDecision) -> SingleGateTrialAuditRecord:
    return SingleGateTrialAuditRecord(
        audit_id=_stable_id("single-gate-audit", target.trial_target_id, decision.decision_id),
        trial_target_id=target.trial_target_id,
        decision_id=decision.decision_id,
        audit_summary="single-gate design only; gate not opened and trial not executed",
    )


def create_single_gate_trial_report_entry(target: SingleGateTrialTarget, scope: SingleGateTrialScope, decision: SingleGateTrialDecision) -> SingleGateTrialReportEntry:
    return SingleGateTrialReportEntry(
        report_entry_id=_stable_id("single-gate-entry", target.trial_target_id, scope.scope_id, decision.decision_id),
        trial_target_id=target.trial_target_id,
        scope_summary="manual/local/deterministic console preview path",
        input_case_summary=STARTER_DELTA_QUESTION,
        expected_trace_summary="experience, semantic, safety, and response previews expected",
        safety_boundary_summary="provider/memory/action/training paths disabled",
        decision_summary=decision.outcome.value,
        recommended_next_review_step="first live interaction path, console only",
    )


def validate_single_gate_target_closed(target: SingleGateTrialTarget) -> bool:
    return not any((target.gate_open, target.active, target.trial_execution_enabled))


def validate_single_gate_scope_safe(scope: SingleGateTrialScope) -> bool:
    return scope.manual_only and scope.local_only and scope.deterministic_only and "provider_calls" in scope.blocked_path


def validate_expected_trace_non_mutating(trace: SingleGateTrialExpectedTrace) -> bool:
    return trace.expected_experience_record and trace.expected_semantic_preview and trace.expected_safety_status and trace.expected_response_preview and not any(
        (trace.expected_memory_write, trace.expected_provider_call, trace.expected_action_execution, trace.expected_training)
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
