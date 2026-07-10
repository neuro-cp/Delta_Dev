"""RC3-A capability gap analysis."""

from __future__ import annotations

from orchestration.runtime.rc3_foundation_state import (
    CapabilityGapAssessment,
    GoalFrame,
    PlanFrame,
    SAFETY_DEFAULTS,
    _stable_id,
)


RC2_CAPABILITIES = {
    "conversation",
    "recall",
    "working memory",
    "contradiction",
    "analogy",
    "wrs",
    "substrate retrieval",
}

RC3_SCAFFOLD_CAPABILITIES = {
    "goal interpretation",
    "read-only planning",
    "introspection",
    "progress evaluation",
    "capability gap",
}


def analyze_capability_gap(goal: GoalFrame, plan: PlanFrame) -> CapabilityGapAssessment:
    requested = _requested(goal, plan)
    existing_rc2 = tuple(item for item in requested if item in RC2_CAPABILITIES)
    existing_rc3 = tuple(item for item in requested if item in RC3_SCAFFOLD_CAPABILITIES)
    missing = tuple(item for item in requested if item not in RC2_CAPABILITIES and item not in RC3_SCAFFOLD_CAPABILITIES)
    recommendation = _recommendation(goal, missing)
    return CapabilityGapAssessment(
        assessment_id=_stable_id("gap", goal.goal_id, plan.plan_id, ",".join(requested)),
        goal_id=goal.goal_id,
        plan_id=plan.plan_id,
        requested_capabilities=requested,
        existing_capability_matches=existing_rc2 + existing_rc3,
        missing_capabilities=missing,
        plugin_needed="plugin" in missing,
        sandbox_needed="sandbox" in missing or "code execution" in missing,
        proposal_needed=bool(missing),
        recommendation=recommendation,
        safety=dict(SAFETY_DEFAULTS),
    )


def _requested(goal: GoalFrame, plan: PlanFrame) -> tuple[str, ...]:
    lower = " ".join((goal.source_user_text, goal.normalized_objective, plan.strategy)).lower()
    requested = set()
    if "conversation" in lower:
        requested.add("conversation")
    if "recall" in lower or "substrate" in lower:
        requested.add("recall")
    if "goal" in lower:
        requested.add("goal interpretation")
    if "plan" in lower or "planning" in lower:
        requested.add("read-only planning")
    if "introspection" in lower:
        requested.add("introspection")
    if "progress" in lower:
        requested.add("progress evaluation")
    if "capability gap" in lower:
        requested.add("capability gap")
    if "plugin" in lower:
        requested.add("plugin")
    if "sandbox" in lower:
        requested.add("sandbox")
    if "code" in lower or "coding" in lower:
        requested.add("code execution")
    return tuple(sorted(requested or {"goal interpretation", "read-only planning"}))


def _recommendation(goal: GoalFrame, missing: tuple[str, ...]) -> str:
    if "do not create or activate plugins" in goal.prohibited_actions and "plugin" in missing:
        return "plugin_candidate_deferred_by_operator_prohibition"
    if "do not create sandboxes" in goal.prohibited_actions and "sandbox" in missing:
        return "sandbox_experiment_candidate_deferred_by_operator_prohibition"
    if "code execution" in missing:
        return "sandbox_experiment_candidate"
    if "plugin" in missing:
        return "plugin_candidate"
    if missing:
        return "operator_decision_required"
    return "existing_rc3_scaffold_sufficient"
