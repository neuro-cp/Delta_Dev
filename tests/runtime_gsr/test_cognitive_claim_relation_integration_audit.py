import json

from orchestration.runtime.cognitive_claim_relation_integration_audit import (
    EXPECTED_AMENDMENT_DIGEST,
    EXPECTED_AMENDMENT_ID,
    EXPECTED_CONTRACT_DIGEST,
    EXPECTED_EVALUATOR_DIGEST,
    REQUIRED_REPORT_FILES,
    STATUS_EXCLUDED_PATH_REQUIRED,
    amendment_consequence,
    authority_inventory,
    classify_feasibility,
    consumer_inventory,
    dependent_work_inventory,
    deterministic_relation_types,
    first_missing_transition,
    integration_path_graph,
    minimum_pilot_boundary,
    operator_request_inventory,
    persistence_inventory,
    producer_inventory,
    relation_classifier_audit,
    required_information_matrix,
    restart_inventory,
    run_integration_audit_report,
    semantic_relation_types,
)


def test_first_missing_transition_is_exact_integration_gap():
    transition = first_missing_transition()
    assert transition["first_missing_transition"].startswith("GovernedClaimRecord and GovernedClaimRelationRecord exist")
    assert "actual cross-turn input event" in transition["required_transition"]


def test_producer_inventory_classifies_clean_and_excluded_paths():
    producers = producer_inventory()
    by_path = {item["path"]: item for item in producers}
    assert by_path["DELTA.py"]["excluded_file"] is True
    assert by_path["orchestration/runtime/live_competence_adapter.py"]["excluded_file"] is True
    assert by_path["orchestration/runtime/v31_learning_opportunity.py"]["can_create_claim_without_inventing_facts"] is False
    assert by_path["orchestration/runtime/v31_gated_integration.py"]["can_create_claim_without_inventing_facts"] is True


def test_consumer_inventory_detects_claim_currentness_gap():
    consumers = consumer_inventory()
    assert any(item["path"] == "DELTA.py" and item["excluded_file"] for item in consumers)
    assert all(item["operator_resolution_consulted"] is False for item in consumers)
    assert any(item["unresolved_contradiction_ignored"] is True for item in consumers)


def test_persistence_boundary_has_clean_candidate_but_no_general_schema_slot():
    persistence = persistence_inventory()
    assert any(item["safe_for_claim_relations_without_source_change"] is True for item in persistence)
    assert any("no claim_relation bundle slot" in item["schema_impact"] for item in persistence)


def test_classifier_distinguishes_deterministic_from_semantic_relation_types():
    audit = relation_classifier_audit()
    assert set(deterministic_relation_types()) == {
        "duplicate_restatement",
        "explicit_correction",
        "authority_revocation",
        "temporal_transition",
        "bounded_exception",
        "unrelated",
    }
    assert set(semantic_relation_types()) == {"direct_contradiction", "uncertain_conflict", "ambiguous_scope", "scoped_preference_update"}
    assert audit["model_called"] is False
    assert audit["classifier_mode_needed_later"] == "hybrid"


def test_feasibility_prefers_excluded_path_required_over_other_blocks():
    result = classify_feasibility()
    assert result["classification"] == "excluded_path_required"
    assert result["status"] == STATUS_EXCLUDED_PATH_REQUIRED


def test_feasibility_can_expose_other_classifications_for_audit_controls():
    clean_producer = [{"path": "clean.py", "can_create_claim_without_inventing_facts": True, "excluded_file": False}]
    clean_consumer = [{"path": "consumer.py", "excluded_file": False}]
    no_persistence = [{"path": "state.py", "safe_for_claim_relations_without_source_change": False}]
    assert classify_feasibility(clean_producer, clean_consumer, no_persistence)["classification"] == "persistence_boundary_required"
    clean_persistence = [{"path": "state.py", "safe_for_claim_relations_without_source_change": True}]
    assert classify_feasibility(clean_producer, clean_consumer, clean_persistence)["classification"] == "semantic_classifier_required"
    unsafe_producer = [{"path": "clean.py", "can_create_claim_without_inventing_facts": False, "excluded_file": False}]
    assert classify_feasibility(unsafe_producer, clean_consumer, clean_persistence)["classification"] == "upstream_provenance_required"


def test_integrity_audit_does_not_fail_only_because_branch_advanced():
    from orchestration.runtime.cognitive_claim_relation_integration_audit import _integrity_reasons

    reasons = _integrity_reasons(
        "post-transfer-checkpoint",
        EXPECTED_EVALUATOR_DIGEST,
        EXPECTED_AMENDMENT_ID,
        EXPECTED_AMENDMENT_DIGEST,
        EXPECTED_CONTRACT_DIGEST,
    )
    assert "head_mismatch" not in reasons
    assert reasons == ()


def test_authority_operator_request_and_workitem_adjacency_are_existing_but_unbound():
    assert any(item["supports_authorization"] for item in authority_inventory())
    assert any(item["consumed_once"] for item in authority_inventory())
    assert any(item["duplicate_suppression"] for item in operator_request_inventory())
    assert any(item["blocked_state"] == "blocked_operator_decision" for item in dependent_work_inventory())
    assert any(item["independent_work_continues"] is True for item in dependent_work_inventory())


def test_restart_inventory_preserves_requests_without_auto_resume():
    restart = restart_inventory()
    assert all(item["automatic_resume"] is False for item in restart)
    assert any(item["pending_request_preserved"] is True for item in restart)


def test_path_graph_and_information_matrix_show_missing_boundaries():
    graph = integration_path_graph()
    matrix = required_information_matrix()
    assert any(edge["status"] == "missing" for edge in graph)
    assert any(row["behavior"] == "direct_contradiction" and row["excluded_path_dependency"] is True for row in matrix)
    assert any(row["behavior"] == "restart_persistence" and row["persisted"] is False for row in matrix)


def test_minimum_pilot_boundary_is_bounded_and_blocked_by_exclusion():
    pilot = minimum_pilot_boundary()
    assert pilot["not_all_baseline_cases_required"] is True
    assert "explicit_correction" in pilot["must_support"]
    assert pilot["blocked_reason"] == "actual input and consumer boundary is excluded dirty work"


def test_amendment_consequence_names_next_gate_without_execution():
    consequence = amendment_consequence("excluded_path_required")
    assert consequence["next_authorized_gate"].startswith("operator scope decision")
    assert consequence["execute_now"] is False
    assert consequence["amend_existing_transfer_amendment"] is False


def test_report_files_identities_and_no_production_integration(tmp_path):
    final = run_integration_audit_report(tmp_path)
    assert final["status"] == STATUS_EXCLUDED_PATH_REQUIRED
    assert final["primary_classification"] == "excluded_path_required"
    for name in REQUIRED_REPORT_FILES:
        assert (tmp_path / name).exists(), name
    evaluator = json.loads((tmp_path / "evaluator_digest_audit.json").read_text(encoding="utf-8"))
    amendment = json.loads((tmp_path / "amendment_digest_audit.json").read_text(encoding="utf-8"))
    contract = json.loads((tmp_path / "contract_digest.json").read_text(encoding="utf-8"))
    assert evaluator["digest"] == EXPECTED_EVALUATOR_DIGEST
    assert amendment["amendment_digest"] == EXPECTED_AMENDMENT_DIGEST
    assert contract["contract_digest"] == EXPECTED_CONTRACT_DIGEST
    assert json.loads((tmp_path / "amendment_identity.json").read_text(encoding="utf-8"))["amendment_id"] == EXPECTED_AMENDMENT_ID
    no_integration = json.loads((tmp_path / "no_production_integration.json").read_text(encoding="utf-8"))
    assert no_integration["memory_mutated"] is False
    assert no_integration["conversation_behavior_mutated"] is False


def test_report_does_not_claim_integration_success(tmp_path):
    run_integration_audit_report(tmp_path)
    classification = json.loads((tmp_path / "feasibility_classification.json").read_text(encoding="utf-8"))
    assert classification["classification"] != "locally_integrable"
    final = json.loads((tmp_path / "final_status.json").read_text(encoding="utf-8"))
    assert final["production_integration"] is False
    assert final["model_executed"] is False
    assert final["candidate_generated"] is False
