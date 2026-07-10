from __future__ import annotations

from orchestration.runtime.rc3_operator_pilot_freeze_readiness import (
    build_rc3_operator_pilot_freeze_readiness,
)


def test_rc3_protocol_records_all_phases_without_enabling_execution() -> None:
    report = build_rc3_operator_pilot_freeze_readiness(write_reports=False)

    assert report["phase_count"] == 24
    assert report["phases"][0]["name"] == "Foundation Lock"
    assert report["phases"][-1]["name"] == "RC3 Freeze Readiness"
    assert report["pilot_constraints"]["unattended_execution_allowed"] is False
    assert report["pilot_constraints"]["automatic_commit_allowed"] is False
    assert report["pilot_constraints"]["automatic_push_allowed"] is False
    assert report["pilot_constraints"]["automatic_plugin_activation_allowed"] is False
    assert report["pilot_sequence_safe_by_design"] is True


def test_rc3_pilot_requires_review_for_mutation_boundary_steps() -> None:
    report = build_rc3_operator_pilot_freeze_readiness(write_reports=False)
    pilot_steps = {item["name"]: item for item in report["pilot_sequence"]}

    assert pilot_steps["Sandbox coding task"]["requires_operator_review"] is True
    assert pilot_steps["Operator-approved integration"]["requires_operator_review"] is True
    assert pilot_steps["Plugin activation"]["requires_operator_review"] is True
    assert pilot_steps["Controlled forgetting test"]["requires_operator_review"] is True
    assert all(item["mutates_production"] is False for item in pilot_steps.values())


def test_rc3_freeze_is_not_ready_before_implementation_evidence() -> None:
    report = build_rc3_operator_pilot_freeze_readiness(write_reports=False)

    assert report["freeze_recommendation"] == "NOT_READY_FOR_RC3_FREEZE_IMPLEMENT_RC3_A_THROUGH_RC3_G_FIRST"
    assert report["freeze_criteria_summary"]["currently_passed"] == 0
    assert report["freeze_criteria_summary"]["not_started"] > 0
    assert report["recommendation"] == "READY_TO_BEGIN_RC3_A_GOAL_AND_PLANNING_SCAFFOLD"


def test_rc3_protocol_preserves_safety_and_delta75_boundary() -> None:
    report = build_rc3_operator_pilot_freeze_readiness(write_reports=False)
    safety = report["safety"]

    assert safety["training_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["autonomous_action_performed"] is False
    assert safety["automatic_commit_performed"] is False
    assert safety["automatic_push_performed"] is False
    assert safety["automatic_plugin_activation_performed"] is False
    assert safety["production_secret_access_performed"] is False
    assert safety["delta_75_interaction_performed"] is False
