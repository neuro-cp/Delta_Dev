from orchestration.runtime.v25_safety_checkpoint_report import (
    build_v25_safety_checkpoint,
    validate_v25_safety_checkpoint,
)


def test_v25_safety_checkpoint_preserves_invariants():
    data = build_v25_safety_checkpoint()

    assert validate_v25_safety_checkpoint(data)
    assert data["phase"] == "Runtime V2.5F"
    assert data["final_recommendation"] == "PROCEED_V26_TRAINING_DATASET_REVIEW_UI"
    assert data["status"]["model_b"] == "default_unchanged"
    assert data["status"]["hyb1"] == "dormant_env_gated_not_promoted"
    assert all(value is False for value in data["safety_invariants"].values())
