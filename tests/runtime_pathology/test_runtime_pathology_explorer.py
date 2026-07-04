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
    assert first["final_recommendation"] in {
        "PROCEED_VERTICAL_INTEGRATION_PATHOLOGY_REDUCTION",
        "PROCEED_DOCUMENT_TO_AUDIT_VERTICAL_SLICE",
        "PROCEED_KERNEL_ROUTING_ENFORCEMENT",
        "PROCEED_SUBSTRATE_QUERY_ADAPTER",
        "PROCEED_UNIFIED_PROPOSAL_REVIEW_STATE_MACHINE",
        "PROCEED_CENTRAL_RUNTIME_ARTIFACT_REGISTRY",
        "PROCEED_RC1_MANUAL_SCENARIO_VALIDATION",
        "PROCEED_MANUAL_RC1_VALIDATION_NO_LIVE_CAPABILITIES",
    }
    assert first["overall_runtime_maturity_estimate"]["estimated_percent"] >= 68
