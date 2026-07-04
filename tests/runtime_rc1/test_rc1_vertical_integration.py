from orchestration.runtime.rc1_vertical_integration import build_rc1_vertical_trace, write_rc1_reports
from orchestration.runtime.v37_capability_registry import CognitiveCapabilityRegistry
from orchestration.runtime.v38_dynamic_pipeline_builder import build_dynamic_pipeline


def test_rc1_vertical_trace_is_kernel_routed_and_transaction_wrapped():
    payload = build_rc1_vertical_trace()
    assert payload["scorecard"]["kernel_routed"] is True
    assert payload["scorecard"]["transaction_wrapped"] is True
    assert all(step["mutating"] is False for step in payload["trace_steps"])


def test_rc1_vertical_trace_links_audit_graph():
    payload = build_rc1_vertical_trace()
    graph = payload["audit_graph"]
    assert payload["scorecard"]["audit_graph_linked"] is True
    assert len(graph["nodes"]) == len(payload["trace_steps"])
    assert len(graph["edges"]) == len(payload["trace_steps"]) - 1


def test_rc1_lifecycle_ownership_has_no_none_roles():
    payload = build_rc1_vertical_trace()
    required = ("creator", "owner", "validator", "consumer", "auditor", "rollback_owner", "explains")
    assert payload["lifecycle_owners"]
    for owner in payload["lifecycle_owners"]:
        assert all(owner[field] for field in required)


def test_dynamic_pipeline_recognizes_semantic_consolidation_scenario():
    pipeline = build_dynamic_pipeline("Why did Project Atlas fail after semantic consolidation?", CognitiveCapabilityRegistry())
    capabilities = [step["capability"] for step in pipeline.as_dict()["steps"]]
    assert "semantic_consolidation_cycle" in capabilities
    assert "vertical_runtime_trace" in capabilities
    assert "audit_graph_review" in capabilities


def test_rc1_trace_preserves_global_safety_flags():
    payload = build_rc1_vertical_trace()
    safety = payload["safety"]
    assert safety["model_b_default"] == "unchanged"
    assert safety["hyb1"] == "dormant_env_gated"
    assert safety["training_performed"] is False
    assert safety["provider_call_performed"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["knowledge_mutation_performed"] is False


def test_rc1_grounded_answer_uses_consolidated_records_and_uncertainty():
    payload = build_rc1_vertical_trace()
    assert payload["scorecard"]["answer_grounded_in_consolidated_records"] is True
    assert payload["scorecard"]["unsupported_uncertainty_identified"] is True
    answer = payload["e2e_cycle"]["grounded_answer"]
    assert answer["supporting_evidence_ids"]
    assert answer["uncertainty"]
    assert answer["unsupported_claims_refused"]


def test_rc1_reports_are_generated():
    payload = write_rc1_reports()
    assert payload["final_recommendation"] == "PROCEED_DOCUMENT_TO_AUDIT_VERTICAL_SLICE"
    assert payload["scorecard"]["estimated_runtime_maturity"] >= 76
