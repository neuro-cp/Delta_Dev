from tools.runtime_pathology_explorer import build_master


def test_pathology_explorer_is_deterministic_and_report_only():
    first = build_master()
    second = build_master()
    assert first == second
    assert first["runtime_module_count"] > 0
    assert first["architectural_debt_count"] > 0
    assert first["dead_system_count"] >= 0
    assert first["safety"]["training_performed"] is False
    assert first["safety"]["provider_authority_granted"] is False
    assert first["safety"]["provider_call_performed"] is False
    assert first["safety"]["memory_mutation_performed"] is False
    assert first["safety"]["knowledge_mutation_performed"] is False
    assert first["safety"]["hyb1"] == "dormant_env_gated"
    assert first["final_recommendation"] == "PROCEED_VERTICAL_INTEGRATION_PATHOLOGY_REDUCTION"
