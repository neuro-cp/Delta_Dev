import importlib
import json

MODULE = "orchestration.runtime.deepening_d_executive_planner"


def m():
    return importlib.import_module(MODULE)


def test_deepening_d_executive_planner_objects_validation_and_safety():
    module = m()
    objects = module.build_objects()
    validation = module.validate_module().as_dict()
    safety = module.safety_invariants()
    assert len(objects) == 5
    assert validation["valid"] is True
    assert validation["training_performed"] is False
    assert safety["model_b_default"] == "unchanged"
    assert safety["hyb1"] == "dormant_env_gated"
    assert safety["training_performed"] is False
    assert safety["provider_authority_granted"] is False
    assert safety["autonomous_browsing_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["knowledge_mutation_performed"] is False


def test_deepening_d_executive_planner_audit_demo_json_graph_and_report():
    module = m()
    payload = module.report_payload()
    assert payload["audit"]["safety_verified"] is True
    assert payload["demo"]["simulated_only"] is True
    assert payload["demo"]["live_behavior_activated"] is False
    assert payload["graph_export_metadata"]["serialized_only"] is True
    assert payload["capability_state"] == "gated_future_capability"
    assert module.write_report()["status"] == "implemented_module_simulated_only"
    json.dumps(payload, sort_keys=True)

