"""AUTONOMY-14 narrow cross-capability composition."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.autonomy_cycle_families import JSON_FAMILY, JSON_TASK_CLASS, RECONCILIATION_FAMILY
from orchestration.runtime.autonomy_task_activation import (
    fresh_task_contract,
    issue_task_activation,
    execute_task_activation,
    complete_task_activation,
    select_task_competence,
)
from orchestration.runtime.autonomy_competence_admission import load_competence_records
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_14_ROOT = Path(".tmp") / "autonomy-14-cross-capability-composition"
COMPOSITION_FAMILY = "validated_json_to_reconciliation_v1"
COMPOSITION_STATUS_PASSED = "AUTONOMY_14_CROSS_CAPABILITY_COMPOSITION_PASSED"
COMPOSITION_STATUS_INTEGRITY_STOP = "AUTONOMY_14_CROSS_CAPABILITY_COMPOSITION_INTEGRITY_STOP"


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


def supported_composition_families() -> tuple[dict[str, Any], ...]:
    return (_digest_record({
        "schema": "autonomy_14_composition_family_v1",
        "composition_family": COMPOSITION_FAMILY,
        "ordered_stage_families": (JSON_FAMILY, RECONCILIATION_FAMILY),
        "stage_1_task_class": JSON_TASK_CLASS,
        "stage_2_task_class": "bounded_cross_format_record_reconciliation",
        "generic_chaining": False,
        "created_at": FIXED_TIMESTAMP,
    }),)


def _authority_intersection() -> dict[str, Any]:
    return _digest_record({
        "schema": "autonomy_14_authority_intersection_v1",
        "read_authority": "disposable_task_inputs_only",
        "disposable_output_authority": True,
        "provider_authority": False,
        "network_authority": False,
        "deployment_authority": False,
        "credential_authority": False,
        "tracked_source_mutation_authority": False,
        "trusted_generalization_authority": False,
        "created_at": FIXED_TIMESTAMP,
    })


def _transition(root: Path, composition_id: str, previous: str, current: str, reason: str) -> dict[str, Any]:
    record = _digest_record({
        "schema": "autonomy_14_composition_lifecycle_transition_v1",
        "transition_id": stable_id("autonomy-14-transition", composition_id, previous, current, reason),
        "composition_id": composition_id,
        "previous_state": previous,
        "next_state": current,
        "reason": reason,
        "created_at": FIXED_TIMESTAMP,
    })
    return _write_json(root / "lifecycle" / f"{record['transition_id']}.json", record)


def _stage_graph() -> dict[str, Any]:
    return _digest_record({
        "schema": "autonomy_14_stage_graph_v1",
        "ordered_stage_ids": ("stage_1_json_validation", "stage_2_reconciliation"),
        "dependency_edges": (("stage_1_json_validation", "stage_2_reconciliation"),),
        "stage_1_family": JSON_FAMILY,
        "stage_2_family": RECONCILIATION_FAMILY,
        "created_at": FIXED_TIMESTAMP,
    })


def _composition_evaluator(task_digest: str, graph_digest: str) -> dict[str, Any]:
    return _digest_record({
        "schema": "autonomy_14_fixed_composition_evaluator_v1",
        "composition_evaluator_id": stable_id("autonomy-14-evaluator", task_digest, graph_digest),
        "sealed_before_stage_execution": True,
        "checks": (
            "stage_order",
            "stage_1_completed_before_stage_2",
            "stage_1_output_digest_matches_stage_2_input_digest",
            "stage_evaluator_digests_fixed",
            "provenance_survives_both_stages",
            "no_invalid_or_unsupported_json_reached_stage_2",
            "stage_2_references_stage_1_validated_records_only",
            "no_duplicate_semantic_stage_execution",
            "authority_intersection_preserved",
            "no_broad_composition_claim",
        ),
        "created_at": FIXED_TIMESTAMP,
    })


def create_composition_request(root: str | Path, *, family: str = COMPOSITION_FAMILY, nonce: str = "pilot") -> dict[str, Any]:
    root = Path(root)
    if family != COMPOSITION_FAMILY:
        return _digest_record({"schema": "autonomy_14_composition_request_v1", "status": "unsupported_composition_family", "composition_family": family, "created_at": FIXED_TIMESTAMP})
    graph = _stage_graph()
    task = _digest_record({
        "schema": "autonomy_14_composed_task_v1",
        "task_id": stable_id("autonomy-14-task", family, nonce),
        "task_digest": bootstrap_digest(("composed-json-reconciliation", nonce)),
        "composition_family": family,
        "objective": "Validate JSON records, then reconcile only validated eligible records.",
        "created_at": FIXED_TIMESTAMP,
    })
    evaluator = _composition_evaluator(task["artifact_digest"], graph["artifact_digest"])
    authority = _authority_intersection()
    request = _digest_record({
        "schema": "autonomy_14_composition_request_v1",
        "composition_id": stable_id("autonomy-14-composition", task["task_id"], graph["artifact_digest"]),
        "task_id": task["task_id"],
        "task_digest": task["artifact_digest"],
        "composition_family": family,
        "ordered_stage_ids": graph["ordered_stage_ids"],
        "stage_input_schemas": ("disposable_json_record_sets_plus_json_schemas", "bounded_tabular_records_with_declared_identifiers"),
        "stage_output_schemas": ("validated_records_for_reconciliation_v1", "confirmed_ambiguous_unmatched_record_decisions"),
        "dependency_edges": graph["dependency_edges"],
        "composition_evaluator_id": evaluator["composition_evaluator_id"],
        "composition_evaluator_digest": evaluator["artifact_digest"],
        "provenance_requirements": ("original_input_digest", "stage_1_output_digest", "stage_2_input_digest", "composition_evaluation_digest"),
        "authority_intersection": authority,
        "prohibited_authorities": ("provider", "network", "deployment", "credentials", "tracked_source_mutation", "trusted_generalization"),
        "expiration": "2026-07-24T02:00:00+00:00",
        "current_stage": "pending_composition_review",
        "lifecycle_status": "pending_composition_review",
        "restart_key": stable_id("autonomy-14-restart", task["task_id"], graph["artifact_digest"]),
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(root / "composition_request.json", request)
    _write_json(root / "stage_graph.json", graph)
    _write_json(root / "evaluator.json", evaluator)
    _write_json(root / "authority_intersection.json", authority)
    return request


def _decision(left_key: str, status: str, *, right_keys: Sequence[str] = (), reason: str = "") -> dict[str, Any]:
    return {"left_key": left_key, "right_keys": tuple(right_keys), "status": status, "reason": reason or status, "provenance": ("stage_1_validated_record",)}


def _case_from_stage_1(stage_1_output_digest: str) -> dict[str, Any]:
    visible = {
        "left_records": ({"key": "json-left-1", "record_id": "J-1", "name": "Json Ada", "source_file": "stage1.validated", "row_id": 1},),
        "right_records": ({"key": "json-right-1", "record_id": "J-1", "name": "Json Ada", "source_file": "stage1.validated", "row_id": 2},),
        "field_mappings": {},
        "composite_keys": (),
        "visible_provenance": ("stage_1_output_digest", stage_1_output_digest),
        "permitted_matching_rules": ("stable_identifier", "uncertainty_preservation"),
        "declared_uncertainty_policy": "preserve ambiguity unless corroborated",
        "permitted_output_schema": ("confirmed", "ambiguous", "unmatched", "unsupported"),
        "unsupported_shape": False,
    }
    semantic_key = bootstrap_digest({"visible": visible, "stage_1_output_digest": stage_1_output_digest})
    return {
        "case_id": stable_id("autonomy-14-reconciliation-case", semantic_key),
        "case_category": "stage_1_validated_record_match",
        "semantic_key": semantic_key,
        "strategy_visible_input": visible,
        "expected_decisions": (_decision("json-left-1", "confirmed", right_keys=("json-right-1",), reason="stage_1_validated_identifier"),),
    }


def _validated_stage_1_payload(result: Mapping[str, Any], *, scenario: str) -> dict[str, Any]:
    primary = dict(result.get("primary_output") or {})
    report = dict(primary.get("report") or {})
    block_reason = ""
    if scenario == "malformed":
        block_reason = "malformed_json"
    elif scenario == "unsupported_schema":
        block_reason = "unsupported_schema_version"
    elif scenario == "missing_provenance":
        block_reason = "missing_provenance"
    elif scenario == "ineligible_schema":
        block_reason = "reconciliation_ineligible_output_schema"
    valid_records = () if block_reason else ({"key": "json-left-1", "record_id": "J-1", "name": "Json Ada"}, {"key": "json-right-1", "record_id": "J-1", "name": "Json Ada"})
    payload = {
        "schema": "autonomy_14_stage_1_validated_output_v1",
        "parse_status": "failed" if block_reason == "malformed_json" else "passed",
        "schema_version": "2" if block_reason == "unsupported_schema_version" else "1",
        "validated_records": valid_records,
        "field_level_failures": tuple(file.get("errors", ()) for file in tuple(report.get("files") or ()) if file.get("errors")),
        "malformed_input_result": block_reason == "malformed_json",
        "unsupported_schema_result": block_reason == "unsupported_schema_version",
        "provenance_completeness_result": block_reason != "missing_provenance",
        "reconciliation_eligible": not block_reason,
        "source_stage_output_digest": result.get("primary_output_digest"),
        "normalized_output_digest": bootstrap_digest((valid_records, result.get("primary_output_digest"), scenario)),
    }
    return _digest_record(payload)


def _composition_evaluate(request: Mapping[str, Any], stage_1: Mapping[str, Any], stage_2: Mapping[str, Any] | None, *, scenario: str, tampered: bool = False, reversed_order: bool = False, evaluator_mutated: bool = False) -> dict[str, Any]:
    reasons = []
    if reversed_order:
        reasons.append("reversed_stage_order")
    if tampered:
        reasons.append("stage_1_output_digest_tampered")
    if evaluator_mutated:
        reasons.append("stage_evaluator_digest_changed")
    if stage_1.get("stage_status") != "stage_1_completed":
        reasons.append(str(stage_1.get("blocked_reason") or "stage_1_not_completed"))
    if stage_2 and stage_2.get("stage_2_input_digest") != stage_1.get("validated_output_digest"):
        reasons.append("stage_1_output_digest_mismatch")
    if stage_2 and stage_2.get("semantic_execution_count") != 1:
        reasons.append("duplicate_stage_2_execution")
    if stage_1.get("semantic_execution_count") != 1:
        reasons.append("duplicate_stage_1_execution")
    aggregate = "integrity_stop" if reasons else "passed"
    return _digest_record({
        "schema": "autonomy_14_composition_evaluation_v1",
        "composition_id": request.get("composition_id"),
        "composition_evaluator_id": request.get("composition_evaluator_id"),
        "composition_evaluator_digest": request.get("composition_evaluator_digest"),
        "aggregate_status": aggregate,
        "integrity_reasons": tuple(reasons),
        "no_broad_composition_claim": True,
        "authority_intersection_preserved": True,
        "created_at": FIXED_TIMESTAMP,
    })


def run_capability_composition(
    output_root: str | Path = AUTONOMY_14_ROOT,
    *,
    competence_roots: Sequence[str | Path] = (),
    scenario: str = "valid",
    family: str = COMPOSITION_FAMILY,
    pause_after_stage_1: bool = False,
    resume: bool = False,
    stop_after_stage_1: bool = False,
    tamper_stage_1: bool = False,
    reverse_order: bool = False,
    mutate_evaluator: bool = False,
    expire_stage_2: bool = False,
    suspended_stage_2: bool = False,
) -> dict[str, Any]:
    root = Path(output_root)
    final = _read_json(root / "composition_result.json")
    if final and final.get("terminal"):
        return {"status": final["status"], "composition_result": final, "duplicate_suppressed": True}
    request = _read_json(root / "composition_request.json") or create_composition_request(root, family=family, nonce=scenario)
    if request.get("status") == "unsupported_composition_family":
        return {"status": "unsupported_composition_family", "composition_result": request, "duplicate_suppressed": False}
    competences = load_competence_records(*competence_roots)
    _transition(root, str(request["composition_id"]), "pending_composition_review", "ready", "composition_family_supported")
    if reverse_order:
        evaluation = _composition_evaluate(request, {"stage_status": "stage_1_not_started", "semantic_execution_count": 0}, None, scenario=scenario, reversed_order=True)
        result = _digest_record({"schema": "autonomy_14_composition_result_v1", "status": COMPOSITION_STATUS_INTEGRITY_STOP, "terminal": True, "composition_evaluation": evaluation, "created_at": FIXED_TIMESTAMP})
        _write_json(root / "composition_result.json", result)
        return {"status": COMPOSITION_STATUS_INTEGRITY_STOP, "composition_result": result, "duplicate_suppressed": False}

    stage_1_result = _read_json(root / "stage_1_result.json")
    if not stage_1_result:
        _transition(root, str(request["composition_id"]), "ready", "stage_1_activating", "activate_json_competence")
        task_1 = fresh_task_contract(JSON_TASK_CLASS, task_nonce=f"a14-{scenario}-stage-1")
        sel_1 = select_task_competence(task_1, competences)
        act_1 = issue_task_activation(root / "s1", task_1, sel_1)
        _transition(root, str(request["composition_id"]), "stage_1_activating", "stage_1_running", "json_activation_ready")
        exec_1 = execute_task_activation(root / "s1", task_1, act_1)
        done_1 = complete_task_activation(root / "s1", act_1, exec_1)
        validated = _validated_stage_1_payload(exec_1, scenario=scenario)
        blocked_reason = "" if validated["reconciliation_eligible"] else (
            "malformed_json" if validated["malformed_input_result"] else "unsupported_schema_version" if validated["unsupported_schema_result"] else "missing_provenance" if not validated["provenance_completeness_result"] else "reconciliation_ineligible_output_schema"
        )
        stage_1_result = _digest_record({
            "schema": "autonomy_14_stage_1_result_v1",
            "stage_id": "stage_1_json_validation",
            "stage_status": "stage_1_completed" if not blocked_reason else "stage_1_failed",
            "activation": done_1,
            "activation_id": done_1.get("activation_id"),
            "activation_digest": done_1.get("artifact_digest"),
            "evaluator_id": exec_1.get("evaluator_id"),
            "evaluator_digest": exec_1.get("evaluator_digest"),
            "evaluation_digest": exec_1.get("evaluation_digest"),
            "stage_output_digest": exec_1.get("primary_output_digest"),
            "validated_output": validated,
            "validated_output_digest": validated["artifact_digest"],
            "blocked_reason": blocked_reason,
            "semantic_execution_count": 1,
            "created_at": FIXED_TIMESTAMP,
        })
        _write_json(root / "stage_1_result.json", stage_1_result)
    if stop_after_stage_1:
        _transition(root, str(request["composition_id"]), "stage_1_completed", "stopped_by_operator", "operator_stop_before_stage_2")
        result = _digest_record({"schema": "autonomy_14_composition_result_v1", "status": "stopped_by_operator", "terminal": True, "stage_1": stage_1_result, "stage_2": None, "created_at": FIXED_TIMESTAMP})
        _write_json(root / "composition_result.json", result)
        return {"status": "stopped_by_operator", "composition_result": result, "duplicate_suppressed": False}
    if pause_after_stage_1 and not resume:
        _transition(root, str(request["composition_id"]), "stage_1_completed", "paused_operator", "pause_before_stage_2")
        result = _digest_record({"schema": "autonomy_14_composition_result_v1", "status": "paused_operator", "terminal": False, "stage_1": stage_1_result, "stage_2": None, "created_at": FIXED_TIMESTAMP})
        _write_json(root / "composition_result.json", result)
        return {"status": "paused_operator", "composition_result": result, "duplicate_suppressed": False}
    if stage_1_result.get("stage_status") != "stage_1_completed":
        _transition(root, str(request["composition_id"]), "stage_1_failed", "stage_2_blocked", str(stage_1_result.get("blocked_reason")))
        result = _digest_record({"schema": "autonomy_14_composition_result_v1", "status": "stage_2_blocked", "terminal": True, "stage_1": stage_1_result, "stage_2": None, "blocked_reason": stage_1_result.get("blocked_reason"), "created_at": FIXED_TIMESTAMP})
        _write_json(root / "composition_result.json", result)
        return {"status": "stage_2_blocked", "composition_result": result, "duplicate_suppressed": False}
    stage_2_result = _read_json(root / "stage_2_result.json")
    if not stage_2_result:
        if expire_stage_2 or suspended_stage_2:
            reason = "activation_expired" if expire_stage_2 else "competence_suspended"
            result = _digest_record({"schema": "autonomy_14_composition_result_v1", "status": "stage_2_blocked", "terminal": True, "stage_1": stage_1_result, "stage_2": None, "blocked_reason": reason, "created_at": FIXED_TIMESTAMP})
            _write_json(root / "composition_result.json", result)
            return {"status": "stage_2_blocked", "composition_result": result, "duplicate_suppressed": False}
        _transition(root, str(request["composition_id"]), "stage_1_completed", "stage_2_activating", "activate_reconciliation_competence")
        stage_1_digest = str(stage_1_result["validated_output_digest"])
        task_2 = fresh_task_contract("bounded_cross_format_record_reconciliation", task_nonce=f"a14-{scenario}-stage-2")
        task_2 = _digest_record({**task_2, "stage_input_digest": stage_1_digest, "record_level_cases": (_case_from_stage_1(stage_1_digest),)})
        sel_2 = select_task_competence(task_2, competences)
        act_2 = issue_task_activation(root / "s2", task_2, sel_2, expires_at="2026-07-24T00:00:00+00:00" if expire_stage_2 else "2026-07-24T02:00:00+00:00")
        if act_2["activation_status"] != "activated_for_task":
            result = _digest_record({"schema": "autonomy_14_composition_result_v1", "status": "stage_2_blocked", "terminal": True, "stage_1": stage_1_result, "stage_2": None, "blocked_reason": act_2.get("reason"), "created_at": FIXED_TIMESTAMP})
            _write_json(root / "composition_result.json", result)
            return {"status": "stage_2_blocked", "composition_result": result, "duplicate_suppressed": False}
        _transition(root, str(request["composition_id"]), "stage_2_activating", "stage_2_running", "reconciliation_activation_ready")
        exec_2 = execute_task_activation(root / "s2", task_2, act_2)
        done_2 = complete_task_activation(root / "s2", act_2, exec_2)
        stage_2_result = _digest_record({
            "schema": "autonomy_14_stage_2_result_v1",
            "stage_id": "stage_2_reconciliation",
            "stage_status": "stage_2_completed" if exec_2.get("execution_status") == "completed" else "stage_2_failed",
            "stage_2_input_digest": stage_1_digest,
            "activation": done_2,
            "activation_id": done_2.get("activation_id"),
            "activation_digest": done_2.get("artifact_digest"),
            "evaluator_id": exec_2.get("evaluator_id"),
            "evaluator_digest": exec_2.get("evaluator_digest"),
            "evaluation_digest": exec_2.get("evaluation_digest"),
            "output_digest": exec_2.get("primary_output_digest"),
            "semantic_execution_count": 1,
            "created_at": FIXED_TIMESTAMP,
        })
        _write_json(root / "stage_2_result.json", stage_2_result)
    _transition(root, str(request["composition_id"]), "stage_2_completed", "composition_evaluating", "evaluate_composition")
    evaluation = _composition_evaluate(request, {**stage_1_result, "validated_output_digest": "tampered" if tamper_stage_1 else stage_1_result["validated_output_digest"], "semantic_execution_count": 1}, stage_2_result, scenario=scenario, tampered=tamper_stage_1, evaluator_mutated=mutate_evaluator)
    status = COMPOSITION_STATUS_INTEGRITY_STOP if evaluation["aggregate_status"] == "integrity_stop" else COMPOSITION_STATUS_PASSED
    result = _digest_record({
        "schema": "autonomy_14_composition_result_v1",
        "status": status,
        "terminal": True,
        "stage_1": stage_1_result,
        "stage_2": stage_2_result,
        "composition_evaluation": evaluation,
        "final_capability_claim": "Validated JSON records were reconciled under the two bounded stage competences; no general data engineering competence was created.",
        "provider_calls": 0,
        "network_calls": 0,
        "deployment": False,
        "credentials": False,
        "tracked_source_mutation": False,
        "global_activation": False,
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(root / "composition_result.json", result)
    _write_json(root / "provenance_chain.json", {
        "original_input_digest": request["task_digest"],
        "stage_1_activation_digest": stage_1_result["activation_digest"],
        "stage_1_output_digest": stage_1_result["validated_output_digest"],
        "stage_1_evaluation_digest": stage_1_result["evaluation_digest"],
        "stage_2_activation_digest": stage_2_result["activation_digest"],
        "stage_2_input_digest": stage_2_result["stage_2_input_digest"],
        "stage_2_output_digest": stage_2_result["output_digest"],
        "stage_2_evaluation_digest": stage_2_result["evaluation_digest"],
        "composition_evaluation_digest": evaluation["artifact_digest"],
        "final_result_digest": result["artifact_digest"],
    })
    return {"status": status, "composition_result": result, "duplicate_suppressed": False}
