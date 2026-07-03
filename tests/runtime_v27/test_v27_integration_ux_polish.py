from orchestration.runtime.v27_integration_ux_polish import (
    build_integration_ux_polish,
    validate_integration_ux_polish_safe,
)


def test_integration_ux_polish_is_report_only():
    data = build_integration_ux_polish()

    assert validate_integration_ux_polish_safe(data)
    assert data["mode"] == "ux_report_only"
    assert data["active_behavior_changes"] == []
