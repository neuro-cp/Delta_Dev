from __future__ import annotations

from orchestration.runtime.rc3_episode_builder import build_rc3_goal_planning_episode
from orchestration.runtime.rc3_plan_revision import (
    PlanRevisionRequest,
    build_rc3_revision_episode,
    compare_plans,
    revise_plan,
)
from orchestration.runtime.rc3_revision_benchmark import run_rc3_b_revision_benchmark


def test_revision_requires_supported_trigger_and_justification() -> None:
    episode = build_rc3_goal_planning_episode("Design RC3 docs.")

    unsupported = revise_plan(
        episode.goal_frame,
        episode.plan_frame,
        PlanRevisionRequest(trigger="autonomous_whim", new_evidence=("none",)),
    )
    unjustified = revise_plan(
        episode.goal_frame,
        episode.plan_frame,
        PlanRevisionRequest(trigger="operator_correction"),
    )

    assert unsupported.revision_applied is False
    assert unsupported.decision == "require_clarification"
    assert unjustified.revision_applied is False
    assert unjustified.decision == "continue_current_plan"


def test_revision_applies_operator_correction_without_execution() -> None:
    episode = build_rc3_goal_planning_episode("Design an RC3 plugin interface, but do not activate plugins.")
    result = revise_plan(
        episode.goal_frame,
        episode.plan_frame,
        PlanRevisionRequest(
            trigger="operator_correction",
            updated_constraints=("operator review required",),
            new_evidence=("operator clarified schema-only scope",),
            operator_notes="Schema only.",
        ),
        progress=episode.progress,
        capability_gap=episode.capability_gap,
    )

    assert result.revision_applied is True
    assert result.decision == "revise_existing_plan"
    assert result.revised_plan.execution_authorized is False
    assert result.validation.result in ("valid", "valid_with_warnings")
    assert result.history[0].trigger == "operator_correction"
    assert all(value is False for value in result.safety.values())


def test_plan_diff_reports_added_steps_and_assumption_changes() -> None:
    episode = build_rc3_goal_planning_episode("Design RC3 docs.")
    result = revise_plan(
        episode.goal_frame,
        episode.plan_frame,
        PlanRevisionRequest(
            trigger="assumption_invalidated",
            changed_assumptions=("legacy planner is reference-only",),
            new_evidence=("architecture review updated assumption",),
        ),
        progress=episode.progress,
        capability_gap=episode.capability_gap,
    )
    diff = compare_plans(episode.plan_frame, result.revised_plan)

    assert diff.added_steps
    assert "legacy planner is reference-only" in diff.modified_assumptions
    assert diff.human_readable


def test_revision_episode_keeps_history_in_developer_overlay_only() -> None:
    episode = build_rc3_goal_planning_episode("Design RC3 docs.")
    revised = build_rc3_revision_episode(
        episode.source_text,
        PlanRevisionRequest(
            trigger="evidence_update",
            new_evidence=("operator added validation requirement",),
        ),
        previous_episode=episode,
    )

    assert revised.persistence_status == "ephemeral"
    assert "revision_history" in revised.developer_overlay
    assert revised.developer_overlay["execution_authorized"] is False
    assert revised.safety["hidden_persistence_performed"] is False


def test_controlled_forgetting_hook_design_does_not_delete_or_persist() -> None:
    episode = build_rc3_goal_planning_episode("Design RC3 docs.")
    result = revise_plan(
        episode.goal_frame,
        episode.plan_frame,
        PlanRevisionRequest(
            trigger="assumption_invalidated",
            changed_assumptions=("old assumption obsolete",),
            new_evidence=("new evidence invalidated old assumption",),
        ),
        progress=episode.progress,
        capability_gap=episode.capability_gap,
    )

    assert result.controlled_forgetting_hook.obsolete_assumptions == ("old assumption obsolete",)
    assert result.controlled_forgetting_hook.deletes_anything is False
    assert result.controlled_forgetting_hook.persists_anything is False


def test_rc3_b_revision_benchmark_passes_safety_gate() -> None:
    report = run_rc3_b_revision_benchmark(write_reports=False)

    assert report["overall"] >= 0.9
    assert report["scores"]["safety"] == 1.0
    assert report["scores"]["rc2_compatibility"] == 1.0
