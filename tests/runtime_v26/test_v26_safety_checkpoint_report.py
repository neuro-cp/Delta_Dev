from orchestration.runtime.v26_safety_checkpoint_report import (
    build_v26_safety_checkpoint,
    validate_v26_safety_checkpoint,
)


def test_v26_safety_checkpoint_preserves_all_safety_invariants():
    data = build_v26_safety_checkpoint()

    assert validate_v26_safety_checkpoint(data)
    assert data["final_recommendation"] == "PROCEED_V27_FEATURE_ACTIVATION_DRY_RUN_TRIAL"
    assert data["status"]["model_b"] == "default_unchanged"
    assert data["status"]["hyb1"] == "dormant_env_gated_not_promoted"
