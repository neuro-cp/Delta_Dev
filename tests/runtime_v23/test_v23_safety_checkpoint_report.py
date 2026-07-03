from orchestration.runtime.v23_safety_checkpoint_report import build_v23_safety_checkpoint, validate_v23_safety_checkpoint, write_v23_safety_checkpoint_report


def test_checkpoint_lists_v23_phases():
    data = build_v23_safety_checkpoint()
    assert len(data["completed_phases"]) == 6
    assert "V2.3A HYB1 Shadow Trial Simulation, Opt-In Only" in data["completed_phases"]


def test_safety_invariants_false():
    data = build_v23_safety_checkpoint()
    assert validate_v23_safety_checkpoint(data)


def test_status_preserves_model_b_hyb1():
    data = build_v23_safety_checkpoint()
    assert data["status"]["model_b"] == "default_unchanged"
    assert "dormant" in data["status"]["hyb1"]


def test_report_generation():
    data = write_v23_safety_checkpoint_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V24_LOCALHOST_FULL_REVIEW_CONSOLE_UX"

