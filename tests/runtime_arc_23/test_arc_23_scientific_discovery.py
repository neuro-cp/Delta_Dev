import importlib
import json

MODULE_NAME = "orchestration.runtime.arc_23_scientific_discovery"


def module():
    return importlib.import_module(MODULE_NAME)


def test_arc_23_object_construction():
    m = module()
    objects = m.build_primitives()
    assert len(objects) == 8
    assert set(m.PRIMITIVE_NAMES) == {'ExperimentProposal', 'ResearchProgram', 'PredictionEngine', 'ValidationPlanner', 'HypothesisPortfolio', 'ExperimentalDesign', 'ResultComparison', 'DiscoveryAudit'}
    assert all(obj.as_dict()["review_state"] == "review_required" for obj in objects)


def test_arc_23_validation_and_safety_flags():
    m = module()
    validation = m.validate_arc()
    safety = m.arc_safety_invariants()
    assert validation["valid"] is True
    assert validation["no_mutation"] is True
    assert validation["no_provider_calls"] is True
    assert validation["no_scheduler"] is True
    assert validation["no_execution"] is True
    assert validation["no_training"] is True
    assert safety["model_b_default"] == "unchanged"
    assert safety["hyb1"] == "dormant_env_gated"
    assert safety["training_performed"] is False
    assert safety["provider_authority_granted"] is False
    assert safety["scheduler_started"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["knowledge_mutation_performed"] is False


def test_arc_23_demo_and_report_payload_json_serializable():
    m = module()
    demo = m.demo_scenario()
    payload = m.report_payload()
    assert demo["simulated_only"] is True
    assert demo["live_behavior_activated"] is False
    assert payload["status"] == "implemented_module_simulated_only"
    assert payload["audit"]["authority_safe"] is True
    json.dumps(payload, sort_keys=True)


def test_arc_23_write_report_outputs_review_only_artifacts():
    m = module()
    payload = m.write_report()
    assert payload["validation"]["valid"] is True
    assert payload["safety"]["hidden_write_performed"] is False
