"""RC3-A read-only plan validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orchestration.runtime.rc3_foundation_state import GoalFrame, PlanFrame


@dataclass(frozen=True)
class PlanValidation:
    result: str
    checks_performed: tuple[str, ...]
    passed_checks: tuple[str, ...]
    failed_checks: tuple[str, ...]
    warnings: tuple[str, ...]
    blocked_steps: tuple[str, ...]
    rejected_steps: tuple[str, ...]
    required_clarification: tuple[str, ...]
    confidence: float
    trace: dict[str, Any]


PROHIBITED_STEP_TERMS = (
    "execute plan",
    "run tool",
    "activate plugin",
    "create sandbox",
    "commit changes",
    "push changes",
    "deploy",
    "call provider",
    "write canonical",
    "write noncanonical",
    "touch delta-75",
)


def validate_plan(goal: GoalFrame, plan: PlanFrame) -> PlanValidation:
    checks = [
        "goal_alignment",
        "constraint_preservation",
        "prohibition_preservation",
        "dependency_ordering",
        "measurable_outputs",
        "validation_coverage",
        "operator_checkpoint_presence",
        "hidden_execution_detection",
        "rc2_contract_compatibility",
    ]
    failed: list[str] = []
    warnings: list[str] = []
    rejected_steps: list[str] = []
    blocked_steps: list[str] = []
    if plan.goal_id != goal.goal_id:
        failed.append("goal_alignment")
    if not set(goal.constraints).issubset(set(plan.constraints_preserved)):
        failed.append("constraint_preservation")
    for prohibition in goal.prohibited_actions:
        if prohibition not in plan.prohibited_actions:
            failed.append("prohibition_preservation")
    seen: set[str] = set()
    for step in plan.steps:
        if not set(step.dependency_ids).issubset(seen):
            failed.append("dependency_ordering")
        seen.add(step.step_id)
        lower = step.summary.lower()
        if any(term in lower for term in PROHIBITED_STEP_TERMS) or step.non_executing is not True:
            rejected_steps.append(step.step_id)
            failed.append("hidden_execution_detection")
        if not step.expected_evidence:
            failed.append("measurable_outputs")
    if not any("validation" in " ".join(step.expected_evidence).lower() or "validation" in step.summary.lower() for step in plan.steps):
        warnings.append("validation coverage is light")
    if not any("review" in " ".join(step.expected_evidence).lower() or "review" in step.summary.lower() for step in plan.steps):
        warnings.append("operator checkpoint should be explicit")
    if goal.status == "awaiting_clarification":
        blocked_steps = tuple(step.step_id for step in plan.steps)
        warnings.append("goal requires clarification before planning confidence can improve")
    failed_unique = tuple(dict.fromkeys(failed))
    if rejected_steps:
        result = "rejected"
    elif blocked_steps:
        result = "blocked"
    elif failed_unique:
        result = "blocked"
    elif warnings:
        result = "valid_with_warnings"
    else:
        result = "valid"
    passed = tuple(check for check in checks if check not in failed_unique)
    return PlanValidation(
        result=result,
        checks_performed=tuple(checks),
        passed_checks=passed,
        failed_checks=failed_unique,
        warnings=tuple(dict.fromkeys(warnings)),
        blocked_steps=tuple(blocked_steps),
        rejected_steps=tuple(rejected_steps),
        required_clarification=("clarify objective or authority",) if goal.status == "awaiting_clarification" else (),
        confidence=0.92 if result == "valid" else (0.78 if result == "valid_with_warnings" else 0.35),
        trace={"execution_authorized": plan.execution_authorized, "rc2_contract_changed": False},
    )
