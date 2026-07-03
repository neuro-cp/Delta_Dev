from __future__ import annotations

from orchestration.runtime.v20_safety_checkpoint_report import build_v20_safety_checkpoint, validate_v20_safety_checkpoint, write_v20_safety_checkpoint_report


def test_checkpoint_lists_completed_phases():
    data = build_v20_safety_checkpoint()
    assert "V2.0A Local DELTA UX Consolidation" in data["completed_phases"]
    assert "V2.0H V2.0 Safety Checkpoint Report" in data["completed_phases"]


def test_invariants_false():
    data = build_v20_safety_checkpoint()
    assert validate_v20_safety_checkpoint(data)


def test_status_preserves_model_b_and_hyb1():
    data = build_v20_safety_checkpoint()
    assert data["status"]["model_b"] == "default_unchanged"
    assert data["status"]["hyb1"] == "dormant_env_gated"


def test_report_generation():
    data = write_v20_safety_checkpoint_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V21_WEB_LOCALHOST_REVIEW_UI_OR_CONTROLLED_GENERAL_MEMORY_EXPANSION"
