"""RC3-A progress evaluation."""

from __future__ import annotations

from orchestration.runtime.rc3_foundation_state import (
    GoalFrame,
    PlanFrame,
    ProgressEvaluation,
    SAFETY_DEFAULTS,
    _stable_id,
)
from orchestration.runtime.rc3_plan_validator import PlanValidation


def evaluate_progress(
    goal: GoalFrame,
    plan: PlanFrame,
    validation: PlanValidation,
    *,
    completed_step_evidence: tuple[str, ...] = (),
    failed_step_evidence: tuple[str, ...] = (),
    operator_review_state: str = "not_reviewed",
) -> ProgressEvaluation:
    criteria = goal.success_criteria
    completed = tuple(item for item in criteria if item in completed_step_evidence)
    failed = failed_step_evidence
    blocked = []
    if validation.result in ("blocked", "rejected"):
        blocked.append(f"plan_validation_{validation.result}")
    if operator_review_state != "approved":
        blocked.append("operator_review_outstanding")
    if failed:
        status = "failed"
    elif blocked:
        status = "blocked" if validation.result in ("blocked", "rejected") else "awaiting_review"
    elif completed and len(completed) < len(criteria):
        status = "partially_complete"
    elif completed and len(completed) == len(criteria):
        status = "completed_with_evidence"
    else:
        status = "not_started"
    score = round(len(completed) / max(1, len(criteria)), 4)
    return ProgressEvaluation(
        evaluation_id=_stable_id("progress", goal.goal_id, plan.plan_id, status),
        goal_id=goal.goal_id,
        plan_id=plan.plan_id,
        status=status,
        completion_score=score,
        completion_evidence=completed,
        missing_evidence=tuple(item for item in criteria if item not in completed),
        blockers=tuple(blocked),
        failure_signals=failed,
        completion_requires_operator_confirmation=True,
        safety=dict(SAFETY_DEFAULTS),
    )
