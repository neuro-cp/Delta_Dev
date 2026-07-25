from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.autonomy_approved_plan_execution import (
    compile_execution_authority,
    compile_strategy,
    evaluate_strategy,
    run_approved_plan_execution,
)
from orchestration.runtime.autonomy_competence_admission import review_competence_candidate
from orchestration.runtime.autonomy_cycle_families import (
    JSON_FAMILY,
    JSON_TASK_CLASS,
    RECONCILIATION_FAMILY,
    cycle_family_registry_record,
    validate_cycle_family_eligibility,
)
from orchestration.runtime.autonomy_goal_queue_planning import approve_plan_for_future_execution, compile_plan_proposal, normalize_plan_feedback
from orchestration.runtime.autonomy_long_horizon_cycle import run_long_horizon_cycle
from orchestration.runtime.autonomy_multi_goal_scheduler import run_scheduler
from orchestration.runtime.autonomy_outcome_review import review_completed_outcome


def _json_plan(tmp_path: Path):
    result = run_long_horizon_cycle(output_root=tmp_path / "json-cycle", cycle_family=JSON_FAMILY)
    plan = json.loads(next((tmp_path / "json-cycle" / "a4_execution" / "inputs").glob("*.plan.json")).read_text(encoding="utf-8"))
    evaluator = json.loads(next((tmp_path / "json-cycle" / "a4_execution" / "evaluator").glob("*.json")).read_text(encoding="utf-8"))
    return result, plan, evaluator


def test_d2_registry_contains_two_materially_distinct_production_families():
    registry = cycle_family_registry_record()
    families = {item["cycle_family"]: item for item in registry["families"]}

    assert (RECONCILIATION_FAMILY, JSON_FAMILY) == tuple(families)
    assert families[RECONCILIATION_FAMILY]["output_schema"] != families[JSON_FAMILY]["output_schema"]
    assert "live_competence_adapter.py" in families[JSON_FAMILY]["implementation_provenance"][0]


def test_d2_unsupported_and_schema_ineligible_families_do_not_fallback_to_reconciliation():
    unsupported = validate_cycle_family_eligibility({"cycle_family": "not_registered", "supported_task_class": ""})
    wrong_for_json = validate_cycle_family_eligibility({"cycle_family": JSON_FAMILY, "supported_task_class": "bounded_cross_format_record_reconciliation"})
    wrong_for_reconciliation = validate_cycle_family_eligibility({"cycle_family": RECONCILIATION_FAMILY, "supported_task_class": JSON_TASK_CLASS})

    assert unsupported["reason"] == "unsupported_cycle_family"
    assert wrong_for_json["reason"] == "ineligible_input_schema"
    assert wrong_for_reconciliation["reason"] == "ineligible_input_schema"


def test_d2_json_cycle_completes_through_a4_a7_and_restart_is_exact(tmp_path):
    first = run_long_horizon_cycle(output_root=tmp_path / "json-cycle", cycle_family=JSON_FAMILY)
    restart = run_long_horizon_cycle(output_root=tmp_path / "json-cycle", cycle_family=JSON_FAMILY)
    report = first["report"]

    assert first["status"] == "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED"
    assert restart["duplicate_suppressed"] is True
    assert report["cycle_family"] == JSON_FAMILY
    assert report["selected_goal"]["condition_key"] == "bounded_json_schema_validation_reporting"
    assert report["evaluator"]["cycle_family"] == JSON_FAMILY
    assert report["outcome_review"]["disposition"] == "candidate_for_competence_admission_review"
    assert report["competence_disposition"]["status"] == "accepted_bounded_competence"
    assert report["next_candidate_executed"] is False
    assert report["second_goal_execution"] is False
    assert len(tuple((tmp_path / "json-cycle" / "final_reports").glob("*.json"))) == 1


def test_d2_cycle_1_and_cycle_2_are_materially_independent(tmp_path):
    cycle1 = run_long_horizon_cycle(output_root=tmp_path / "cycle1", cycle_family=RECONCILIATION_FAMILY)
    cycle2 = run_long_horizon_cycle(output_root=tmp_path / "cycle2", cycle_family=JSON_FAMILY)

    assert cycle1["report"]["cycle_family"] == RECONCILIATION_FAMILY
    assert cycle2["report"]["cycle_family"] == JSON_FAMILY
    assert cycle1["report"]["selected_goal"]["condition_key"] != cycle2["report"]["selected_goal"]["condition_key"]
    assert cycle1["report"]["evaluator"]["evaluator_digest"] != cycle2["report"]["evaluator"]["evaluator_digest"]


def test_d2_json_evaluation_changes_with_behavior_not_strategy_label(tmp_path):
    _result, plan, evaluator = _json_plan(tmp_path)
    bad = compile_strategy(plan, evaluator, version="initial")
    good = compile_strategy(plan, evaluator, version="revised")
    same_output_label = {**good, "strategy_id": "different-label-same-behavior"}

    bad_eval = evaluate_strategy(bad, evaluator)
    good_eval = evaluate_strategy(good, evaluator)
    same_eval = evaluate_strategy(same_output_label, evaluator)

    assert bad_eval["aggregate_status"] == "revision_required"
    assert good_eval["aggregate_status"] == "passed"
    assert same_eval["aggregate_status"] == "passed"
    assert good_eval["strategy_identity_used_for_scoring"] is False


def test_d2_json_integrity_stops_for_family_mismatch_late_evaluator_and_hidden_leakage(tmp_path):
    _result, plan, evaluator = _json_plan(tmp_path)
    strategy = compile_strategy(plan, evaluator, version="revised")

    family_mismatch = evaluate_strategy({**strategy, "cycle_family": RECONCILIATION_FAMILY}, evaluator)
    late_evaluator = evaluate_strategy(strategy, {**evaluator, "sealed_before_strategy": False})
    leakage = evaluate_strategy({**strategy, "hidden_expected_outputs_seen": True}, evaluator)

    assert family_mismatch["aggregate_status"] == "integrity_stop"
    assert "strategy_family_provenance_mismatch" in family_mismatch["integrity_reasons"]
    assert late_evaluator["aggregate_status"] == "integrity_stop"
    assert "evaluator_created_after_strategy_output" in late_evaluator["integrity_reasons"]
    assert leakage["aggregate_status"] == "integrity_stop"
    assert "hidden_answer_leakage" in leakage["integrity_reasons"]


def test_d2_json_a5_a6_are_family_neutral_and_do_not_broaden_claim(tmp_path):
    result = run_long_horizon_cycle(output_root=tmp_path / "json-cycle", cycle_family=JSON_FAMILY)
    review = json.loads(next((tmp_path / "json-cycle" / "a5_review" / "reviews").glob("*.json")).read_text(encoding="utf-8"))
    candidate = json.loads(next((tmp_path / "json-cycle" / "a6_admission" / "admission_candidates").glob("*.json")).read_text(encoding="utf-8"))

    assert result["status"] == "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED"
    assert review["cycle_family"] == JSON_FAMILY
    assert "JSON record sets" in review["supported_behavior"]
    assert candidate["cycle_family"] == JSON_FAMILY
    assert candidate["supported_task_class"] == JSON_TASK_CLASS
    assert "general software engineering" in candidate["excluded_behavior"]
    assert "reconciliation" not in candidate["exact_behavioral_capability_statement"].lower()


def test_d2_scheduler_keeps_one_active_goal_across_families(tmp_path):
    result = run_scheduler(tmp_path / "scheduler", seed_goals=(
        {"condition_key": "bounded_json_schema_validation_reporting", "priority": 9, "cycle_family": JSON_FAMILY, "supported_task_class": JSON_TASK_CLASS},
        {"condition_key": "missing_or_unreliable_identifier_reconciliation", "priority": 8, "cycle_family": RECONCILIATION_FAMILY, "supported_task_class": "bounded_cross_format_record_reconciliation"},
        {"condition_key": "unsupported_family_goal", "priority": 99, "state": "blocked", "cycle_family": "not_registered"},
    ))
    restart = run_scheduler(tmp_path / "scheduler")

    assert result["scheduler"]["one_active_goal_maximum"] is True
    assert result["scheduler"]["selected_goal"]["condition_key"] == "bounded_json_schema_validation_reporting"
    assert result["scheduler"]["selected_goal"]["cycle_family"] == JSON_FAMILY
    assert restart["scheduler"]["queue_snapshot"] == result["scheduler"]["queue_snapshot"]


def test_d2_common_a4_lifecycle_rejects_unknown_family_before_execution(tmp_path):
    goal_result = run_long_horizon_cycle(output_root=tmp_path / "unknown", cycle_family="not_registered")

    assert goal_result["status"] == "unsupported_cycle_family"
    assert not (tmp_path / "unknown" / "a4_execution" / "strategies").exists()


def test_d2_direct_a4_json_artifacts_review_and_admission_can_be_replayed(tmp_path):
    first = run_long_horizon_cycle(output_root=tmp_path / "json-cycle", cycle_family=JSON_FAMILY)
    a4 = tmp_path / "json-cycle" / "a4_execution"
    a5 = tmp_path / "json-cycle" / "a5_review"
    a6 = tmp_path / "json-cycle" / "a6_admission"

    review = review_completed_outcome(a4, output_root=a5)
    admission = review_competence_candidate(a5, output_root=a6)

    assert first["status"] == "AUTONOMY_12_LONG_HORIZON_GOVERNED_CYCLE_PASSED"
    assert review["duplicate_suppressed"] is True
    assert admission["duplicate_suppressed"] is True


def test_d2_no_provider_network_deployment_or_source_mutation_authority(tmp_path):
    result = run_long_horizon_cycle(output_root=tmp_path / "json-cycle", cycle_family=JSON_FAMILY)
    report = result["report"]

    assert report["provider_calls"] == 0
    assert report["network_calls"] == 0
    assert report["deployment"] is False
    assert report["primary_tracked_source_mutation"] is False
    assert report["trusted_admission"] is False
    assert report["broad_promotion"] is False
