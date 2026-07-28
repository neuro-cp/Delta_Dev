import json

from orchestration.runtime.cognitive_excluded_path_reconciliation import (
    EXPECTED_AMENDMENT_DIGEST,
    EXPECTED_AMENDMENT_ID,
    EXPECTED_CONTRACT_DIGEST,
    EXPECTED_EVALUATOR_DIGEST,
    REQUIRED_REPORT_FILES,
    STATUS_DELTA_ONLY,
    alternative_clean_seams,
    checkpoint_ownership,
    classify_delta_hunks,
    classify_live_adapter_hunks,
    classify_reconciliation,
    deferred_semantic_cases,
    delta_hunk_inventory,
    delta_integration_seams,
    deterministic_pilot_cases,
    exact_authorization_boundary,
    first_missing_transition,
    live_adapter_dependency,
    live_adapter_hunk_inventory,
    minimum_pilot,
    run_reconciliation_report,
    scope_conflict_matrix,
    semantic_classifier_placement,
    worktree_digest,
)


def test_first_missing_transition_matches_excluded_path_reconciliation_gap():
    transition = first_missing_transition()
    assert transition["first_missing_transition"].startswith("claim-relation integration requires DELTA.py")
    assert "exact excluded-file diff" in transition["required_transition"]


def test_delta_only_classification_is_primary_when_live_adapter_deferred():
    result = classify_reconciliation(delta_required=True, live_required=False)
    assert result["classification"] == "DELTA_ONLY_AUTHORIZATION_REQUIRED"
    assert result["status"] == STATUS_DELTA_ONLY


def test_both_files_required_classification_control():
    result = classify_reconciliation(delta_required=True, live_required=True)
    assert result["classification"] == "BOTH_EXCLUDED_FILES_AUTHORIZATION_REQUIRED"


def test_conflict_and_unknown_ownership_controls_take_precedence():
    assert classify_reconciliation(dirty_conflict=True)["classification"] == "EXISTING_DIRTY_WORK_CONFLICT"
    assert classify_reconciliation(unknown_ownership=True)["classification"] == "UNKNOWN_DIRTY_HUNK_OWNERSHIP"


def test_clean_adapter_and_semantic_classifier_controls():
    assert classify_reconciliation(clean_adapter_available=True)["classification"] == "CLEAN_ADAPTER_PATH_AVAILABLE"
    assert classify_reconciliation(semantic_required_first=True)["classification"] == "SEMANTIC_CLASSIFIER_GATE_REQUIRED_FIRST"


def test_delta_hunks_are_inventoryed_and_preserved():
    hunks = delta_hunk_inventory()
    assert len(hunks) >= 8
    assert any(item["symbol"] == "conversation command dispatch" for item in hunks)
    classified = classify_delta_hunks()
    assert all(item["must_remain_byte_for_byte_preserved"] is True for item in classified)
    assert any(item["classification"] == "production behavior change" for item in classified)
    assert all(item["unknown_ownership"] is False for item in hunks)


def test_live_adapter_hunk_is_deferred_compatibility_repair():
    hunks = live_adapter_hunk_inventory()
    assert len(hunks) == 1
    classified = classify_live_adapter_hunks()[0]
    assert classified["classification"] == "compatibility repair"
    assert "create_json_fixture" in classified["symbol"]
    dependency = live_adapter_dependency()
    assert dependency["classification"] == "deferred"
    assert dependency["required_for_operator_turn_claim_production"] is False


def test_delta_integration_seams_are_additive_and_flaggable():
    seams = delta_integration_seams()
    assert any("conversation intake" in item["symbol"] for item in seams)
    assert all(item["clean_function_call_can_be_inserted"] is True for item in seams)
    assert all(item["bounded_pilot_flag_possible"] is True for item in seams)


def test_clean_adapter_alternatives_are_rejected_when_they_bypass_production():
    alternatives = alternative_clean_seams()
    assert all(item["accepted"] is False for item in alternatives)
    assert any("bypass actual DELTA.py conversation route" in item["reason"] for item in alternatives)


def test_semantic_classifier_is_deferred_but_deterministic_pilot_remains_meaningful():
    placement = semantic_classifier_placement()
    assert placement["model_called"] is False
    assert placement["first_pilot_can_defer_semantic_classifier"] is True
    assert "explicit_correction" in deterministic_pilot_cases()
    assert "direct_contradiction" in deferred_semantic_cases()
    assert placement["meaningful_without_model_inference"] is True


def test_minimum_pilot_completeness():
    pilot = minimum_pilot()
    assert pilot["requires_delta_py"] is True
    assert pilot["requires_live_competence_adapter"] is False
    assert pilot["direct_semantic_contradiction_deferred"] is True
    assert "restart_persistence" in pilot["required_cases"]


def test_scope_conflict_matrix_records_required_and_deferred_paths():
    matrix = scope_conflict_matrix()
    by_row = {item["row"]: item for item in matrix}
    assert by_row["claim producer insertion"]["required_for_pilot"] is True
    assert by_row["live_competence_adapter.py existing dirty hunk"]["required_for_pilot"] is False
    assert by_row["claim producer insertion"]["operator_authorization_required"] is True


def test_checkpoint_ownership_separates_existing_dirty_work_from_transfer_pilot():
    decision = checkpoint_ownership()
    assert decision["include_existing_dirty_in_same_transfer_checkpoint"] is False
    assert decision["delta_dirty_work"] == "commit_separately_before_claim_relation_integration_preferred"
    assert decision["impossible_to_separate_safely"] is False


def test_exact_authorization_boundary_is_delta_only_and_deterministic():
    boundary = exact_authorization_boundary()
    assert boundary["classification"] == "DELTA_ONLY_AUTHORIZATION_REQUIRED"
    assert "import a new claim-relation pilot service" in boundary["allowed_additive_changes"]
    assert "direct_contradiction" in boundary["prohibited_semantic_cases"]
    assert boundary["checkpoint_strategy"]["include_existing_dirty_in_same_transfer_checkpoint"] is False


def test_report_files_identity_stability_and_no_excluded_file_mutation(tmp_path):
    delta_before = worktree_digest(__import__("pathlib").Path("DELTA.py"))
    live_before = worktree_digest(__import__("pathlib").Path("orchestration/runtime/live_competence_adapter.py"))
    final = run_reconciliation_report(tmp_path)
    assert final["status"] == STATUS_DELTA_ONLY
    for name in REQUIRED_REPORT_FILES:
        assert (tmp_path / name).exists(), name
    assert worktree_digest(__import__("pathlib").Path("DELTA.py")) == delta_before
    assert worktree_digest(__import__("pathlib").Path("orchestration/runtime/live_competence_adapter.py")) == live_before
    no_mutation = json.loads((tmp_path / "no_excluded_file_mutation.json").read_text(encoding="utf-8"))
    assert no_mutation["mutated_by_gate"] is False
    assert no_mutation["delta_digest_before"] == no_mutation["delta_digest_after"]
    assert no_mutation["live_adapter_digest_before"] == no_mutation["live_adapter_digest_after"]


def test_report_records_accepted_identities(tmp_path):
    run_reconciliation_report(tmp_path)
    evaluator = json.loads((tmp_path / "evaluator_identity.json").read_text(encoding="utf-8"))
    contract = json.loads((tmp_path / "contract_identity.json").read_text(encoding="utf-8"))
    amendment = json.loads((tmp_path / "amendment_identity.json").read_text(encoding="utf-8"))
    assert evaluator["digest"] == EXPECTED_EVALUATOR_DIGEST
    assert contract["contract_digest"] == EXPECTED_CONTRACT_DIGEST
    assert amendment["amendment_id"] == EXPECTED_AMENDMENT_ID
    assert amendment["amendment_digest"] == EXPECTED_AMENDMENT_DIGEST


def test_report_does_not_authorize_or_simulate_integration(tmp_path):
    run_reconciliation_report(tmp_path)
    no_integration = json.loads((tmp_path / "no_production_integration.json").read_text(encoding="utf-8"))
    no_model = json.loads((tmp_path / "no_model_execution.json").read_text(encoding="utf-8"))
    no_candidate = json.loads((tmp_path / "no_candidate_generation.json").read_text(encoding="utf-8"))
    assert no_integration["conversation_behavior_mutated"] is False
    assert no_model["model_executed"] is False
    assert no_candidate["candidate_generated"] is False
