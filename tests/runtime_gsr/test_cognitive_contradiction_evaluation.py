import json

from orchestration.runtime.cognitive_contradiction_evaluation import (
    FIRST_INCORRECT_TRANSITION,
    MATERIAL_GAP_ID,
    STATUS_GAP_IDENTIFIED,
    behavioral_cases,
    evaluate_observation,
    expected_observation,
    inspect_current_runtime_paths,
    observe_current_behavior,
    perturb_non_behavioral_labels,
    run_baseline_evaluation,
    with_relation,
)


def _case(case_id):
    return {case.case_id: case for case in behavioral_cases()}[case_id]


def test_behavioral_case_catalog_covers_required_transfer_cases():
    cases = behavioral_cases()
    assert [case.case_id for case in cases] == list("ABCDEFGHIJKL")
    assert {case.expected_classification for case in cases} >= {
        "correct_confirmation",
        "correct_explicit_correction",
        "correct_scoped_preference_update",
        "correct_bounded_exception",
        "correct_uncertain_conflict",
        "correct_unrelated",
        "correct_revocation",
        "correct_temporal_transition",
        "blocked_ambiguity",
        "operator_resolution_required",
    }
    assert _case("L").requires_operator_request is True


def test_path_inventory_is_diagnosis_only_and_names_current_surfaces():
    inventory = inspect_current_runtime_paths()
    assert inventory["mutation_performed"] is False
    assert inventory["provider_call_performed"] is False
    assert any("v31_contradiction_aggregation" in item for item in inventory["claim_paths"])
    assert any("v34_cognitive_state" in item for item in inventory["memory_paths"])
    assert any("v31_gated_integration" in item for item in inventory["authority_paths"])


def test_positive_controls_classify_expected_behavior():
    for case in behavioral_cases():
        observation = expected_observation(case)
        result = evaluate_observation(case, observation)
        assert result.classification == case.expected_classification
        assert result.passed is True


def test_evaluator_ignores_strategy_fixture_and_final_status_labels():
    case = _case("B")
    original = expected_observation(case)
    perturbed = perturb_non_behavioral_labels(original)
    assert evaluate_observation(case, original).as_dict() == evaluate_observation(case, perturbed).as_dict()


def test_missing_relation_record_detects_current_baseline_failure(tmp_path):
    case = _case("A")
    observation = observe_current_behavior(case, output_root=tmp_path)
    result = evaluate_observation(case, observation)
    assert result.classification == "missed_contradiction"
    assert result.passed is False
    assert result.first_incorrect_transition == FIRST_INCORRECT_TRANSITION
    assert observation["mutation_performed"] is False
    assert observation["provider_call_performed"] is False


def test_unrelated_topics_are_not_false_positive_contradictions(tmp_path):
    case = _case("F")
    observation = observe_current_behavior(case, output_root=tmp_path)
    result = evaluate_observation(case, observation)
    assert result.classification == "correct_unrelated"
    assert result.passed is True


def test_duplicate_restatement_is_not_misread_as_contradiction_success(tmp_path):
    case = _case("G")
    observation = observe_current_behavior(case, output_root=tmp_path)
    result = evaluate_observation(case, observation)
    assert result.classification == "false_contradiction"
    assert result.passed is False


def test_current_baseline_does_not_create_operator_boundary_request(tmp_path):
    case = _case("L")
    observation = observe_current_behavior(case, output_root=tmp_path)
    result = evaluate_observation(case, observation)
    assert result.classification == "missed_contradiction"
    assert result.passed is False
    assert observation["operator_resolution_request"] == ""
    assert observation["dependent_work_suspended"] is False


def test_authority_revocation_requires_linked_relation_state():
    case = _case("H")
    incomplete = with_relation(case, "revocation")
    incomplete["authority_revocation_record"] = ""
    result = evaluate_observation(case, incomplete)
    assert result.classification == "missed_contradiction"
    assert result.passed is False


def test_restart_case_requires_durable_claim_relation_state(tmp_path):
    case = _case("K")
    observation = observe_current_behavior(case, output_root=tmp_path)
    result = evaluate_observation(case, observation)
    assert observation["restart_round_trip_preserved"] is True
    assert result.classification == "restart_state_loss"
    assert result.passed is False


def test_baseline_report_identifies_one_material_gap_and_stops(tmp_path):
    report = run_baseline_evaluation(tmp_path)
    assert report["status"] == STATUS_GAP_IDENTIFIED
    assert report["material_gap"]["gap_id"] == MATERIAL_GAP_ID
    assert report["material_gap"]["single_material_gap"] is True
    assert report["stop_before_design_or_implementation"] is True
    assert report["implementation_performed"] is False
    assert report["candidate_generated"] is False
    assert report["sandbox_activation_performed"] is False
    assert report["staged"] is False
    assert report["committed"] is False
    assert report["pushed"] is False
    assert (tmp_path / "report.json").exists()
    restored = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert restored["status"] == STATUS_GAP_IDENTIFIED


def test_baseline_has_positive_control_and_multiple_independent_failures(tmp_path):
    report = run_baseline_evaluation(tmp_path)
    classifications = {item["case_id"]: item["classification"] for item in report["evaluations"]}
    assert classifications["F"] == "correct_unrelated"
    assert classifications["A"] == "missed_contradiction"
    assert classifications["B"] == "missed_contradiction"
    assert classifications["G"] == "false_contradiction"
    assert classifications["K"] == "restart_state_loss"
