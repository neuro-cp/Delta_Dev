"""DELTA 1.0 gated capability activation framework."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now


CAPABILITY_STATES = (
    "UNAVAILABLE",
    "REGISTERED",
    "SHADOW_ONLY",
    "DISABLED",
    "PILOT_ELIGIBLE",
    "TRIAL_APPROVED",
    "TRIAL_ACTIVE",
    "SUSPENDED",
    "REVOKED",
    "RETIRED",
)

AUTHORITIES = ("OBSERVE", "ADVISE", "PROPOSE", "PREPARE", "EXECUTE_BOUNDED")
MAX_AUTHORITIES = {
    "RC6_GOVERNED_EXTERNAL_INTELLIGENCE": "ADVISE",
    "RC8_GOVERNED_EXTERNAL_RETRIEVAL": "ADVISE",
    "RC9_REAL_CAMPAIGN_OPERATIONS": "PREPARE",
    "RC10_SPECIALIST_COGNITION": "ADVISE",
    "PYTHON_CODING_MODULE_V1": "PREPARE",
}


@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    name: str
    owner: str
    state: str
    max_authority: str
    dependencies: tuple[str, ...]
    allowed_modes: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    kill_switch: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ActivationRequest:
    request_id: str
    capability_id: str
    requested_state: str
    requested_authority: str
    operator_approved: bool
    scope: str
    evidence_refs: tuple[str, ...]
    requested_by: str = "operator"
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ActivationDecision:
    decision_id: str
    capability_id: str
    allowed: bool
    from_state: str
    to_state: str
    authority: str
    reasons: tuple[str, ...]
    audit_event: dict[str, Any]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


TRANSITIONS: dict[str, tuple[str, ...]] = {
    "UNAVAILABLE": ("REGISTERED",),
    "REGISTERED": ("SHADOW_ONLY", "DISABLED", "RETIRED"),
    "SHADOW_ONLY": ("PILOT_ELIGIBLE", "DISABLED", "SUSPENDED", "RETIRED"),
    "DISABLED": ("SHADOW_ONLY", "PILOT_ELIGIBLE", "RETIRED"),
    "PILOT_ELIGIBLE": ("TRIAL_APPROVED", "SUSPENDED", "DISABLED"),
    "TRIAL_APPROVED": ("TRIAL_ACTIVE", "SUSPENDED", "DISABLED"),
    "TRIAL_ACTIVE": ("SUSPENDED", "DISABLED", "RETIRED"),
    "SUSPENDED": ("DISABLED", "PILOT_ELIGIBLE", "REVOKED"),
    "REVOKED": ("RETIRED",),
    "RETIRED": (),
}


def default_capabilities() -> dict[str, CapabilityDescriptor]:
    return {
        key: CapabilityDescriptor(
            capability_id=key,
            name=key.replace("_", " ").title(),
            owner="DELTA_1_0_OPERATOR_PILOT",
            state="SHADOW_ONLY" if key in ("RC10_SPECIALIST_COGNITION", "PYTHON_CODING_MODULE_V1") else "DISABLED",
            max_authority=authority,
            dependencies=(),
            allowed_modes=("OBSERVATION_ONLY", "ASSISTED_WORK", "REVIEW_WORKFLOW", "CONTROLLED_CAPABILITY_TRIAL"),
            prohibited_actions=(
                "provider_call_without_operator_approval",
                "network_call",
                "automatic_execution",
                "automatic_code_modification",
                "automatic_commit_push",
                "hidden_persistence",
                "delta_75_interaction",
            ),
            evidence_requirements=("real_operator_evidence", "focused_tests", "governance_audit"),
        )
        for key, authority in MAX_AUTHORITIES.items()
    }


def activation_request(
    capability_id: str,
    requested_state: str,
    requested_authority: str,
    *,
    operator_approved: bool,
    scope: str,
    evidence_refs: tuple[str, ...] = (),
    requested_by: str = "operator",
) -> ActivationRequest:
    return ActivationRequest(
        request_id=stable_id("activation-request", capability_id, requested_state, requested_authority, scope, evidence_refs),
        capability_id=capability_id,
        requested_state=requested_state,
        requested_authority=requested_authority,
        operator_approved=operator_approved,
        scope=scope,
        evidence_refs=evidence_refs,
        requested_by=requested_by,
    )


def evaluate_activation(descriptor: CapabilityDescriptor, request: ActivationRequest) -> ActivationDecision:
    reasons: list[str] = []
    if descriptor.kill_switch:
        reasons.append("kill_switch_active")
    if request.requested_by == descriptor.capability_id:
        reasons.append("self_activation_rejected")
    if not request.operator_approved:
        reasons.append("operator_approval_required")
    if request.requested_state not in TRANSITIONS.get(descriptor.state, ()):
        reasons.append("invalid_state_transition")
    if _authority_rank(request.requested_authority) > _authority_rank(descriptor.max_authority):
        reasons.append("requested_authority_exceeds_capability_maximum")
    if request.requested_authority == "EXECUTE_BOUNDED":
        reasons.append("execute_bounded_not_available_in_delta_1_0_foundation")
    if len(request.evidence_refs) < len(descriptor.evidence_requirements):
        reasons.append("insufficient_evidence")
    if "delta-75" in request.scope.lower() or "delta_75" in request.scope.lower():
        reasons.append("delta_75_out_of_scope")
    allowed = not reasons
    to_state = request.requested_state if allowed else descriptor.state
    return ActivationDecision(
        decision_id=stable_id("activation-decision", descriptor.capability_id, request.request_id, allowed, reasons),
        capability_id=descriptor.capability_id,
        allowed=allowed,
        from_state=descriptor.state,
        to_state=to_state,
        authority=request.requested_authority if allowed else descriptor.max_authority,
        reasons=tuple(reasons) if reasons else ("activation_request_accepted_for_operator_governed_trial",),
        audit_event={
            "created_at": utc_now(),
            "request_id": request.request_id,
            "operator_approved": request.operator_approved,
            "fail_closed": not allowed,
            "hidden_activation": False,
        },
    )


def transition_descriptor(descriptor: CapabilityDescriptor, decision: ActivationDecision) -> CapabilityDescriptor:
    if not decision.allowed:
        return descriptor
    return replace(descriptor, state=decision.to_state)


def gated_capability_report() -> dict[str, Any]:
    caps = default_capabilities()
    decisions = {}
    for cap_id, descriptor in caps.items():
        request = activation_request(
            cap_id,
            "TRIAL_ACTIVE",
            "EXECUTE_BOUNDED",
            operator_approved=False,
            scope="attempted automatic activation",
            evidence_refs=(),
            requested_by=cap_id,
        )
        decisions[cap_id] = evaluate_activation(descriptor, request)
    return {
        "status": "GATED_CAPABILITY_FRAMEWORK_READY_FAIL_CLOSED",
        "capabilities": caps,
        "negative_control_decisions": decisions,
        "rc6_status": "DISABLED_PENDING_REAL_OPERATOR_EVIDENCE",
        "rc8_status": "DISABLED_PENDING_OPERATOR_TRIAL",
        "rc9_status": "PREPARE_ONLY_REQUIRES_OPERATOR_APPROVAL",
        "rc10_status": "SHADOW_ONLY_ADVISORY",
        "python_module_status": "SHADOW_ONLY_PROPOSE_PREPARE",
        "safety": safety_metadata(),
    }


def _authority_rank(authority: str) -> int:
    if authority not in AUTHORITIES:
        return len(AUTHORITIES)
    return AUTHORITIES.index(authority)
