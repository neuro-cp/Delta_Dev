from pathlib import Path

from orchestration.runtime.cognitive_strategy_feasibility import (
    REQUIRED_REPORT_FILES,
    STATUS_NEW_GOVERNED_STATE_REQUIRED,
    audit_failed_replacement,
    audit_revision_noop,
    behavioral_requirement,
    classify_feasibility,
    classify_required_information,
    first_missing_transition,
    helper_search_results,
    inspect_source_boundary,
    minimum_feasible_boundary,
    negative_controls,
    proposal_consequence,
    run_strategy_feasibility_audit,
)


def _source() -> str:
    return Path("orchestration/runtime/autonomy_advisory_assistance.py").read_text(encoding="utf-8")


def test_behavioral_fact_extraction_names_required_distinctions():
    requirement = behavioral_requirement()
    assert requirement["freshness_required"] is True
    assert requirement["rejection_history_required"] is True
    assert "must not emit PASSED" in requirement["blocked_or_rejected_state"]


def test_exact_selected_block_scope_audit():
    audit = inspect_source_boundary(_source())
    assert audit["selected_start_line"] == 224
    assert audit["selected_end_line"] == 250
    assert audit["selected_unit"] == "if_statement"
    assert "report.get(\"status\")" in audit["selected_block"]
    assert "persist_consumed_before_success" in audit["selected_block"]


def test_containing_function_scope_audit_records_parameters_and_locals():
    audit = inspect_source_boundary(_source())
    assert audit["containing_function"] == "request_bounded_advice"
    assert set(("output_root", "packet", "mode")).issubset(audit["parameters"])
    assert set(("existing", "audit", "report", "request")).issubset(audit["local_variables"])


def test_symbol_provenance_verification_rejects_absent_helpers():
    audit = inspect_source_boundary(_source())
    assert "validate_artifact_freshness" not in audit["module_functions"]
    assert "has_rejection_history" not in audit["module_functions"]


def test_similar_name_semantic_mismatch_rejection():
    helpers = helper_search_results()
    stale_packet = next(item for item in helpers if item["symbol"] == "detect_stale_packet")
    assert stale_packet["safe_and_reusable"] is False
    assert stale_packet["addresses_behavioral_contract"] is False


def test_test_only_helper_rejection_negative_control():
    assert negative_controls()["test_only_helper_rejected"] is True


def test_existing_production_helper_is_not_enough_when_semantics_do_not_match():
    helpers = helper_search_results()
    advisory_validator = next(item for item in helpers if item["symbol"] == "validate_advisory_output")
    assert advisory_validator["production_code"] is True
    assert advisory_validator["addresses_behavioral_contract"] is False


def test_upstream_dataflow_classification_records_no_safe_local_freshness():
    matrix = classify_required_information(inspect_source_boundary(_source()))
    freshness = next(row for row in matrix if row["fact"] == "artifact_creation_time")
    assert freshness["safe_to_consume"] is False
    assert freshness["available_in_selected_block"] == ()


def test_missing_governed_state_classification():
    matrix = classify_required_information(inspect_source_boundary(_source()))
    classification = classify_feasibility(matrix, helper_search_results())
    assert classification["classification"] == "new_governed_state_required"
    assert classification["status"] == STATUS_NEW_GOVERNED_STATE_REQUIRED


def test_locally_expressible_requires_concrete_symbol_mapping():
    matrix = classify_required_information(inspect_source_boundary(_source()))
    classification = classify_feasibility(matrix, helper_search_results())
    assert classification["locally_expressible"] is False
    assert classification["concrete_symbol_mapping_demonstrated"] is False


def test_minimum_feasible_boundary_calculation():
    matrix = classify_required_information(inspect_source_boundary(_source()))
    boundary = minimum_feasible_boundary(classify_feasibility(matrix, helper_search_results()))
    assert boundary["minimum_boundary"] == "one governed state contract and consumer"
    assert boundary["operator_reauthorization_required"] is True


def test_proposal_amendment_requirement():
    consequence = proposal_consequence()
    assert consequence["required_consequence"] == "strategy amendment"
    assert consequence["proposal_change_performed"] is False


def test_no_automatic_authorization_or_candidate_generation(tmp_path):
    result = run_strategy_feasibility_audit(tmp_path)
    assert result["status"] == STATUS_NEW_GOVERNED_STATE_REQUIRED
    assert (tmp_path / "required_operator_authorization.json").exists()
    assert (tmp_path / "no_candidate_generation.json").read_text(encoding="utf-8").find("false") >= 0


def test_no_implementation_or_evaluator_mutation_declared(tmp_path):
    run_strategy_feasibility_audit(tmp_path)
    assert '"implementation_source_mutated": false' in (tmp_path / "no_implementation_mutation.json").read_text(encoding="utf-8")
    assert '"evaluator_mutated": false' in (tmp_path / "evaluator_immutability.json").read_text(encoding="utf-8")


def test_proposal_and_amendment_immutability(tmp_path):
    run_strategy_feasibility_audit(tmp_path)
    assert '"proposal_mutated": false' in (tmp_path / "proposal_immutability.json").read_text(encoding="utf-8")
    assert '"amendment_mutated": false' in (tmp_path / "amendment_immutability.json").read_text(encoding="utf-8")


def test_previous_stage_reports_are_referenced_and_all_required_reports_written(tmp_path):
    run_strategy_feasibility_audit(tmp_path)
    for name in REQUIRED_REPORT_FILES:
        assert (tmp_path / name).exists(), name
    assert first_missing_transition()["schema"].endswith("_v1")
    assert audit_failed_replacement()["assumed_unavailable_state"] is True
    assert audit_revision_noop()["empty_effective_repair"] is True
