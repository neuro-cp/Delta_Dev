from orchestration.runtime.v27_feature_activation_dry_run_trial import (
    build_feature_activation_dry_run_trial,
    validate_feature_activation_dry_run_trial_safe,
)


def test_feature_activation_dry_run_activates_nothing():
    data = build_feature_activation_dry_run_trial()

    assert validate_feature_activation_dry_run_trial_safe(data)
    assert data["activated_features"] == []
    assert data["evaluated_gates"]["training"] == "would_remain_blocked"
