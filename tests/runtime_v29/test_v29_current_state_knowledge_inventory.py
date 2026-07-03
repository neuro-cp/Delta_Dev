from orchestration.runtime.v29_current_state_knowledge_inventory import (
    build_current_state_inventory,
    validate_current_state_inventory_safe,
)


def test_current_state_inventory_describes_v28_v29_without_authority():
    data = build_current_state_inventory()

    assert validate_current_state_inventory_safe(data)
    assert data["phase"] == "Runtime V2.9"
    assert data["current_default"] == "Model B"
    assert data["hyb1_status"] == "dormant_env_gated_shadow_only"
    assert "V2.8" in data["phase_summaries"]
    assert data["safety_invariants"]["training_performed"] is False
    assert data["safety_invariants"]["provider_call_performed"] is False
