from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orchestration.runtime import rc4_governed_action_runtime as rc4
from orchestration.runtime.rc4_ui_capability_adapter import (
    RC4_PANEL_ORDER,
    build_rc4_ui_integration_report,
    build_rc4_ui_snapshot,
    render_rc4_panel,
    validate_rc4_ui_snapshot,
)


def test_rc4_authorization_rejects_vague_expired_revoked_and_protected_targets():
    report = rc4.run_authorization_benchmark()
    assert report["passed"] is True
    assert report["outcomes"]["valid"] == "AUTHORIZED"
    assert report["outcomes"]["vague"] == "DENIED"
    assert report["outcomes"]["expired"] == "EXPIRED"
    assert report["outcomes"]["revoked"] == "REVOKED"
    assert report["outcomes"]["protected_target"] == "PROHIBITED_TARGET"


def test_rc4_authorization_scope_does_not_inherit_push_or_live_write():
    scope = rc4.make_scope(allowed_commands=("python_compile",), allowed_tools=("filesystem_read",))
    request = rc4.make_execution_request(
        "Apply exact fixture patch.",
        requested_commands=("python_compile",),
        requested_tools=("filesystem_read", "git_fixture_mutation"),
    )
    decision = rc4.evaluate_authorization(rc4.make_authorization(request, rc4.make_permission_grant(scope)))
    assert decision.outcome == "PROHIBITED_TOOL"
    assert "tool_out_of_scope" in decision.reasons


def test_rc4_patch_validation_rejects_unsafe_capability_and_secret_patterns():
    scope = rc4.make_scope()
    unsafe = rc4.build_candidate_patch(base_text="x=1\n", new_text="import os\n" + "os" + ".system('x')\n")
    unsafe_artifact = rc4.validate_patch(unsafe, scope)
    secret = rc4.build_candidate_patch(
        base_text="x=1\n",
        new_text=("OPENAI" + "_API_KEY='sk" + "-abc12345678901234567890'\n"),
    )
    secret_artifact = rc4.validate_patch(secret, scope)
    assert unsafe_artifact.validation.valid is False
    assert unsafe_artifact.validation.unsafe_capability_detected is True
    assert secret_artifact.validation.valid is False
    assert secret_artifact.validation.secret_pattern_detected is True


def test_rc4_disposable_execution_runs_and_tears_down_without_live_mutation():
    episode = rc4.build_successful_fixture_episode()
    assert episode.decision.outcome == "AUTHORIZED"
    assert episode.execution_result.outcome == "EXECUTION_SUCCEEDED"
    assert episode.execution_result.evidence.teardown_verified is True
    assert episode.execution_result.safety["live_repository_mutation_performed"] is False
    assert episode.integration_candidate.permission_status["push"] == "disabled"


def test_rc4_repair_rollback_and_recovery_are_bounded():
    report = rc4.run_repair_and_rollback_benchmark()
    assert report["passed"] is True
    assert report["checks"]["repair_bounded"] is True
    assert report["checks"]["rollback_verified"] is True
    assert report["checks"]["partial_failures_reported"] is True


def test_rc4_tool_orchestration_blocks_unknown_dynamic_tools():
    report = rc4.run_tool_orchestration_benchmark()
    assert report["passed"] is True
    outcomes = {item["tool_identifier"]: item["outcome"] for item in report["results"]}
    assert outcomes["dynamic_tool_install"] == "TOOL_UNKNOWN"


def test_rc4_adversarial_suite_covers_required_negative_cases():
    report = rc4.run_adversarial_evaluation()
    assert report["passed"] is True
    assert report["case_count"] >= 38
    cases = {case["case"] for case in report["cases"]}
    assert "network attempt" in cases
    assert "unauthorized push" in cases
    assert "protected repository access attempt" in cases


def test_rc4_reports_end_with_operator_pilot_freeze_blocker_only(tmp_path):
    reports = rc4.run_all_rc4_reports(write_reports=False)
    final = reports["RC4_FREEZE_READINESS_FINAL"]
    assert final["freeze_status"] == "RC4_FREEZE_PENDING_REAL_OPERATOR_PILOT"
    assert final["freeze_blockers"] == ("operator_pilot_evidence",)
    assert final["safety"]["provider_calls_performed"] is False
    assert final["safety"]["automatic_push_performed"] is False


def test_rc4_ui_panels_are_read_only_and_honest():
    rc4.run_all_rc4_reports(write_reports=True)
    snapshot = build_rc4_ui_snapshot()
    validation = validate_rc4_ui_snapshot(snapshot)
    assert tuple(snapshot["panels"]) == RC4_PANEL_ORDER
    assert validation["passed"] is True
    assert all(value is False for value in snapshot["actions_enabled"].values())
    assert "Safety:" in render_rc4_panel("Authorization", snapshot)
    report = build_rc4_ui_integration_report(write_reports=False)
    assert report["freeze_status"] == "RC4_FREEZE_PENDING_REAL_OPERATOR_PILOT"


def test_rc4_explicit_expiration_uses_current_time():
    scope = rc4.make_scope()
    grant = rc4.make_permission_grant(scope, seconds=1)
    request = rc4.make_execution_request("Apply exact fixture patch.")
    decision = rc4.evaluate_authorization(
        rc4.make_authorization(request, grant),
        now=datetime.now(UTC) + timedelta(seconds=5),
    )
    assert decision.outcome == "EXPIRED"
