"""Evidence-based RC3-A introspection."""

from __future__ import annotations

from orchestration.runtime.rc3_foundation_state import (
    GoalFrame,
    GoalPlanArbitration,
    IntrospectionSnapshot,
    PlanFrame,
    SAFETY_DEFAULTS,
    _stable_id,
)
from orchestration.runtime.rc3_plan_validator import PlanValidation


def build_introspection_snapshot(
    goal: GoalFrame,
    plan: PlanFrame,
    validation: PlanValidation,
    arbitration: GoalPlanArbitration,
) -> IntrospectionSnapshot:
    claims = (
        {"claim": f"Active objective: {goal.normalized_objective}", "evidence": "GoalFrame.normalized_objective"},
        {"claim": f"Plan strategy: {plan.strategy}", "evidence": "PlanFrame.strategy"},
        {"claim": f"Plan validation result: {validation.result}", "evidence": "PlanValidation.result"},
        {"claim": "No execution authority is present.", "evidence": "PlanFrame.execution_authorized=false"},
        {"claim": "RC3-A state is ephemeral.", "evidence": "GoalFrame.persistence_status and PlanFrame.persistence_status"},
    )
    missing = []
    if goal.operator_confirmation_status != "confirmed":
        missing.append("operator confirmation")
    if validation.required_clarification:
        missing.extend(validation.required_clarification)
    return IntrospectionSnapshot(
        snapshot_id=_stable_id("snapshot", goal.goal_id, plan.plan_id, validation.result),
        claims=claims,
        assumptions=goal.assumptions,
        uncertainty=tuple(missing or ("No durable project evidence has been recorded.",)),
        fabricated_self_state=False,
        hidden_state_detected=False,
        evidence_sources=(
            "GoalFrame",
            "PlanFrame",
            "PlanValidation",
            "GoalPlanArbitration",
            "docs/RC3_STATE_MODEL.md",
        ),
        safety=dict(SAFETY_DEFAULTS),
    )
