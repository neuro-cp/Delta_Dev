"""Natural RC3-A summary renderer."""

from __future__ import annotations

from orchestration.runtime.rc3_foundation_state import RC3Episode


def render_rc3_foundation_summary(episode: RC3Episode) -> dict[str, object]:
    goal = episode.goal_frame
    plan = episode.plan_frame
    progress = episode.progress
    gap = episode.capability_gap
    constraints = "; ".join(goal.constraints) if goal.constraints else "no explicit extra constraints"
    prohibitions = "; ".join(goal.prohibited_actions) if goal.prohibited_actions else "no explicit prohibitions"
    steps = [step.summary for step in plan.steps]
    missing = "; ".join(progress.missing_evidence) if progress.missing_evidence else "no missing evidence"
    gaps = "; ".join(gap.missing_capabilities) if gap.missing_capabilities else "no capability gap detected"
    text = (
        f"I understand the objective as: {goal.normalized_objective}. "
        f"The controlling constraints are {constraints}; the prohibited actions are {prohibitions}. "
        f"The proposed plan is read-only and has {len(steps)} step(s): "
        f"{'; '.join(steps)}. "
        f"Current progress is {progress.status}; missing evidence: {missing}. "
        f"Capability gap assessment: {gap.recommendation} ({gaps}). "
        "No execution, persistence, plugin activation, sandbox creation, provider call, commit, push, or deployment is authorized."
    )
    return {
        "summary": text,
        "developer_overlay": episode.developer_overlay,
        "safety": episode.safety,
    }
