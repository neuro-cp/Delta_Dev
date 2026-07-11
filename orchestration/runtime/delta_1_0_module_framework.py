"""Governed module attachment framework for DELTA 1.0."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now


MODULE_STATES = (
    "DISCOVERED",
    "REGISTERED",
    "VALIDATED",
    "DISABLED",
    "SHADOW_ONLY",
    "PILOT_ELIGIBLE",
    "ATTACHED",
    "SUSPENDED",
    "DETACHED",
    "RETIRED",
)

PROHIBITED_PERMISSIONS = {
    "provider_call",
    "network_call",
    "production_write",
    "automatic_commit",
    "automatic_push",
    "deployment",
    "hidden_persistence",
    "delta_75_access",
}


@dataclass(frozen=True)
class ModuleManifest:
    module_id: str
    name: str
    version: str
    declared_permissions: tuple[str, ...]
    declared_inputs: tuple[str, ...]
    declared_outputs: tuple[str, ...]
    side_effects: tuple[str, ...]
    rollback_strategy: str
    owner: str = "operator"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ModuleRegistryEntry:
    manifest: ModuleManifest
    state: str
    validation_errors: tuple[str, ...]
    attached_at: str | None = None
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ModuleCallRequest:
    module_id: str
    requested_permission: str
    input_type: str
    output_type: str
    operator_approved: bool
    payload_summary: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ModuleCallDecision:
    allowed: bool
    reasons: tuple[str, ...]
    effective_permissions: tuple[str, ...]
    audit: dict[str, Any]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def validate_manifest(manifest: ModuleManifest) -> tuple[str, ...]:
    errors: list[str] = []
    prohibited = sorted(set(manifest.declared_permissions) & PROHIBITED_PERMISSIONS)
    if prohibited:
        errors.append(f"prohibited_permissions:{','.join(prohibited)}")
    if any(effect != "none" for effect in manifest.side_effects):
        errors.append("side_effects_must_be_none_for_delta_1_0")
    if not manifest.declared_inputs:
        errors.append("declared_inputs_required")
    if not manifest.declared_outputs:
        errors.append("declared_outputs_required")
    if "rollback" not in manifest.rollback_strategy.lower():
        errors.append("rollback_strategy_required")
    return tuple(errors)


def register_module(manifest: ModuleManifest) -> ModuleRegistryEntry:
    errors = validate_manifest(manifest)
    state = "VALIDATED" if not errors else "DISABLED"
    return ModuleRegistryEntry(manifest=manifest, state=state, validation_errors=errors)


def attach_module(entry: ModuleRegistryEntry, *, operator_approved: bool) -> ModuleRegistryEntry:
    if not operator_approved:
        return entry
    if entry.validation_errors:
        return entry
    return replace(entry, state="ATTACHED", attached_at=utc_now())


def suspend_module(entry: ModuleRegistryEntry, reason: str) -> ModuleRegistryEntry:
    return replace(entry, state="SUSPENDED", validation_errors=tuple(sorted(set(entry.validation_errors + (reason,)))))


def detach_module(entry: ModuleRegistryEntry) -> ModuleRegistryEntry:
    return replace(entry, state="DETACHED")


def evaluate_module_call(entry: ModuleRegistryEntry, request: ModuleCallRequest, session_permissions: tuple[str, ...]) -> ModuleCallDecision:
    reasons: list[str] = []
    effective = tuple(sorted(set(entry.manifest.declared_permissions) & set(session_permissions)))
    if entry.state not in ("ATTACHED", "SHADOW_ONLY"):
        reasons.append("module_not_attached_or_shadow_available")
    if request.requested_permission not in effective:
        reasons.append("requested_permission_not_effective")
    if request.requested_permission in PROHIBITED_PERMISSIONS:
        reasons.append("prohibited_permission_requested")
    if request.input_type not in entry.manifest.declared_inputs:
        reasons.append("undeclared_input_type")
    if request.output_type not in entry.manifest.declared_outputs:
        reasons.append("undeclared_output_type")
    if not request.operator_approved:
        reasons.append("operator_approval_required")
    allowed = not reasons
    return ModuleCallDecision(
        allowed=allowed,
        reasons=tuple(reasons) if reasons else ("module_call_allowed_for_bounded_prepare_only",),
        effective_permissions=effective,
        audit={"module_id": entry.manifest.module_id, "fail_closed": not allowed, "created_at": utc_now()},
    )


def python_module_manifest() -> ModuleManifest:
    return ModuleManifest(
        module_id="PYTHON_CODING_MODULE_V1",
        name="Python Coding Module v1",
        version="1.0.0",
        declared_permissions=("repo_read", "proposal_prepare", "validation_plan_prepare"),
        declared_inputs=("approved_repo_root", "change_request", "test_failure", "python_source"),
        declared_outputs=("repo_index", "implementation_proposal", "patch_proposal", "failure_interpretation", "validation_plan"),
        side_effects=("none",),
        rollback_strategy="rollback by detaching module; proposals are inert and unapplied",
    )


def module_framework_report() -> dict[str, Any]:
    entry = register_module(python_module_manifest())
    attached = attach_module(entry, operator_approved=True)
    denied = evaluate_module_call(
        attached,
        ModuleCallRequest(
            module_id="PYTHON_CODING_MODULE_V1",
            requested_permission="automatic_commit",
            input_type="approved_repo_root",
            output_type="patch_proposal",
            operator_approved=True,
            payload_summary="attempt to commit from runtime",
        ),
        session_permissions=("repo_read", "proposal_prepare"),
    )
    return {
        "status": "MODULE_ATTACHMENT_FRAMEWORK_READY",
        "python_module_entry": attached,
        "negative_control": denied,
        "safety": safety_metadata(),
    }
