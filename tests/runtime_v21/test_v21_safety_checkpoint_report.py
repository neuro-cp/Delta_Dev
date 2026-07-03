from __future__ import annotations

from orchestration.runtime.v21_safety_checkpoint_report import build_v21_safety_checkpoint, validate_v21_safety_checkpoint, write_v21_safety_checkpoint_report


def test_checkpoint_lists_v21_phases():
    data = build_v21_safety_checkpoint()
    assert "V2.1A Web / Localhost Review UI Prototype" in data["completed_phases"]
    assert "V2.1F V2.1 Safety Checkpoint Report" in data["completed_phases"]


def test_safety_invariants_false():
    data = build_v21_safety_checkpoint()
    assert validate_v21_safety_checkpoint(data)


def test_status_preserves_model_b_hyb1():
    data = build_v21_safety_checkpoint()
    assert data["status"]["model_b"] == "default_unchanged"
    assert data["status"]["hyb1"] == "dormant_env_gated_report_only"


def test_report_generation():
    data = write_v21_safety_checkpoint_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V22_LOCALHOST_UI_MUTATION_BRIDGE_OR_CONTROLLED_RECALL_EXPANSION"
