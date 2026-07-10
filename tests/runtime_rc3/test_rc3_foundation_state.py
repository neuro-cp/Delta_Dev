from __future__ import annotations

from orchestration.runtime.rc3_foundation_state import (
    SAFETY_DEFAULTS,
    build_rc3_foundation_episode,
    build_rc3_milestone_1_foundation_report,
)


def test_rc3_foundation_episode_is_ephemeral_and_non_executing() -> None:
    episode = build_rc3_foundation_episode(
        "Help me design RC3. Do not touch DELTA-75 and do not execute plans."
    )

    assert episode.persistence_status == "ephemeral"
    assert episode.goal_frame.persistence_status == "ephemeral"
    assert episode.plan_frame.persistence_status == "ephemeral"
    assert episode.plan_frame.execution_authorized is False
    assert all(step.non_executing for step in episode.plan_frame.steps)
    assert episode.progress.status == "needs_evidence"


def test_rc3_goal_frame_preserves_prohibitions_and_constraints() -> None:
    episode = build_rc3_foundation_episode(
        "Build a plan for RC3, but do not execute plans, do not activate plugins, and do not touch DELTA-75."
    )

    assert "preserve explicit prohibitions" in episode.goal_frame.constraints
    assert "do not execute plans" in episode.goal_frame.prohibited_actions
    assert "do not activate plugins" in episode.goal_frame.prohibited_actions
    assert "do not interact with DELTA-75" in episode.goal_frame.prohibited_actions
    assert episode.arbitration.operator_approval_required_before_action is True


def test_rc3_introspection_is_evidence_based() -> None:
    episode = build_rc3_foundation_episode("Design RC3 foundation state.")

    assert episode.introspection.fabricated_self_state is False
    assert episode.introspection.hidden_state_detected is False
    assert episode.introspection.evidence_sources
    assert all("claim" in claim and "evidence" in claim for claim in episode.introspection.claims)


def test_rc3_capability_gap_prevents_direct_jump_to_sandbox_or_plugin() -> None:
    episode = build_rc3_foundation_episode(
        "Design RC3 goals, planning, introspection, progress evaluation, and capability gap analysis."
    )

    assert episode.capability_gap.proposal_needed is True
    assert episode.capability_gap.plugin_needed is False
    assert episode.capability_gap.sandbox_needed is False
    assert "sandbox runtime" in episode.capability_gap.missing_capabilities
    assert "plugin activation workflow" in episode.capability_gap.missing_capabilities


def test_rc3_foundation_safety_defaults_are_false() -> None:
    episode = build_rc3_foundation_episode("Help me design RC3 safely.")

    assert set(episode.safety) == set(SAFETY_DEFAULTS)
    assert all(value is False for value in episode.safety.values())
    assert all(value is False for value in episode.goal_frame.safety.values())
    assert all(value is False for value in episode.plan_frame.safety.values())


def test_rc3_foundation_report_classifies_legacy_code_without_activation() -> None:
    report = build_rc3_milestone_1_foundation_report(write_reports=False)

    assert report["validation_claims"]["objects_ephemeral"] is True
    assert report["validation_claims"]["no_execution_authorized"] is True
    assert report["validation_claims"]["safety_all_false"] is True
    assert report["legacy_code_classification"]["orchestration.agency.goal_system"] == "legacy_reference_only_for_now"
    assert report["recommendation"] == "READY_FOR_FOCUSED_RC3_A_GOAL_AND_PLANNING_SCAFFOLD_IMPLEMENTATION"
