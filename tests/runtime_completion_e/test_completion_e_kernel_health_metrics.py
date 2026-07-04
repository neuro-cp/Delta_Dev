from orchestration.runtime import completion_e_kernel_health_metrics as module


def test_completion_e_kernel_health_metrics_objects_validation_and_safety():
    objects = module.build_objects()
    assert len(objects) == 6
    assert all(obj.authority == "advisory_only" for obj in objects)
    assert all(obj.mutation_performed is False for obj in objects)
    validation = module.validate_module().as_dict()
    assert validation["valid"] is True
    assert validation["object_count"] == 6
    assert validation["training_performed"] is False
    safety = module.safety_invariants()
    assert safety["model_b_default"] == "unchanged"
    assert safety["hyb1"] == "dormant_env_gated"
    assert safety["training_performed"] is False
    assert safety["provider_authority_granted"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["knowledge_mutation_performed"] is False


def test_completion_e_kernel_health_metrics_audit_demo_json_graph_markdown_and_report():
    audit = module.audit_summary().as_dict()
    assert audit["safety_verified"] is True
    demo = module.demo_payload()
    assert demo["simulated_only"] is True
    assert demo["live_behavior_activated"] is False
    payload = module.json_export()
    assert payload["capability_state"] == "gated_future_capability"
    assert payload["metrics"]["authority_score"] == 0
    graph = module.graph_export_metadata()
    assert graph["serialized_only"] is True
    assert len(graph["nodes"]) == 6
    assert module.markdown_export().startswith("# ")
    report = module.write_report()
    assert report["module_id"] == module.MODULE_ID
