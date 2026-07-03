from orchestration.runtime.v25_training_readiness_audit import (
    build_training_readiness_audit,
    validate_training_readiness_audit_safe,
)


def test_training_readiness_is_report_only_and_blocked():
    data = build_training_readiness_audit()

    assert validate_training_readiness_audit_safe(data)
    assert data["phase"] == "Runtime V2.5A"
    assert data["outcome"] == "report_only_no_training"
    assert data["final_recommendation"] == "PROCEED_FEATURE_ACTIVATION_READINESS_MATRIX"
    assert data["blockers"]
    assert data["invariant_flags"]["report_only"] is True
    assert data["invariant_flags"]["training_performed"] is False
    assert data["invariant_flags"]["dataset_exported"] is False
