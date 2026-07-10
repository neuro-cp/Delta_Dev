from __future__ import annotations

from orchestration.runtime.rc3_capability_gap_analyzer import analyze_capability_gap
from orchestration.runtime.rc3_episode_builder import build_rc3_goal_planning_episode
from orchestration.runtime.rc3_foundation_renderer import render_rc3_foundation_summary
from orchestration.runtime.rc3_goal_interpreter import interpret_goal
from orchestration.runtime.rc3_goal_lifecycle import evaluate_goal_transition
from orchestration.runtime.rc3_goal_plan_arbitration import arbitrate_goal_plan
from orchestration.runtime.rc3_plan_generator import generate_read_only_plan
from orchestration.runtime.rc3_plan_validator import validate_plan
from orchestration.runtime.rc3_progress_evaluator import evaluate_progress


def test_goal_interpreter_extracts_design_goal_and_plugin_prohibition() -> None:
    result = interpret_goal("Design a plugin interface, but do not implement or activate plugins yet.")

    assert result.goal_frame.goal_type == "design_goal"
    assert result.goal_frame.normalized_objective == "Design a plugin interface"
    assert "do not create or activate plugins" in result.goal_frame.prohibited_actions
    assert result.goal_frame.persistence_status == "ephemeral"


def test_goal_interpreter_rejects_casual_thought_as_goal() -> None:
    result = interpret_goal("I wonder whether a plugin might help someday.")

    assert result.goal_frame.goal_type == "no_goal_detected"
    assert result.trace["non_goal_detected"] is True
    assert result.goal_frame.status == "interpreted"


def test_goal_lifecycle_rejects_completion_without_evidence() -> None:
    goal = interpret_goal("Validate the RC3-A reports.").goal_frame
    transition = evaluate_goal_transition(goal, "completed", reason="user asked")

    assert transition.accepted is False
    assert transition.reason == "completion requires evidence"


def test_plan_generator_preserves_constraints_and_stays_non_executing() -> None:
    goal = interpret_goal("Design RC3 docs in read-only mode and do not execute plans.").goal_frame
    plan = generate_read_only_plan(goal)

    assert plan.execution_authorized is False
    assert plan.persistence_status == "ephemeral"
    assert "read-only" in plan.constraints_preserved
    assert all(step.non_executing for step in plan.steps)


def test_plan_validator_rejects_hidden_execution_step() -> None:
    goal = interpret_goal("Design a safe plan.").goal_frame
    plan = generate_read_only_plan(goal)
    bad_step = plan.steps[0].__class__(
        step_id="bad",
        summary="Execute plan and push changes",
        dependency_ids=(),
        preserves_constraints=(),
        prohibited_actions=(),
        expected_evidence=("trace",),
        risk="high",
        uncertainty="high",
        non_executing=False,
    )
    bad_plan = plan.__class__(**{**plan.__dict__, "steps": (bad_step,) + plan.steps[1:]})

    validation = validate_plan(goal, bad_plan)

    assert validation.result == "rejected"
    assert "hidden_execution_detection" in validation.failed_checks


def test_arbitration_rejects_blocked_plan() -> None:
    goal = interpret_goal("Design a read-only plan and execute now even though there should be no execution.").goal_frame
    plan = generate_read_only_plan(goal)
    validation = validate_plan(goal, plan)
    arbitration = arbitrate_goal_plan(goal, plan, validation)

    assert arbitration.selected is False
    assert arbitration.status == "needs_clarification"


def test_progress_requires_evidence_and_review() -> None:
    goal = interpret_goal("Validate the RC3-A reports.").goal_frame
    plan = generate_read_only_plan(goal)
    validation = validate_plan(goal, plan)
    progress = evaluate_progress(goal, plan, validation)

    assert progress.status in ("not_started", "awaiting_review", "blocked")
    assert progress.completion_score == 0.0
    assert progress.completion_requires_operator_confirmation is True


def test_capability_gap_identifies_deferred_sandbox_candidate() -> None:
    goal = interpret_goal("Plan how code could be tested in a sandbox without creating one now.").goal_frame
    plan = generate_read_only_plan(goal)
    gap = analyze_capability_gap(goal, plan)

    assert gap.sandbox_needed is True
    assert gap.recommendation == "sandbox_experiment_candidate_deferred_by_operator_prohibition"
    assert gap.safety["sandbox_creation_performed"] is False


def test_episode_builder_unifies_rc3_a_state_without_execution() -> None:
    episode = build_rc3_goal_planning_episode("Design the RC3-A scaffold and do not touch DELTA-75.")

    assert episode.persistence_status == "ephemeral"
    assert episode.plan_frame.execution_authorized is False
    assert episode.developer_overlay["normal_conversation_attached"] is False
    assert episode.safety["delta_75_interaction_performed"] is False


def test_renderer_summarizes_without_internal_field_names() -> None:
    episode = build_rc3_goal_planning_episode("Design the RC3-A scaffold without execution.")
    rendered = render_rc3_foundation_summary(episode)

    assert "No execution" in rendered["summary"]
    assert "GoalFrame" not in rendered["summary"]
    assert "PlanFrame" not in rendered["summary"]
