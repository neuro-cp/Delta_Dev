"""DELTA 1.0 development objective engine."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now


OBJECTIVE_TYPES = (
    "CAPABILITY_IMPROVEMENT",
    "RELIABILITY_IMPROVEMENT",
    "GOVERNANCE_HARDENING",
    "PERFORMANCE_OPTIMIZATION",
    "USABILITY_IMPROVEMENT",
    "BUG_FIX",
    "DOCUMENTATION",
    "EVALUATION",
    "OPERATOR_WORKFLOW",
)

OBJECTIVE_ORIGINS = (
    "OPERATOR_CREATED",
    "OPERATOR_APPROVED_PROPOSAL",
    "PILOT_EVIDENCE",
    "TEST_FAILURE",
    "BENCHMARK_FAILURE",
    "GOVERNANCE_AUDIT",
    "CODE_REVIEW",
)

OBJECTIVE_STATES = (
    "DRAFT",
    "PROPOSED",
    "AWAITING_EVIDENCE",
    "AWAITING_OPERATOR_APPROVAL",
    "APPROVED",
    "ACTIVE",
    "PAUSED",
    "BLOCKED",
    "EVALUATING",
    "COMPLETED",
    "REJECTED",
    "CANCELLED",
    "FAILED",
)

VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "DRAFT": ("PROPOSED", "CANCELLED"),
    "PROPOSED": ("AWAITING_EVIDENCE", "AWAITING_OPERATOR_APPROVAL", "REJECTED", "CANCELLED"),
    "AWAITING_EVIDENCE": ("AWAITING_OPERATOR_APPROVAL", "REJECTED", "CANCELLED"),
    "AWAITING_OPERATOR_APPROVAL": ("APPROVED", "REJECTED", "DEFERRED", "CANCELLED"),
    "APPROVED": ("ACTIVE", "PAUSED", "CANCELLED"),
    "ACTIVE": ("PAUSED", "BLOCKED", "EVALUATING", "FAILED", "CANCELLED"),
    "PAUSED": ("ACTIVE", "CANCELLED"),
    "BLOCKED": ("ACTIVE", "FAILED", "CANCELLED"),
    "EVALUATING": ("COMPLETED", "FAILED", "ACTIVE"),
    "COMPLETED": (),
    "REJECTED": (),
    "CANCELLED": (),
    "FAILED": (),
}


@dataclass(frozen=True)
class PriorityBreakdown:
    user_value: float
    evidence_strength: float
    risk_reduction: float
    implementation_cost_inverse: float
    governance_urgency: float

    @property
    def score(self) -> float:
        return round(
            (self.user_value * 0.3)
            + (self.evidence_strength * 0.25)
            + (self.risk_reduction * 0.2)
            + (self.implementation_cost_inverse * 0.15)
            + (self.governance_urgency * 0.1),
            4,
        )


@dataclass(frozen=True)
class ResourcePlan:
    allowed_resources: tuple[str, ...]
    prohibited_resources: tuple[str, ...]
    approval_required: bool
    budget_notes: str


@dataclass(frozen=True)
class EvaluationPlan:
    success_criteria: tuple[str, ...]
    required_tests: tuple[str, ...]
    regression_checks: tuple[str, ...]
    stop_conditions: tuple[str, ...]


@dataclass(frozen=True)
class DevelopmentObjective:
    objective_id: str
    title: str
    objective_type: str
    origin: str
    state: str
    evidence_refs: tuple[str, ...]
    priority: PriorityBreakdown
    resource_plan: ResourcePlan
    evaluation_plan: EvaluationPlan
    operator_approved: bool = False
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class CapabilityGap:
    gap_id: str
    observed_deficit: str
    affected_capability: str
    evidence_refs: tuple[str, ...]
    proposed_objective: DevelopmentObjective
    proposal_only: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def propose_objective(
    title: str,
    *,
    objective_type: str,
    origin: str,
    evidence_refs: tuple[str, ...] = (),
    success_criteria: tuple[str, ...] = (),
) -> DevelopmentObjective:
    if objective_type not in OBJECTIVE_TYPES:
        raise ValueError(f"unknown objective type: {objective_type}")
    if origin not in OBJECTIVE_ORIGINS:
        raise ValueError(f"unknown objective origin: {origin}")
    priority = PriorityBreakdown(
        user_value=0.85 if origin.startswith("OPERATOR") else 0.65,
        evidence_strength=min(1.0, 0.35 + 0.15 * len(evidence_refs)),
        risk_reduction=0.75 if objective_type == "GOVERNANCE_HARDENING" else 0.55,
        implementation_cost_inverse=0.65,
        governance_urgency=0.9 if objective_type == "GOVERNANCE_HARDENING" else 0.55,
    )
    return DevelopmentObjective(
        objective_id=stable_id("delta10-objective", title, objective_type, origin, evidence_refs),
        title=title.strip(),
        objective_type=objective_type,
        origin=origin,
        state="PROPOSED",
        evidence_refs=evidence_refs,
        priority=priority,
        resource_plan=ResourcePlan(
            allowed_resources=("repo_inspection", "focused_tests", "local_reports"),
            prohibited_resources=("provider_calls", "network_calls", "production_mutation", "delta_75_interaction"),
            approval_required=True,
            budget_notes="operator approval required before any bounded trial",
        ),
        evaluation_plan=EvaluationPlan(
            success_criteria=success_criteria or ("focused_tests_pass", "governance_preserved", "operator_disposition_recorded"),
            required_tests=("py_compile", "focused_unit_tests"),
            regression_checks=("rc2_fast_validate", "rc3_rc4_rc5_focused_regressions"),
            stop_conditions=("governance_regression", "scope_creep", "operator_rejection"),
        ),
    )


def detect_capability_gap(observed_deficit: str, affected_capability: str, evidence_refs: tuple[str, ...]) -> CapabilityGap:
    objective = propose_objective(
        f"Improve {affected_capability}: {observed_deficit}",
        objective_type="CAPABILITY_IMPROVEMENT",
        origin="PILOT_EVIDENCE",
        evidence_refs=evidence_refs,
        success_criteria=(f"{affected_capability}_improves_without_governance_regression",),
    )
    return CapabilityGap(
        gap_id=stable_id("delta10-gap", observed_deficit, affected_capability, evidence_refs),
        observed_deficit=observed_deficit,
        affected_capability=affected_capability,
        evidence_refs=evidence_refs,
        proposed_objective=objective,
    )


def transition_objective(objective: DevelopmentObjective, to_state: str, *, operator_approved: bool = False, evidence_refs: tuple[str, ...] = ()) -> tuple[DevelopmentObjective, str]:
    if to_state not in OBJECTIVE_STATES:
        return objective, "unknown_state"
    if to_state not in VALID_TRANSITIONS.get(objective.state, ()):
        return objective, "invalid_transition"
    if to_state in ("APPROVED", "ACTIVE", "COMPLETED") and not operator_approved:
        return objective, "operator_approval_required"
    if to_state == "COMPLETED" and not evidence_refs:
        return objective, "completion_requires_evidence"
    return replace(
        objective,
        state=to_state,
        operator_approved=objective.operator_approved or operator_approved,
        evidence_refs=tuple(sorted(set(objective.evidence_refs + evidence_refs))),
    ), "transition_accepted"


def objective_engine_report() -> dict[str, Any]:
    gap = detect_capability_gap("operator pilot needs rollback evidence", "RC4_RC5_FREEZE_EVIDENCE", ("pilot-session-1",))
    approved, approval_result = transition_objective(gap.proposed_objective, "AWAITING_OPERATOR_APPROVAL")
    return {
        "status": "DEVELOPMENT_OBJECTIVE_ENGINE_READY_PROPOSAL_ONLY",
        "sample_gap": gap,
        "sample_transition": {"state": approved.state, "result": approval_result},
        "objective_states": OBJECTIVE_STATES,
        "safety": safety_metadata(),
    }
