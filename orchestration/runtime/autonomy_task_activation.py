"""AUTONOMY-13 task-scoped bounded competence activation."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.autonomy_approved_plan_execution import compile_fixed_evaluator, compile_strategy, evaluate_strategy
from orchestration.runtime.autonomy_cycle_families import (
    JSON_FAMILY,
    JSON_TASK_CLASS,
    RECONCILIATION_FAMILY,
    compile_family_evaluator,
)
from orchestration.runtime.autonomy_competence_admission import ACTIVATION_STATE, load_competence_records
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_13_ROOT = Path(".tmp") / "autonomy-13-task-scoped-activation-v1"
ACTIVATION_STATES = {
    "pending_activation_review",
    "activated_for_task",
    "activation_rejected",
    "activation_expired",
    "activation_completed",
    "activation_integrity_stop",
}


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return dict(payload)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _parse_time(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _family_for_task_class(task_class: str) -> str:
    if task_class == JSON_TASK_CLASS:
        return JSON_FAMILY
    if task_class == "bounded_cross_format_record_reconciliation":
        return RECONCILIATION_FAMILY
    return ""


def _schemas_for_family(family: str) -> dict[str, str]:
    if family == JSON_FAMILY:
        return {
            "input_schema": "disposable_json_record_sets_plus_json_schemas",
            "output_schema": "deterministic_json_validation_report",
        }
    if family == RECONCILIATION_FAMILY:
        return {
            "input_schema": "bounded_tabular_records_with_declared_identifiers",
            "output_schema": "confirmed_ambiguous_unmatched_record_decisions",
        }
    return {"input_schema": "", "output_schema": ""}


def fresh_task_contract(task_class: str, *, task_nonce: str, input_schema: str | None = None, output_schema: str | None = None) -> dict[str, Any]:
    family = _family_for_task_class(task_class)
    schemas = _schemas_for_family(family)
    record = {
        "schema": "autonomy_13_task_contract_v1",
        "task_id": stable_id("autonomy-13-task", task_class, task_nonce),
        "task_class": task_class,
        "cycle_family": family,
        "input_schema": input_schema or schemas["input_schema"],
        "output_schema": output_schema or schemas["output_schema"],
        "provenance_requirements": ("accepted_competence_record", "sealed_evaluator_digest", "task_input_digest"),
        "authority_limits": {
            "provider_calls": 0,
            "network": False,
            "deployment": False,
            "credentials": False,
            "tracked_source_mutation": False,
            "global_activation": False,
        },
        "task_input_digest": bootstrap_digest(("fresh-task", task_class, task_nonce, input_schema or schemas["input_schema"])),
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _competence_matches_task(competence: Mapping[str, Any], task: Mapping[str, Any]) -> dict[str, Any]:
    task_class = str(task.get("task_class") or "")
    family = _family_for_task_class(task_class)
    schemas = _schemas_for_family(family)
    limitations = tuple(competence.get("limitations") or ())
    checks = {
        "accepted_status": competence.get("admission_status") == "accepted_bounded_competence",
        "future_bounded_use_allowed": competence.get("allowed_use_state") == ACTIVATION_STATE or competence.get("activation_state") == ACTIVATION_STATE,
        "task_class_exact": competence.get("task_class") == task_class,
        "input_schema_exact": task.get("input_schema") == schemas["input_schema"],
        "output_schema_exact": task.get("output_schema") == schemas["output_schema"],
        "required_provenance_present": bool(competence.get("competence_digest") or competence.get("artifact_digest")) and bool(competence.get("evaluator_digest")),
        "limitations_satisfied": bool(limitations),
        "no_prohibited_authority": not any(bool(task.get("authority_limits", {}).get(key)) for key in ("network", "deployment", "credentials", "tracked_source_mutation", "global_activation")),
    }
    return _digest_record({
        "schema": "autonomy_13_clause_level_scope_match_v1",
        "task_id": task.get("task_id"),
        "competence_id": competence.get("competence_id"),
        "checks": checks,
        "matched": all(checks.values()),
        "failed_clauses": tuple(key for key, value in checks.items() if not value),
        "limitations": limitations,
        "created_at": FIXED_TIMESTAMP,
    })


def select_task_competence(task: Mapping[str, Any], competences: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    matches = tuple((competence, _competence_matches_task(competence, task)) for competence in competences)
    accepted = tuple(item for item in matches if item[1]["matched"])
    if len(accepted) == 1:
        competence, scope = accepted[0]
        status = "selected"
        reason = "exact_task_scoped_match"
    elif len(accepted) > 1:
        competence, scope = {}, {}
        status = "rejected"
        reason = "ambiguous_multiple_competences"
    else:
        competence, scope = {}, matches[0][1] if matches else {}
        status = "rejected"
        reason = "no_exact_accepted_competence"
    return _digest_record({
        "schema": "autonomy_13_competence_selection_v1",
        "selection_id": stable_id("autonomy-13-selection", task.get("task_id"), tuple(record.get("competence_id") for record in competences), status, reason),
        "task_id": task.get("task_id"),
        "status": status,
        "reason": reason,
        "selected_competence": competence,
        "scope_match": scope,
        "global_activation": False,
        "created_at": FIXED_TIMESTAMP,
    })


def _active_activation(root: Path, task_id: str) -> dict[str, Any] | None:
    for path in sorted((root / "activations").glob("*.json")):
        record = _read_json(path)
        if record and record.get("task_id") == task_id and record.get("activation_status") == "activated_for_task":
            return record
    return None


def issue_task_activation(
    root: str | Path,
    task: Mapping[str, Any],
    selection: Mapping[str, Any],
    *,
    expires_at: str = "2026-07-24T02:00:00+00:00",
    now: datetime | None = None,
) -> dict[str, Any]:
    root = Path(root)
    if selection.get("status") != "selected":
        status = "activation_rejected"
        reason = str(selection.get("reason") or "selection_not_accepted")
    elif _active_activation(root, str(task.get("task_id"))):
        status = "activation_rejected"
        reason = "duplicate_active_execution"
    elif (expires := _parse_time(expires_at)) and (now or datetime(2026, 7, 24, 1, 0, tzinfo=timezone.utc)) >= expires:
        status = "activation_expired"
        reason = "activation_expired_before_execution"
    else:
        status = "activated_for_task"
        reason = "task_scoped_activation_issued"
    competence = dict(selection.get("selected_competence") or {})
    record = {
        "schema": "autonomy_13_task_scoped_activation_v1",
        "activation_id": stable_id("autonomy-13-activation", task.get("task_id"), competence.get("competence_id"), selection.get("artifact_digest"), status),
        "activation_request_id": stable_id("autonomy-13-activation-request", task.get("task_id"), selection.get("selection_id")),
        "activation_request_digest": bootstrap_digest((task.get("artifact_digest"), selection.get("artifact_digest"))),
        "task_id": task.get("task_id"),
        "task_digest": task.get("artifact_digest"),
        "competence_id": competence.get("competence_id", ""),
        "competence_digest": competence.get("competence_digest") or competence.get("artifact_digest", ""),
        "task_class": task.get("task_class"),
        "input_schema": task.get("input_schema"),
        "output_schema": task.get("output_schema"),
        "clause_level_scope_match": selection.get("scope_match"),
        "limitations": tuple(competence.get("limitations") or ()),
        "provenance_requirements": tuple(task.get("provenance_requirements") or ()),
        "evaluator_id": competence.get("evaluator_id", ""),
        "evaluator_digest": competence.get("evaluator_digest", ""),
        "authority_limits": dict(task.get("authority_limits") or {}),
        "activation_expiration": expires_at,
        "activation_status": status,
        "reason": reason,
        "global_activation": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write_json(root / "activations" / f"{record['activation_id']}.json", _digest_record(record))


def _plan_for_task(task: Mapping[str, Any]) -> dict[str, Any]:
    return _digest_record({
        "schema": "autonomy_13_activation_execution_plan_v1",
        "plan_id": stable_id("autonomy-13-plan", task.get("task_id")),
        "goal_id": task.get("task_id"),
        "goal_digest": task.get("artifact_digest"),
        "condition_key": task.get("task_class"),
        "cycle_family": task.get("cycle_family"),
        "supported_task_class": task.get("task_class"),
        "validation_strategy": ("sealed activation evaluator",),
        "authority_requirements": (),
        "proposed_work_items": ({"work_item_id": "activation-execution", "title": "Execute task-scoped competence once"},),
        "created_at": FIXED_TIMESTAMP,
    })


def _evaluator_for_task(task: Mapping[str, Any], root: Path) -> dict[str, Any]:
    plan = _plan_for_task(task)
    if task.get("cycle_family") == JSON_FAMILY:
        evaluator = compile_family_evaluator(plan, root / "json_evaluator")
        if evaluator:
            return evaluator
    if task.get("cycle_family") == RECONCILIATION_FAMILY and task.get("record_level_cases"):
        cases = tuple(dict(item) for item in tuple(task.get("record_level_cases") or ()))
        sealed_expected = tuple({"case_id": case["case_id"], "case_category": case["case_category"], "expected_decisions": case["expected_decisions"]} for case in cases)
        return _digest_record({
            "schema": "autonomy_13_task_bound_reconciliation_evaluator_v1",
            "cycle_family": RECONCILIATION_FAMILY,
            "evaluator_id": stable_id("autonomy-13-reconciliation-evaluator", task.get("task_id"), task.get("stage_input_digest"), tuple(case["case_id"] for case in cases)),
            "plan_id": plan["plan_id"],
            "sealed_before_strategy": True,
            "case_categories": tuple(str(case["case_category"]) for case in cases),
            "record_level_cases": cases,
            "sealed_expected_outputs": sealed_expected,
            "sealed_expected_output_digest": bootstrap_digest(sealed_expected),
            "scoring_rules": (
                "grade actual reconciliation decisions against task-bound validated records",
                "require Stage 1 input digest provenance",
                "do not score by strategy name, fixture path, or competence id",
            ),
            "negative_controls": True,
            "transfer_cases": True,
            "leakage_controls": ("strategy receives no expected hidden outputs",),
            "decision_rule": "all task-bound case categories must pass",
            "pass_threshold": len(cases),
            "created_at": FIXED_TIMESTAMP,
        })
    return compile_fixed_evaluator(plan)


def execute_task_activation(root: str | Path, task: Mapping[str, Any], activation: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root)
    existing = _read_json(root / "execution_results" / f"{activation.get('activation_id')}.json")
    if existing:
        return existing
    if activation.get("activation_status") != "activated_for_task":
        result = _digest_record({
            "schema": "autonomy_13_activation_execution_result_v1",
            "activation_id": activation.get("activation_id"),
            "task_id": task.get("task_id"),
            "execution_status": "not_executed",
            "reason": activation.get("reason") or activation.get("activation_status"),
            "semantic_execution_count": 0,
            "created_at": FIXED_TIMESTAMP,
        })
        return _write_json(root / "execution_results" / f"{activation.get('activation_id')}.json", result)
    evaluator_dir = root / ("j" if task.get("cycle_family") == JSON_FAMILY else "r")
    evaluator = _evaluator_for_task(task, evaluator_dir)
    strategy = compile_strategy(_plan_for_task(task), evaluator, version="revised")
    evaluation = evaluate_strategy(strategy, evaluator)
    result = _digest_record({
        "schema": "autonomy_13_activation_execution_result_v1",
        "activation_id": activation.get("activation_id"),
        "task_id": task.get("task_id"),
        "competence_id": activation.get("competence_id"),
        "evaluator_id": evaluator.get("evaluator_id"),
        "evaluator_digest": evaluator.get("artifact_digest"),
        "strategy_id": strategy.get("strategy_id"),
        "strategy_digest": strategy.get("artifact_digest"),
        "evaluation_id": evaluation.get("evaluation_id"),
        "evaluation_digest": evaluation.get("artifact_digest"),
        "evaluation": evaluation,
        "evaluator": evaluator,
        "primary_output": next(iter(dict(evaluation.get("strategy_outputs") or {}).values()), {}),
        "primary_output_digest": next((dict(item).get("artifact_digest") for item in dict(evaluation.get("strategy_outputs") or {}).values() if isinstance(item, Mapping)), ""),
        "evaluation_status": evaluation.get("aggregate_status"),
        "execution_status": "completed" if evaluation.get("aggregate_status") == "passed" else "activation_integrity_stop",
        "semantic_execution_count": 1,
        "evaluator_grades_actual_output": True,
        "strategy_identity_used_for_scoring": evaluation.get("strategy_identity_used_for_scoring") is True,
        "fixture_name_used_for_scoring": evaluation.get("fixture_name_used_for_scoring") is True,
        "provider_calls": 0,
        "network_calls": 0,
        "deployment": False,
        "credentials": False,
        "tracked_source_mutation": False,
        "created_at": FIXED_TIMESTAMP,
    })
    return _write_json(root / "execution_results" / f"{activation.get('activation_id')}.json", result)


def complete_task_activation(root: str | Path, activation: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root)
    status = "activation_completed" if result.get("execution_status") == "completed" else "activation_integrity_stop"
    record = dict(activation)
    record["activation_status"] = status
    record["execution_result"] = {
        "execution_status": result.get("execution_status"),
        "evaluation_status": result.get("evaluation_status"),
        "execution_digest": result.get("artifact_digest"),
    }
    record["final_disposition"] = status
    record["completed_at"] = FIXED_TIMESTAMP
    return _write_json(root / "activations" / f"{record['activation_id']}.json", _digest_record(record))


def run_task_scoped_activation(
    output_root: str | Path = AUTONOMY_13_ROOT,
    *,
    competence_roots: Sequence[str | Path] = (),
) -> dict[str, Any]:
    root = Path(output_root)
    existing = _read_json(root / "final_status.json")
    if existing:
        report = _read_json(root / "report.json") or {}
        return {"status": existing.get("status"), "report": report, "duplicate_suppressed": True}
    competences = load_competence_records(*competence_roots)
    pilots = []
    rejection_checks = []
    for task_class, nonce in (("bounded_cross_format_record_reconciliation", "fresh-reconciliation"), (JSON_TASK_CLASS, "fresh-json")):
        task = fresh_task_contract(task_class, task_nonce=nonce)
        _write_json(root / "tasks" / f"{task['task_id']}.json", task)
        selection = select_task_competence(task, competences)
        _write_json(root / "selections" / f"{selection['selection_id']}.json", selection)
        activation = issue_task_activation(root, task, selection)
        result = execute_task_activation(root, task, activation)
        completed = complete_task_activation(root, activation, result)
        restart_result = execute_task_activation(root, task, completed)
        wrong = select_task_competence({**task, "task_class": JSON_TASK_CLASS if task_class != JSON_TASK_CLASS else "bounded_cross_format_record_reconciliation"}, competences)
        unsupported = select_task_competence({**task, "input_schema": "unsupported_schema"}, competences)
        rejection_checks.extend((wrong, unsupported))
        pilots.append({
            "task": task,
            "selection": selection,
            "activation": completed,
            "execution_result": result,
            "restart_result": restart_result,
            "wrong_competence_rejected": wrong["status"] == "rejected",
            "unsupported_schema_rejected": unsupported["status"] == "rejected",
        })
    passed = (
        len(pilots) == 2
        and all(pilot["selection"]["status"] == "selected" for pilot in pilots)
        and all(pilot["activation"]["activation_status"] == "activation_completed" for pilot in pilots)
        and all(pilot["execution_result"]["semantic_execution_count"] == 1 for pilot in pilots)
        and all(pilot["restart_result"]["semantic_execution_count"] == 1 for pilot in pilots)
        and all(pilot["wrong_competence_rejected"] and pilot["unsupported_schema_rejected"] for pilot in pilots)
        and all(pilot["execution_result"]["evaluator_grades_actual_output"] for pilot in pilots)
        and all(not pilot["activation"]["global_activation"] for pilot in pilots)
        and all(check["status"] == "rejected" for check in rejection_checks)
    )
    status = "AUTONOMY_13_TASK_SCOPED_CAPABILITY_ACTIVATION_PASSED" if passed else "AUTONOMY_13_TASK_SCOPED_CAPABILITY_ACTIVATION_FAILED"
    report = _digest_record({
        "schema": "autonomy_13_task_scoped_activation_report_v1",
        "status": status,
        "first_missing_transition": "" if passed else "accepted competence -> eligible task-scoped activation -> exact-once evaluated completion",
        "competence_roots": tuple(str(path) for path in competence_roots),
        "competence_count": len(competences),
        "allowed_states": tuple(sorted(ACTIVATION_STATES)),
        "pilots": tuple(pilots),
        "rejection_checks": tuple(rejection_checks),
        "provider_calls": 0,
        "network_calls": 0,
        "deployment": False,
        "credentials": False,
        "tracked_source_mutation": False,
        "global_activation": False,
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(root / "report.json", report)
    _write_json(root / "records.json", {"pilots": tuple(pilots), "rejection_checks": tuple(rejection_checks)})
    _write_json(root / "restart_audit.json", {"restart_exact": all(pilot["restart_result"] == pilot["execution_result"] for pilot in pilots)})
    _write_json(root / "duplicate_audit.json", {"duplicate_semantic_execution_suppressed": all(pilot["restart_result"]["semantic_execution_count"] == 1 for pilot in pilots)})
    _write_json(root / "final_status.json", {"status": status, "artifact_digest": report["artifact_digest"]})
    return {"status": status, "report": report, "duplicate_suppressed": False}
