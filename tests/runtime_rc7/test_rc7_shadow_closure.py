from __future__ import annotations

import json

from orchestration.runtime.rc7_shadow_closure import (
    campaign_drift_sweep,
    dashboard_sweep,
    determinism_sweep,
    evidence_honesty_sweep,
    final_adversarial_sweep,
    final_campaign_calibration,
    final_governance_audit,
    forward_transition_readiness,
    operator_workload_sweep,
    post_rc7_forward_direction,
    rc6_integration_boundary_sweep,
    rc7_boundary_payload,
    state_lifecycle_audit,
    stop_condition_sweep,
    write_reports,
)


def test_rc7_boundary_preserves_shadow_only_mode():
    boundary = rc7_boundary_payload()
    assert boundary["mode"] == "SHADOW_ONLY"
    assert boundary["recommendation"] == "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS"
    assert "autonomous_campaigns" in boundary["not_activated"]
    assert boundary["safety"]["campaign_execution_performed"] is False


def test_rc7_final_sweeps_pass_and_preserve_honest_evidence():
    assert state_lifecycle_audit()["passed"] is True
    assert stop_condition_sweep()["passed"] is True
    assert evidence_honesty_sweep()["passed"] is True
    assert operator_workload_sweep()["passed"] is True
    assert campaign_drift_sweep()["passed"] is True
    assert rc6_integration_boundary_sweep()["passed"] is True
    assert dashboard_sweep()["passed"] is True
    assert final_adversarial_sweep()["passed"] is True
    assert determinism_sweep()["passed"] is True


def test_rc7_final_reports_are_json_serializable_and_do_not_claim_freeze():
    governance = final_governance_audit()
    calibration = final_campaign_calibration()
    transition = forward_transition_readiness()
    direction = post_rc7_forward_direction()
    assert governance["recommendation"] == "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS"
    assert calibration["recommendation"] == "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS"
    assert transition["recommendation"] == "READY_FOR_FORWARD_TRANSITION_PLANNING"
    assert "real_long_horizon_operator_campaigns" in calibration["remaining_evidence_needed"]
    assert direction["recommended_next_direction"] == "B_RC8_REAL_RC7_OPERATOR_CAMPAIGN_PILOT"
    json.dumps(governance)
    json.dumps(calibration)
    json.dumps(transition)
    json.dumps(direction)


def test_rc7_write_reports_creates_required_payloads():
    reports = write_reports()
    assert reports["RC7_FINAL_SHADOW_READINESS"]["recommendation"] == "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS"
    assert reports["RC7_FINAL_GOVERNANCE_AUDIT"]["passed"] is True
    assert reports["RC7_FINAL_CAMPAIGN_CALIBRATION"]["passed"] is True
    assert reports["RC7_FORWARD_TRANSITION_READINESS"]["passed"] is True
    json.dumps(reports)
