from __future__ import annotations

from orchestration.runtime.v22_safety_closure_report import build_v22_safety_closure, validate_v22_safety_closure, write_v22_safety_closure_report


def test_closure_lists_v22_phases():
    data = build_v22_safety_closure()
    assert "V2.2A Localhost UI Mutation Bridge, Explicit Approval Only" in data["completed_phases"]
    assert "V2.2F V2.2 Safety Closure Report" in data["completed_phases"]


def test_safety_invariants_false():
    data = build_v22_safety_closure()
    assert validate_v22_safety_closure(data)


def test_model_b_and_hyb1_status():
    data = build_v22_safety_closure()
    assert data["status"]["model_b"] == "default_unchanged"
    assert data["status"]["hyb1"] == "dormant_env_gated_shadow_design_only"


def test_report_generation():
    data = write_v22_safety_closure_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V23_HYB1_SHADOW_SIMULATION_OR_LOCALHOST_WRITE_EXECUTION_BRIDGE"
