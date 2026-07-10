"""Read-only RC3-A plan generation."""

from __future__ import annotations

from orchestration.runtime.rc3_foundation_state import (
    GoalFrame,
    PlanFrame,
    PlanStepFrame,
    SAFETY_DEFAULTS,
    _stable_id,
)


def generate_read_only_plan(goal: GoalFrame) -> PlanFrame:
    form = _plan_form(goal)
    steps = _steps_for_form(goal, form)
    return PlanFrame(
        plan_id=_stable_id("plan", goal.goal_id, form),
        goal_id=goal.goal_id,
        strategy=form,
        lifecycle_state="draft" if goal.status != "awaiting_clarification" else "needs_clarification",
        steps=steps,
        constraints_preserved=goal.constraints,
        dependencies=_dependencies(steps),
        risks=_risks(goal),
        assumptions=goal.assumptions,
        prohibited_actions=goal.prohibited_actions,
        execution_authorized=False,
        persistence_status="ephemeral",
        provenance={"source_goal_id": goal.goal_id, "planner": "rc3_plan_generator"},
        confidence=0.82 if goal.status != "awaiting_clarification" else 0.42,
        uncertainty="moderate" if goal.status != "awaiting_clarification" else "high_clarification_required",
        safety=dict(SAFETY_DEFAULTS),
    )


def _plan_form(goal: GoalFrame) -> str:
    if goal.status == "awaiting_clarification":
        return "clarification_only"
    if goal.goal_type == "design_goal":
        return "design_only"
    if goal.goal_type == "implementation_goal":
        return "implementation_proposal"
    if goal.goal_type == "validation_goal":
        return "validation_only"
    if goal.prohibited_actions:
        return "review_gated"
    return "linear"


def _steps_for_form(goal: GoalFrame, form: str) -> tuple[PlanStepFrame, ...]:
    if form == "clarification_only":
        summaries = ("Ask the operator to clarify the objective, authority, and success criteria.",)
    elif form == "design_only":
        summaries = (
            "Review current architecture and constraints.",
            "Define the design surface and required fields.",
            "Define validation rules and review gates.",
            "Write the design artifact for operator review.",
        )
    elif form == "implementation_proposal":
        summaries = (
            "Translate the implementation request into a proposal scope.",
            "Identify prohibited actions and permission gaps.",
            "Describe implementation steps without executing them.",
            "Define validation required before any future integration.",
        )
    elif form == "validation_only":
        summaries = (
            "Identify the validation target and success criteria.",
            "Select focused tests or benchmark probes.",
            "Run only approved validation outside RC3 plan execution.",
            "Report results and missing evidence.",
        )
    else:
        summaries = (
            "Interpret the objective.",
            "List constraints, dependencies, and risks.",
            "Prepare a reviewable non-executing plan.",
            "Evaluate progress only from evidence.",
        )
    steps = []
    previous = ()
    for index, summary in enumerate(summaries, start=1):
        step_id = _stable_id("plan-step", goal.goal_id, str(index), summary)
        steps.append(
            PlanStepFrame(
                step_id=step_id,
                summary=summary,
                dependency_ids=previous,
                preserves_constraints=goal.constraints,
                prohibited_actions=goal.prohibited_actions,
                expected_evidence=_expected_evidence(summary),
                risk="low" if "execute" not in summary.lower() else "medium",
                uncertainty=goal.uncertainty,
                non_executing=True,
            )
        )
        previous = (step_id,)
    return tuple(steps)


def _expected_evidence(summary: str) -> tuple[str, ...]:
    lower = summary.lower()
    if "review" in lower:
        return ("operator_review_record",)
    if "validation" in lower or "test" in lower:
        return ("validation_result",)
    if "design" in lower or "artifact" in lower:
        return ("design_artifact",)
    return ("trace_record",)


def _dependencies(steps: tuple[PlanStepFrame, ...]) -> tuple[str, ...]:
    return tuple(dep for step in steps for dep in step.dependency_ids)


def _risks(goal: GoalFrame) -> tuple[str, ...]:
    risks = ["RC3-A plans are descriptive and must not be executed."]
    if goal.prohibited_actions:
        risks.append("Plan must preserve explicit prohibitions.")
    if goal.status == "awaiting_clarification":
        risks.append("Ambiguous goal could produce the wrong plan without clarification.")
    return tuple(risks)
