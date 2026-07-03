from orchestration.runtime.v30_safety_checkpoint import build_v30_safety_checkpoint


def test_v30_safety_checkpoint_preserves_frozen_boundaries():
    data = build_v30_safety_checkpoint()
    assert data["model_b_default"] == "unchanged"
    assert data["hyb1"] == "dormant_env_gated_shadow_only"
    assert data["training"] == "disabled"
    assert data["provider_calls"] == "disabled"
    assert data["memory_writes"] == "disabled"
    assert data["scheduler"] == "disabled"
    assert data["action_execution"] == "disabled"
    assert all(value is False for value in data["safety_invariants"].values())
