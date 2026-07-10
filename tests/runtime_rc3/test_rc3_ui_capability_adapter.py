from orchestration.runtime.rc3_ui_capability_adapter import (
    PANEL_ORDER,
    build_rc3_ui_integration_report,
    build_rc3_ui_snapshot,
    render_rc3_panel,
    validate_rc3_ui_snapshot,
)


def test_rc3_ui_snapshot_has_all_capability_panels_and_no_action_controls():
    snapshot = build_rc3_ui_snapshot()
    validation = validate_rc3_ui_snapshot(snapshot)
    assert snapshot["coverage"]["all_panels_present"] is True
    assert tuple(snapshot["panels"]) == PANEL_ORDER
    assert all(value is False for value in snapshot["actions_enabled"].values())
    assert validation["passed"] is True


def test_rc3_ui_distinguishes_pilot_evidence_from_freeze_status():
    snapshot = build_rc3_ui_snapshot()
    pilot = snapshot["panels"]["Pilot Evidence"]
    freeze = snapshot["panels"]["Freeze Readiness"]
    assert "actual_operator_pilot_evidence" in pilot["detail"]
    assert pilot["status"] in ("SIMULATED_FIXTURE_EVIDENCE", "REAL_OPERATOR_EVIDENCE")
    if pilot["detail"]["actual_operator_pilot_evidence"] is False:
        assert freeze["detail"]["freeze_status"] != "READY_FOR_RC3_FREEZE"


def test_rc3_panel_rendering_is_human_readable_and_warning_bounded():
    snapshot = build_rc3_ui_snapshot()
    text = render_rc3_panel("Governance", snapshot)
    assert "Governance" in text
    assert "Safety:" in text
    assert "does not execute plans" in text


def test_rc3_ui_report_generation_is_read_only():
    report = build_rc3_ui_integration_report(write_reports=False)
    assert report["panel_coverage"]["all_panels_present"] is True
    assert all(value is False for value in report["actions_enabled"].values())
    assert report["recommendation"] in (
        "READY_FOR_RC3_FREEZE",
        "CONTINUE_RC3_UI_CALIBRATION",
        "BLOCKED_BY_UI_CAPABILITY_GAPS",
        "BLOCKED_BY_UNRESOLVED_OPERATOR_FINDINGS",
    )
