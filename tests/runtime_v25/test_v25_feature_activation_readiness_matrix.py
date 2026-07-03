from orchestration.runtime.v25_feature_activation_readiness_matrix import (
    build_feature_activation_readiness_matrix,
    validate_feature_activation_matrix_safe,
)


def test_feature_activation_matrix_activates_nothing():
    data = build_feature_activation_readiness_matrix()

    assert validate_feature_activation_matrix_safe(data)
    assert data["phase"] == "Runtime V2.5B"
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_TRAINING_DATASET_EXPORT_TRIAL"
    assert all(not feature["activated"] for feature in data["matrix"].values())
    assert data["invariant_flags"]["readiness_only"] is True
    assert data["invariant_flags"]["feature_activated"] is False
    assert data["invariant_flags"]["training_activated"] is False
