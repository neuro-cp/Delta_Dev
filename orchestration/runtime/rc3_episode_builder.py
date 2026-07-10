"""Unified RC3-A episode builder."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from orchestration.runtime.rc3_capability_gap_analyzer import analyze_capability_gap
from orchestration.runtime.rc3_foundation_state import (
    RC3Episode,
    SAFETY_DEFAULTS,
    _stable_id,
)
from orchestration.runtime.rc3_goal_interpreter import interpret_goal
from orchestration.runtime.rc3_goal_lifecycle import evaluate_goal_transition
from orchestration.runtime.rc3_goal_plan_arbitration import arbitrate_goal_plan
from orchestration.runtime.rc3_introspection_engine import build_introspection_snapshot
from orchestration.runtime.rc3_plan_generator import generate_read_only_plan
from orchestration.runtime.rc3_plan_validator import validate_plan
from orchestration.runtime.rc3_progress_evaluator import evaluate_progress


def build_rc3_goal_planning_episode(
    user_message: str,
    *,
    rc2_episode_reference: str | None = None,
    previous_episode: RC3Episode | None = None,
    explicit_operator_constraints: tuple[str, ...] = (),
    completed_step_evidence: tuple[str, ...] = (),
    failed_step_evidence: tuple[str, ...] = (),
    operator_review_state: str = "not_reviewed",
) -> RC3Episode:
    """Build one explicit RC3-A episode.

    This is an explicit entry point. It is not attached to every normal
    conversation turn.
    """

    previous_goal = previous_episode.goal_frame if previous_episode else None
    interpretation = interpret_goal(
        user_message,
        rc2_episode_reference=rc2_episode_reference,
        previous_goal=previous_goal,
        explicit_operator_constraints=explicit_operator_constraints,
    )
    goal = interpretation.goal_frame
    transition = evaluate_goal_transition(
        goal,
        "confirmed" if goal.status == "interpreted" else "awaiting_clarification",
        reason="RC3-A explicit episode construction",
    )
    plan = generate_read_only_plan(goal)
    validation = validate_plan(goal, plan)
    arbitration = arbitrate_goal_plan(goal, plan, validation, previous_goal=previous_goal)
    introspection = build_introspection_snapshot(goal, plan, validation, arbitration)
    progress = evaluate_progress(
        goal,
        plan,
        validation,
        completed_step_evidence=completed_step_evidence,
        failed_step_evidence=failed_step_evidence,
        operator_review_state=operator_review_state,
    )
    gap = analyze_capability_gap(goal, plan)
    overlay = {
        "entry_point": "build_rc3_goal_planning_episode",
        "goal_interpretation_trace": interpretation.trace,
        "goal_transition": asdict(transition),
        "plan_validation": asdict(validation),
        "arbitration": asdict(arbitration),
        "introspection": asdict(introspection),
        "progress": asdict(progress),
        "capability_gap": asdict(gap),
        "normal_conversation_attached": False,
        "execution_authorized": False,
        "persistence_status": "ephemeral",
        "safety": dict(SAFETY_DEFAULTS),
    }
    return RC3Episode(
        episode_id=_stable_id("episode", user_message, goal.goal_id, plan.plan_id),
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        source_text=user_message,
        rc2_episode_reference=rc2_episode_reference,
        goal_frame=goal,
        plan_frame=plan,
        arbitration=arbitration,
        introspection=introspection,
        progress=progress,
        capability_gap=gap,
        developer_overlay=overlay,
        persistence_status="ephemeral",
        safety=dict(SAFETY_DEFAULTS),
    )
