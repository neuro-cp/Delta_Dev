from __future__ import annotations

from orchestration.runtime import rc45_operator_mimic_calibration as rc45
from orchestration.runtime import rc5_ui_capability_adapter as rc5_ui


def test_operator_mimic_scenarios_are_realistic_developer_rehearsal_only():
    scenarios = rc45.build_operator_mimic_scenarios()
    categories = {scenario.category for scenario in scenarios}

    assert 50 <= len(scenarios) <= 100
    assert all(scenario.evidence_class == rc45.EVIDENCE_CLASS for scenario in scenarios)
    assert len(categories) >= 40
    assert any(s.category == "consultation_safety" for s in scenarios)
    assert any(s.category == "interruption" for s in scenarios)
    assert any(s.category == "false_positive" for s in scenarios)


def test_integrated_cycle_rejects_unsafe_advice_and_preserves_safety():
    scenario = next(s for s in rc45.build_operator_mimic_scenarios() if s.category == "consultation_safety")
    cycle = rc45.run_integrated_cycle(scenario)

    assert cycle.evidence_class == rc45.EVIDENCE_CLASS
    assert cycle.unsafe_advice_rejected is True
    assert all(value is False for value in cycle.safety.values())
    assert cycle.rc4_artifacts["governance"].startswith("operator review")


def test_operator_mimic_reports_do_not_claim_freeze_or_real_pilot():
    reports = rc45.run_operator_mimic_pilot(write_reports=False)
    readiness = reports["RC45_FREEZE_READINESS_REVIEW"]
    consolidated = reports["RC45_OPERATOR_MIMIC_CONSOLIDATED"]

    assert consolidated["evidence_class"] == rc45.EVIDENCE_CLASS
    assert consolidated["scenario_count"] >= 50
    assert readiness["rc4_recommendation"] == "RC4_FREEZE_PENDING_REAL_OPERATOR_PILOT"
    assert readiness["rc5_recommendation"] == "RC5_FREEZE_PENDING_REAL_OPERATOR_PILOT"
    assert readiness["recommendation"] == "READY_FOR_REAL_OPERATOR_PILOT_NOT_FREEZE"


def test_rc5_ui_surfaces_mimic_calibration_as_rehearsal_only():
    rc45.run_operator_mimic_pilot(write_reports=True)
    snapshot = rc5_ui.build_rc5_ui_snapshot()
    validation = rc5_ui.validate_rc5_ui_snapshot(snapshot)

    assert "Mimic Calibration" in snapshot["panels"]
    assert snapshot["panels"]["Mimic Calibration"]["authority"] == "developer_rehearsal_only"
    assert "not real operator-pilot evidence" in snapshot["panels"]["Mimic Calibration"]["warnings"][0]
    assert validation["passed"] is True
