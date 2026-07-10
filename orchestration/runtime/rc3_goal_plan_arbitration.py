"""RC3-A goal/plan arbitration."""

from __future__ import annotations

from orchestration.runtime.rc3_foundation_state import (
    GoalFrame,
    GoalPlanArbitration,
    PlanFrame,
    SAFETY_DEFAULTS,
    _stable_id,
)
from orchestration.runtime.rc3_plan_validator import PlanValidation


def arbitrate_goal_plan(
    goal: GoalFrame,
    plan: PlanFrame,
    validation: PlanValidation,
    *,
    previous_goal: GoalFrame | None = None,
) -> GoalPlanArbitration:
    conflicts = []
    rejected_reasons = []
    if previous_goal and goal.superseded_goal == previous_goal.goal_id:
        rejected_reasons.append(f"stale goal superseded: {previous_goal.goal_id}")
    if validation.result in ("blocked", "rejected"):
        conflicts.extend(validation.failed_checks)
        rejected_reasons.append(f"plan validation result: {validation.result}")
    if goal.status == "awaiting_clarification":
        conflicts.append("goal_requires_clarification")
    selected = not conflicts and validation.result in ("valid", "valid_with_warnings")
    status = "accepted_read_only" if selected else ("needs_clarification" if goal.status == "awaiting_clarification" else "rejected")
    return GoalPlanArbitration(
        arbitration_id=_stable_id("arbitration", goal.goal_id, plan.plan_id, validation.result),
        goal_id=goal.goal_id,
        plan_id=plan.plan_id,
        status=status,
        selected=selected,
        conflicts=tuple(dict.fromkeys(conflicts)),
        rejected_reasons=tuple(dict.fromkeys(rejected_reasons)),
        constraint_checks=tuple(f"preserved: {item}" for item in goal.constraints) or ("no_explicit_constraints_found",),
        decision_reason=_decision_reason(selected, validation),
        operator_approval_required_before_action=True,
        safety=dict(SAFETY_DEFAULTS),
    )


def _decision_reason(selected: bool, validation: PlanValidation) -> str:
    if selected:
        return "Selected read-only plan because validation found no execution authority and constraints are preserved."
    return f"Plan not selected because validation returned {validation.result}; operator clarification or revision is required."
