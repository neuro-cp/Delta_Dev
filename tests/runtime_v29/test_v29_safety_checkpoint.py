from orchestration.runtime.v29_safety_checkpoint import (
    build_v29_safety_checkpoint,
    validate_v29_safety_checkpoint_safe,
)


def test_v29_safety_checkpoint_preserves_defaults():
    data = build_v29_safety_checkpoint()

    assert validate_v29_safety_checkpoint_safe(data)
    assert data["safety_state"]["model_b_default"] == "unchanged"
    assert data["safety_state"]["hyb1"] == "dormant_env_gated_shadow_only"
    assert data["safety_state"]["training"] == "disabled"
