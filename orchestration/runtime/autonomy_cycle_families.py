"""Known AUTONOMY-12 cycle families with bounded evaluator/strategy hooks."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.live_competence_adapter import (
    JSON_CASE_CLASSES,
    JSON_OBJECTIVE,
    JSON_SEMANTIC_OPERATIONS,
    JSON_TASK_CLASS,
    _json_mission_output,
    _mission,
    _negative_controls,
    _validate_json_output,
    compile_live_competence_context,
    create_json_fixture,
    registered_live_task_adapters,
    seal_json_validator,
)
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


RECONCILIATION_FAMILY = "reconciliation_record_level_v1"
JSON_FAMILY = "structured_json_validation_v1"


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def supported_cycle_families() -> tuple[dict[str, Any], ...]:
    return (
        {
            "cycle_family": RECONCILIATION_FAMILY,
            "goal_type": "record_reconciliation",
            "supported_task_class": "bounded_cross_format_record_reconciliation",
            "input_schema": "bounded_tabular_records_with_declared_identifiers",
            "output_schema": "confirmed_ambiguous_unmatched_record_decisions",
            "implementation_provenance": ("orchestration/runtime/autonomy_approved_plan_execution.py",),
            "test_provenance": ("tests/runtime_gsr/test_autonomy_4_approved_plan_execution.py",),
        },
        {
            "cycle_family": JSON_FAMILY,
            "goal_type": "json_validation",
            "supported_task_class": JSON_TASK_CLASS,
            "input_schema": "disposable_json_record_sets_plus_json_schemas",
            "output_schema": "deterministic_json_validation_report",
            "evaluator_policy_version": "autonomy_12r_json_family_evaluator_policy_v1",
            "revision_policy": "enable_json_semantics_after_failed_empty_report_ablation",
            "prohibited_authorities": ("provider_calls", "network", "tracked_source_mutation", "deployment", "credentials"),
            "implementation_provenance": ("orchestration/runtime/live_competence_adapter.py",),
            "test_provenance": ("tests/runtime_gsr/test_live_competence_adapter.py",),
        },
    )


def cycle_family_registry_record() -> dict[str, Any]:
    return _digest_record({
        "schema": "autonomy_12_cycle_family_registry_v1",
        "families": supported_cycle_families(),
        "default_family": RECONCILIATION_FAMILY,
        "unsupported_disposition": "unsupported_cycle_family",
        "created_at": FIXED_TIMESTAMP,
    })


def infer_cycle_family(goal_or_plan: Mapping[str, Any]) -> str:
    declared = str(goal_or_plan.get("cycle_family") or "")
    if declared:
        return declared
    condition = str(goal_or_plan.get("condition_key") or goal_or_plan.get("normalized_objective") or "")
    task_class = str(goal_or_plan.get("supported_task_class") or "")
    if condition == "missing_or_unreliable_identifier_reconciliation" or "reconciliation" in condition:
        return RECONCILIATION_FAMILY
    if task_class == JSON_TASK_CLASS or "json" in condition:
        return JSON_FAMILY
    return RECONCILIATION_FAMILY


def validate_cycle_family_eligibility(plan: Mapping[str, Any]) -> dict[str, Any]:
    family = infer_cycle_family(plan)
    task_class = str(plan.get("supported_task_class") or "")
    if family == RECONCILIATION_FAMILY:
        if task_class and task_class not in {"bounded_cross_format_record_reconciliation", "record_reconciliation"}:
            return {"eligible": False, "reason": "ineligible_input_schema", "cycle_family": family}
        return {"eligible": True, "reason": "eligible", "cycle_family": family}
    if family == JSON_FAMILY:
        if task_class != JSON_TASK_CLASS:
            return {"eligible": False, "reason": "ineligible_input_schema", "cycle_family": family}
        paths = ("orchestration/runtime/live_competence_adapter.py", "tests/runtime_gsr/test_live_competence_adapter.py")
        if not all(Path(path).exists() for path in paths):
            return {"eligible": False, "reason": "implementation_or_test_path_missing", "cycle_family": family}
        return {"eligible": True, "reason": "eligible", "cycle_family": family}
    return {"eligible": False, "reason": "unsupported_cycle_family", "cycle_family": family or "unknown"}


def _json_adapter():
    return next(adapter for adapter in registered_live_task_adapters() if adapter.adapter_id == "structured_json_validation")


def compile_family_evaluator(plan: Mapping[str, Any], output_root: Path) -> dict[str, Any] | None:
    eligibility = validate_cycle_family_eligibility(plan)
    if eligibility["cycle_family"] != JSON_FAMILY or not eligibility["eligible"]:
        return None
    runtime_root = Path(output_root) / "family_runtime"
    mission = _digest_record(dict(_mission(JSON_TASK_CLASS, JSON_OBJECTIVE)))
    fixture = create_json_fixture(runtime_root, reset=False)
    context = compile_live_competence_context(runtime_root, mission, _json_adapter())
    validator = seal_json_validator(runtime_root, fixture)
    case_families = {
        "visible": ("valid_record_set", "missing_required_field"),
        "transfer": ("optional_null", "multiple_error_record", "provenance_completeness"),
        "adversarial": ("invalid_nested_object", "invalid_boolean", "malformed_json", "unsupported_schema_version"),
        "negative_control": ("unexpected_field", "invalid_integer", "multiple_error_record", "invalid_nested_object", "malformed_json", "unsupported_schema_version"),
    }
    return _digest_record({
        "schema": "autonomy_12_family_fixed_evaluator_v1",
        "cycle_family": JSON_FAMILY,
        "evaluator_id": stable_id("autonomy-12-json-evaluator", plan.get("plan_id"), fixture["artifact_digest"], validator["artifact_digest"]),
        "plan_id": plan.get("plan_id"),
        "sealed_before_strategy": True,
        "family_runtime_root": str(runtime_root),
        "mission": mission,
        "fixture": fixture,
        "context": context,
        "sealed_validator": validator,
        "case_categories": JSON_CASE_CLASSES,
        "case_family_sets": case_families,
        "hidden_case_digest": bootstrap_digest({"hidden": ("invalid_nested_object", "multiple_error_record"), "expected": validator["expected_report_digest"]}),
        "sealed_expected_outputs": {"expected_report_digest": validator["expected_report_digest"]},
        "sealed_expected_output_digest": validator["expected_report_digest"],
        "negative_controls": True,
        "transfer_cases": True,
        "evaluator_policy_version": "autonomy_12r_json_family_evaluator_policy_v1",
        "evaluator_provenance": ("live_competence_json_validation_retained_evidence",),
        "source_evidence_ids": ("live-competence-json-fixture", "live-competence-json-validator"),
        "source_evidence_digests": (fixture["artifact_digest"], validator["artifact_digest"]),
        "scoring_rules": (
            "compare actual JSON validation report per file against sealed report",
            "require fixture input digests unchanged",
            "grade actual output behavior, not adapter or family label",
        ),
        "negative_control_rules": ("empty", "irrelevant", "keyword_only", "flat_field_only", "unstructured"),
        "capability_statement": {
            "statement": "Validates bounded JSON record sets against supplied supported schemas and reports missing fields, unexpected fields, primitive type errors, nested object errors, malformed JSON, unsupported schema versions, optional nulls, multiple errors, and provenance-complete field-level failures without mutating inputs.",
            "supported_inputs": ("disposable JSON record sets", "declared JSON schemas"),
            "supported_outputs": ("deterministic JSON validation report",),
            "supported_case_families": JSON_CASE_CLASSES,
            "known_failure_modes": ("bounded disposable fixtures only", "does not prove general JSON tooling or source repair"),
            "excluded_domains": ("general software engineering", "source mutation", "unbounded data validation", "provider-backed inference"),
        },
        "implementation_provenance": ("orchestration/runtime/live_competence_adapter.py",),
        "test_provenance": ("tests/runtime_gsr/test_live_competence_adapter.py",),
        "created_at": FIXED_TIMESTAMP,
    })


def compile_family_strategy(plan: Mapping[str, Any], evaluator: Mapping[str, Any], *, version: str) -> dict[str, Any] | None:
    if evaluator.get("cycle_family") != JSON_FAMILY:
        return None
    semantic_enabled = version not in {"initial", "revised_failed"}
    return _digest_record({
        "schema": "autonomy_12_json_validation_strategy_v1",
        "cycle_family": JSON_FAMILY,
        "strategy_id": stable_id("autonomy-12-json-strategy", plan.get("plan_id"), evaluator.get("artifact_digest"), version),
        "plan_id": plan.get("plan_id"),
        "evaluator_digest": evaluator.get("artifact_digest"),
        "version": version,
        "output_schema": "live_competence_json_validation_report_v1",
        "behavior_profile": "structured_json_semantics_enabled" if semantic_enabled else "empty_report_semantic_ablation",
        "adapter_semantics_enabled": semantic_enabled,
        "semantic_operations": JSON_SEMANTIC_OPERATIONS if semantic_enabled else (),
        "hidden_expected_outputs_seen": False,
        "created_at": FIXED_TIMESTAMP,
    })


def evaluate_family_strategy(strategy: Mapping[str, Any], evaluator: Mapping[str, Any]) -> dict[str, Any] | None:
    if evaluator.get("cycle_family") != JSON_FAMILY:
        return None
    if evaluator.get("sealed_before_strategy") is not True:
        aggregate = "integrity_stop"
        reasons = ("evaluator_created_after_strategy_output",)
        output = {}
        evaluation = {"case_results": (), "validation_digest": "", "artifact_digest": ""}
    elif strategy.get("cycle_family") != evaluator.get("cycle_family"):
        aggregate = "integrity_stop"
        reasons = ("strategy_family_provenance_mismatch",)
        output = {}
        evaluation = {"case_results": (), "validation_digest": "", "artifact_digest": ""}
    elif strategy.get("evaluator_digest") != evaluator.get("artifact_digest"):
        aggregate = "integrity_stop"
        reasons = ("strategy_evaluator_digest_mismatch",)
        output = {}
        evaluation = {"case_results": (), "validation_digest": "", "artifact_digest": ""}
    elif strategy.get("hidden_expected_outputs_seen") or strategy.get("visible_expected_report"):
        aggregate = "integrity_stop"
        reasons = ("hidden_answer_leakage",)
        output = {}
        evaluation = {"case_results": (), "validation_digest": "", "artifact_digest": ""}
    else:
        runtime_root = Path(str(evaluator["family_runtime_root"]))
        output = _json_mission_output(runtime_root, evaluator["mission"], evaluator["context"], semantic_enabled=bool(strategy.get("adapter_semantics_enabled")))
        evaluation = _validate_json_output(runtime_root, evaluator["mission"], evaluator["fixture"], evaluator["sealed_validator"], output)
        aggregate = "passed" if evaluation["aggregate_status"] == "passed" else "revision_required"
        reasons = ()
    case_outcomes = tuple(
        {
            "case_id": item.get("case_class"),
            "case_category": item.get("case_class"),
            "outcome": item.get("outcome"),
            "score": 1 if item.get("outcome") == "passed" else 0,
            "expected_output_digest": evaluator.get("sealed_expected_output_digest"),
            "strategy_output_digest": output.get("artifact_digest", ""),
        }
        for item in tuple(evaluation.get("case_results") or ())
    )
    failed = tuple(item for item in case_outcomes if item.get("outcome") != "passed")
    return _digest_record({
        "schema": "autonomy_4_strategy_evaluation_v1",
        "cycle_family": JSON_FAMILY,
        "evaluation_id": stable_id("autonomy-12-json-evaluation", strategy.get("artifact_digest"), evaluator.get("artifact_digest"), output.get("artifact_digest", ""), tuple(reasons)),
        "strategy_id": strategy.get("strategy_id"),
        "strategy_digest": strategy.get("artifact_digest"),
        "evaluator_id": evaluator.get("evaluator_id"),
        "evaluator_digest": evaluator.get("artifact_digest"),
        "case_outcomes": case_outcomes,
        "strategy_outputs": {str(output.get("output_id", "integrity_stop")): output} if output else {},
        "evaluator_observations": tuple(evaluation.get("case_results") or ()),
        "aggregate_status": aggregate,
        "failed_case_ids": tuple(item["case_id"] for item in failed),
        "failed_case_categories": tuple(item["case_category"] for item in failed),
        "evaluator_weakened": False,
        "integrity_reasons": reasons,
        "record_level_evaluation": False,
        "behavior_based_evaluation": True,
        "strategy_identity_used_for_scoring": False,
        "fixture_name_used_for_scoring": False,
        "created_at": FIXED_TIMESTAMP,
    })


def compile_family_revision(prior_strategy: Mapping[str, Any], evaluation: Mapping[str, Any], evaluator: Mapping[str, Any], *, budget_remaining: int) -> dict[str, Any] | None:
    if evaluator.get("cycle_family") != JSON_FAMILY:
        return None
    return _digest_record({
        "schema": "autonomy_4_strategy_revision_v1",
        "cycle_family": JSON_FAMILY,
        "revision_id": stable_id("autonomy-12-json-revision", prior_strategy.get("strategy_id"), evaluation.get("artifact_digest")),
        "prior_strategy_id": prior_strategy.get("strategy_id"),
        "prior_strategy_digest": prior_strategy.get("artifact_digest"),
        "failed_evaluator_case_ids": tuple(evaluation.get("failed_case_ids") or ()),
        "observed_failure": "semantic ablation produced an empty JSON validation report",
        "diagnosed_first_incorrect_transition": "fixture inspection -> empty report -> unsupported missing/type/nested error evidence",
        "proposed_change": "enable structured JSON schema validation semantics while preserving sealed evaluator digest",
        "expected_effect": "actual output report matches sealed missing, unexpected, type, nested, optional-null, and multiple-error cases",
        "unchanged_evaluator_digest": evaluator.get("artifact_digest"),
        "budget_remaining": budget_remaining,
        "authority_confirmation": "within approved one-revision budget",
        "revision_result": "ready_for_revised_strategy",
        "created_at": FIXED_TIMESTAMP,
    })


def family_negative_control_results(evaluator: Mapping[str, Any]) -> dict[str, int]:
    if evaluator.get("cycle_family") != JSON_FAMILY:
        return {}
    return _negative_controls(Path(str(evaluator["family_runtime_root"])), evaluator["mission"], evaluator["fixture"], evaluator["sealed_validator"])
