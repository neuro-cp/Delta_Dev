from orchestration.runtime.v26_feature_activation_gate_console import (
    build_feature_activation_gate_console,
    validate_feature_activation_gate_console_safe,
)


def test_feature_activation_gate_console_changes_no_gates():
    data = build_feature_activation_gate_console()

    assert validate_feature_activation_gate_console_safe(data)
    assert data["gates"]["training"] == "blocked"
    assert data["gates"]["hyb1_shadow"] == "env_gated_dormant"
    assert data["active_gate_changes"] == []
