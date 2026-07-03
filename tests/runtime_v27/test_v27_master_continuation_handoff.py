from orchestration.runtime.v27_master_continuation_handoff import (
    build_master_continuation_handoff,
    validate_master_continuation_handoff_safe,
)


def test_master_continuation_handoff_preserves_safety_state():
    data = build_master_continuation_handoff()

    assert validate_master_continuation_handoff_safe(data)
    assert data["current_default"] == "Model B"
    assert data["training"] == "not_performed"
    assert data["hyb1"] == "dormant_env_gated_shadow_only"
