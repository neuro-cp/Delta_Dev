from orchestration.runtime.v24_safety_closure_report import build_v24_safety_closure, validate_v24_safety_closure, write_v24_safety_closure_report


def test_closure_lists_v24_phases():
    data = build_v24_safety_closure()
    assert len(data["completed_phases"]) == 6
    assert "V2.4A Localhost Full Review Console UX" in data["completed_phases"]


def test_safety_invariants_false():
    data = build_v24_safety_closure()
    assert validate_v24_safety_closure(data)


def test_status_preserves_defaults():
    data = build_v24_safety_closure()
    assert data["status"]["model_b"] == "default_unchanged"
    assert "dormant" in data["status"]["hyb1"]


def test_report_generation():
    data = write_v24_safety_closure_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_TRAINING_READINESS_AUDIT_OR_FEATURE_ACTIVATION_READINESS_MATRIX"

