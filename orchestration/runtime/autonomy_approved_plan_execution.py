"""AUTONOMY-4 approved-plan execution and bounded strategy revision."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP
from orchestration.runtime.autonomy_cycle_families import (
    compile_family_evaluator,
    compile_family_revision,
    compile_family_strategy,
    evaluate_family_strategy,
    infer_cycle_family,
    validate_cycle_family_eligibility,
)


AUTONOMY_4_ROOT = Path(".tmp") / "autonomy-4-approved-plan-execution-v1"
FINAL_DISPOSITIONS = {
    "completed_with_provisional_evidence",
    "completed_without_revision",
    "failed_after_revision",
    "blocked_capability",
    "paused_budget",
    "stopped_by_operator",
    "integrity_stop",
}
TERMINAL_WORK_ITEM_STATES = {
    "completed",
    "failed_evaluation",
    "revision_required",
    "paused_operator",
    "stopped_by_operator",
    "authority_expired",
    "terminal",
}
VALID_WORK_ITEM_TRANSITIONS = {
    "ready": {"running"},
    "running": {"completed", "failed_evaluation", "revision_required", "paused_operator", "stopped_by_operator", "authority_expired", "terminal"},
    "failed_evaluation": {"revision_required"},
    "revision_required": {"running"},
    "paused_operator": {"running", "stopped_by_operator"},
    "authority_expired": set(),
    "completed": set(),
    "stopped_by_operator": set(),
    "terminal": set(),
}
STAGE_WORK_ITEM_IDS = {
    "prepared": "approved-plan-preflight",
    "evaluator": "sealed-evaluator",
    "initial_strategy": "initial-reconciliation-strategy",
    "initial_evaluation": "initial-strategy-evaluation",
    "revision": "bounded-strategy-revision",
    "revised_strategy": "revised-reconciliation-strategy",
    "revised_evaluation": "revised-strategy-evaluation",
    "final_synthesis": "final-synthesis",
    "execution": "approved-plan-execution",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return data


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _lock_owner(root: Path) -> dict[str, Any]:
    return _read_json(root / "runner.lock" / "owner.json") or {}


def acquire_execution_lock(root: Path, authority: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root)
    lock = root / "runner.lock"
    root.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        return _digest_record({
            "schema": "autonomy_4_execution_lock_result_v1",
            "acquired": False,
            "reason": "duplicate_active_runner",
            "owner": _lock_owner(root),
            "created_at": FIXED_TIMESTAMP,
        })
    owner = _digest_record({
        "schema": "live_runtime_4_runner_lock_owner_v1",
        "pid": os.getpid(),
        "authority_id": authority["authority_id"],
        "authority_digest": authority["artifact_digest"],
        "runner_lock_scope": authority.get("runner_lock_scope") or stable_id("live-runtime-4-runner-lock", str(root), authority.get("plan_id")),
        "plan_id": authority.get("plan_id"),
        "execution_id": stable_id("autonomy-4-execution", authority["authority_id"]),
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(lock / "owner.json", owner)
    return _digest_record({
        "schema": "autonomy_4_execution_lock_result_v1",
        "acquired": True,
        "reason": "",
        "owner": owner,
        "created_at": FIXED_TIMESTAMP,
    })


def release_execution_lock(root: Path) -> None:
    lock = Path(root) / "runner.lock"
    if lock.exists():
        shutil.rmtree(lock)


def validate_work_item_transition(previous_state: str, next_state: str) -> None:
    if next_state not in VALID_WORK_ITEM_TRANSITIONS.get(previous_state, set()):
        raise ValueError(f"invalid_work_item_transition:{previous_state}->{next_state}")


def persist_work_item_transition(
    output_root: Path,
    *,
    execution_id: str,
    goal_id: str,
    plan_id: str,
    work_item_id: str,
    previous_state: str,
    next_state: str,
    reason: str,
    source_artifact_id: str,
    source_artifact_digest: str,
    authority_id: str,
    controller_cycle: int,
) -> dict[str, Any]:
    validate_work_item_transition(previous_state, next_state)
    transition = _digest_record({
        "schema": "autonomy_4_work_item_lifecycle_transition_v1",
        "transition_id": stable_id("autonomy-4-work-transition", execution_id, work_item_id, previous_state, next_state, reason, controller_cycle),
        "execution_id": execution_id,
        "goal_id": goal_id,
        "plan_id": plan_id,
        "work_item_id": work_item_id,
        "previous_state": previous_state,
        "next_state": next_state,
        "reason": reason,
        "source_artifact_id": source_artifact_id,
        "source_artifact_digest": source_artifact_digest,
        "authority_id": authority_id,
        "controller_cycle": controller_cycle,
        "created_at": FIXED_TIMESTAMP,
    })
    path = Path(output_root) / "work_item_lifecycle" / f"{transition['transition_id']}.json"
    existing = _read_json(path)
    if existing:
        return existing
    return _write_json(path, transition)


def reconstruct_lifecycle_state(output_root: Path) -> dict[str, Any]:
    states: dict[str, str] = {}
    transitions: list[dict[str, Any]] = []
    for path in sorted((Path(output_root) / "work_item_lifecycle").glob("*.json")):
        transition = _read_json(path)
        if not transition:
            continue
        transitions.append(transition)
    transitions = sorted(transitions, key=lambda item: (int(item.get("controller_cycle") or 0), str(item.get("transition_id") or "")))
    for transition in transitions:
        states[str(transition["work_item_id"])] = str(transition["next_state"])
    return _digest_record({
        "schema": "autonomy_4_lifecycle_state_v1",
        "states": states,
        "transition_count": len(transitions),
        "terminal": states.get(STAGE_WORK_ITEM_IDS["execution"]) in {"terminal", "stopped_by_operator", "authority_expired"},
        "created_at": FIXED_TIMESTAMP,
    })


def compile_execution_authority(
    plan: Mapping[str, Any],
    approval: Mapping[str, Any],
    *,
    expires_at: str = "2026-10-22T00:00:00+00:00",
    issued_at: str = FIXED_TIMESTAMP,
) -> dict[str, Any]:
    authority = {
        "schema": "autonomy_4_execution_authority_v1",
        "authority_id": stable_id("autonomy-4-authority", plan["plan_id"], approval["approval_id"]),
        "goal_id": plan["goal_id"],
        "goal_digest": plan["goal_digest"],
        "plan_id": plan["plan_id"],
        "plan_digest": plan["artifact_digest"],
        "approved_plan_version": approval["plan_id"],
        "allowed_work_item_ids": tuple(item["work_item_id"] for item in tuple(plan.get("proposed_work_items") or ())),
        "maximum_controller_cycles": 12,
        "maximum_execution_attempts": 2,
        "maximum_learning_attempts": 1,
        "maximum_provider_calls": 0,
        "retrieval_budget": 0,
        "duration_limit_minutes": 10,
        "mutation_surface": "none",
        "network_permission": False,
        "deployment_permission": False,
        "credential_permission": False,
        "trusted_admission_permission": False,
        "capability_promotion_permission": False,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "duration_seconds": max(0, int((_parse_time(expires_at) - _parse_time(issued_at)).total_seconds())) if _parse_time(expires_at) and _parse_time(issued_at) else None,
        "runner_lock_scope": stable_id("live-runtime-4-runner-lock", str(AUTONOMY_4_ROOT), plan["plan_id"]),
        "revoked": False,
        "consumed": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(authority)


def validate_execution_eligibility(
    plan: Mapping[str, Any],
    approval: Mapping[str, Any],
    authority: Mapping[str, Any],
    *,
    active_plan_digest: str | None = None,
    resolved_goal: bool = False,
    active_runner_exists: bool = False,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    current_time = (now or _utc_now)()
    issued_at = _parse_time(authority.get("issued_at"))
    expires_at = _parse_time(authority.get("expires_at"))
    if approval.get("plan_status") != "approved_for_future_execution":
        reasons.append("plan_not_approved")
    if approval.get("plan_digest") != plan.get("artifact_digest"):
        reasons.append("plan_approval_digest_mismatch")
    if authority.get("plan_digest") != plan.get("artifact_digest") or authority.get("goal_digest") != plan.get("goal_digest"):
        reasons.append("authority_digest_mismatch")
    if active_plan_digest and active_plan_digest != plan.get("artifact_digest"):
        reasons.append("superseded_plan")
    if authority.get("consumed") is True:
        reasons.append("authority_consumed")
    if authority.get("revoked") is True:
        reasons.append("authority_revoked")
    if issued_at and current_time < issued_at:
        reasons.append("authority_not_yet_valid")
    if expires_at and current_time >= expires_at:
        reasons.append("authority_expired")
    if active_runner_exists:
        reasons.append("duplicate_active_runner")
    if resolved_goal:
        reasons.append("goal_resolved_before_execution")
    if not tuple(plan.get("validation_strategy") or ()):
        reasons.append("missing_validator")
    reqs = dict(plan.get("authority_requirements") or {})
    if reqs.get("tracked_source_mutation") or reqs.get("network") or reqs.get("deployment") or reqs.get("credentials"):
        reasons.append("prohibited_permission_required")
    family = validate_cycle_family_eligibility(plan)
    if not family["eligible"]:
        reasons.append(str(family["reason"]))
    return _digest_record({
        "schema": "autonomy_4_execution_eligibility_v1",
        "eligibility_id": stable_id("autonomy-4-eligibility", plan.get("plan_id"), approval.get("approval_id"), authority.get("authority_id"), tuple(reasons)),
        "plan_id": plan.get("plan_id"),
        "authority_id": authority.get("authority_id"),
        "eligible": not reasons,
        "reasons": tuple(reasons),
        "cycle_family": family["cycle_family"],
        "created_at": FIXED_TIMESTAMP,
    })


def _decision(left_key: str, status: str, *, right_keys: Sequence[str] = (), reason: str = "", provenance: Sequence[str] = ("input_record",)) -> dict[str, Any]:
    return {
        "left_key": left_key,
        "right_keys": tuple(right_keys),
        "status": status,
        "reason": reason or status,
        "provenance": tuple(provenance),
    }


def _case(
    category: str,
    *,
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    expected: Sequence[Mapping[str, Any]],
    field_mappings: Mapping[str, str] | None = None,
    composite_keys: Sequence[str] = (),
    unsupported_shape: bool = False,
) -> dict[str, Any]:
    semantic_key = bootstrap_digest({"left": tuple(left), "right": tuple(right), "expected_statuses": tuple((item["left_key"], item["status"]) for item in expected)})
    visible = {
        "left_records": tuple(dict(item) for item in left),
        "right_records": tuple(dict(item) for item in right),
        "field_mappings": dict(field_mappings or {}),
        "composite_keys": tuple(composite_keys),
        "visible_provenance": ("source_file", "row_id", "declared_field_mapping"),
        "permitted_matching_rules": ("stable_identifier", "declared_composite_key", "uncertainty_preservation"),
        "declared_uncertainty_policy": "preserve ambiguity when corroborating identifier or composite evidence is absent",
        "permitted_output_schema": ("confirmed", "ambiguous", "unmatched", "unsupported"),
        "unsupported_shape": unsupported_shape,
    }
    return {
        "case_id": stable_id("autonomy-4-record-case", semantic_key),
        "case_category": category,
        "semantic_key": semantic_key,
        "strategy_visible_input": visible,
        "expected_decisions": tuple(dict(item) for item in expected),
    }


def _record_level_cases() -> tuple[dict[str, Any], ...]:
    return (
        _case("exact_stable_identifier", left=({"key": "l-exact", "record_id": "A-1", "name": "Ada Core", "source_file": "left.csv", "row_id": 1},), right=({"key": "r-exact", "record_id": "A-1", "name": "Ada Core", "source_file": "right.json", "row_id": 11},), expected=(_decision("l-exact", "confirmed", right_keys=("r-exact",), reason="stable_identifier"),)),
        _case("identifier_missing", left=({"key": "l-missing", "record_id": "", "name": "Solo Missing", "source_file": "left.csv", "row_id": 2},), right=({"key": "r-other", "record_id": "B-2", "name": "Other Record", "source_file": "right.json", "row_id": 12},), expected=(_decision("l-missing", "unmatched", reason="missing_identifier_no_candidate"),)),
        _case("identifier_renamed", left=({"key": "l-renamed", "record_id": "C-3", "name": "Renamed Field", "source_file": "left.tsv", "row_id": 3},), right=({"key": "r-renamed", "legacy_id": "C-3", "name": "Renamed Field", "source_file": "right.ndjson", "row_id": 13},), field_mappings={"record_id": "legacy_id"}, expected=(_decision("l-renamed", "confirmed", right_keys=("r-renamed",), reason="mapped_identifier"),)),
        _case("composite_identifier", left=({"key": "l-composite", "region": "NE", "account": "44", "name": "Composite Account", "source_file": "left.csv", "row_id": 4},), right=({"key": "r-composite", "region": "NE", "account": "44", "name": "Composite Account", "source_file": "right.json", "row_id": 14},), composite_keys=("region", "account"), expected=(_decision("l-composite", "confirmed", right_keys=("r-composite",), reason="composite_identifier"),)),
        _case("duplicated_identifier", left=({"key": "l-dup", "record_id": "D-4", "name": "Duplicate Id", "source_file": "left.csv", "row_id": 5},), right=({"key": "r-dup-1", "record_id": "D-4", "name": "Duplicate Id A", "source_file": "right.json", "row_id": 15}, {"key": "r-dup-2", "record_id": "D-4", "name": "Duplicate Id B", "source_file": "right.json", "row_id": 16}), expected=(_decision("l-dup", "ambiguous", right_keys=("r-dup-1", "r-dup-2"), reason="duplicate_identifier"),)),
        _case("conflicting_identifiers", left=({"key": "l-conflict", "record_id": "E-5", "name": "Conflict", "provenance_tag": "verified", "source_file": "left.csv", "row_id": 6},), right=({"key": "r-conflict", "record_id": "E-5", "name": "Conflict", "provenance_tag": "contradicted", "source_file": "right.json", "row_id": 17},), expected=(_decision("l-conflict", "ambiguous", right_keys=("r-conflict",), reason="conflicting_provenance"),)),
        _case("ambiguous_near_match", left=({"key": "l-near", "record_id": "", "name": "North Clinic", "source_file": "left.csv", "row_id": 7},), right=({"key": "r-near", "record_id": "", "name": "North Clinical", "source_file": "right.json", "row_id": 18},), expected=(_decision("l-near", "ambiguous", right_keys=("r-near",), reason="near_match_without_corroboration"),)),
        _case("no_valid_match", left=({"key": "l-none", "record_id": "F-6", "name": "No Match", "source_file": "left.csv", "row_id": 8},), right=({"key": "r-none", "record_id": "G-7", "name": "Different", "source_file": "right.json", "row_id": 19},), expected=(_decision("l-none", "unmatched", reason="no_valid_match"),)),
        _case("adversarial_similarity", left=({"key": "l-adv", "record_id": "", "name": "Jordan Lee", "entity_class": "person", "source_file": "left.csv", "row_id": 9},), right=({"key": "r-adv", "record_id": "", "name": "Jordan Lee", "entity_class": "facility", "source_file": "right.json", "row_id": 20},), expected=(_decision("l-adv", "unmatched", reason="incompatible_entity_class"),)),
        _case("transfer_unseen_fixture", left=({"key": "l-transfer", "asset_code": "T-8", "label": "Transfer Asset", "source_file": "left.parsed", "row_id": 10},), right=({"key": "r-transfer", "id_code": "T-8", "label": "Transfer Asset", "source_file": "right.parsed", "row_id": 21},), field_mappings={"asset_code": "id_code"}, expected=(_decision("l-transfer", "confirmed", right_keys=("r-transfer",), reason="transfer_mapped_identifier"),)),
    )


def _visible_input_integrity(evaluator: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    for case in tuple(evaluator.get("record_level_cases") or ()):
        visible = dict(case.get("strategy_visible_input") or {})
        text = json.dumps(visible, sort_keys=True, default=str).lower()
        if "expected_decisions" in visible or "expected_output" in text or "sealed_expected" in text:
            reasons.append(f"hidden_expected_output_visible:{case.get('case_category')}")
    return {"passed": not reasons, "reasons": tuple(reasons)}


def _record_value(record: Mapping[str, Any], fields: Sequence[str]) -> tuple[Any, ...]:
    return tuple(record.get(field) for field in fields)


def _similar(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    lname = str(left.get("name") or left.get("label") or "").lower()
    rname = str(right.get("name") or right.get("label") or "").lower()
    if not lname or not rname:
        return False
    return lname == rname or lname.split()[0:1] == rname.split()[0:1]


def _strategy_decision_for_left(left: Mapping[str, Any], rights: Sequence[Mapping[str, Any]], visible: Mapping[str, Any], behavior: str) -> dict[str, Any]:
    mappings = dict(visible.get("field_mappings") or {})
    composite_keys = tuple(visible.get("composite_keys") or ())
    if visible.get("unsupported_shape"):
        return _decision(str(left["key"]), "unsupported", reason="unsupported_input_shape")
    left_id = str(left.get("record_id") or left.get("asset_code") or "")
    right_id_field = mappings.get("record_id") or mappings.get("asset_code") or "record_id"
    id_matches = tuple(right for right in rights if left_id and str(right.get(right_id_field) or right.get("record_id") or right.get("id_code") or "") == left_id)
    if len(id_matches) > 1:
        return _decision(str(left["key"]), "ambiguous", right_keys=tuple(str(item["key"]) for item in id_matches), reason="duplicate_identifier")
    if len(id_matches) == 1:
        right = id_matches[0]
        if left.get("provenance_tag") and right.get("provenance_tag") and left.get("provenance_tag") != right.get("provenance_tag"):
            return _decision(str(left["key"]), "ambiguous", right_keys=(str(right["key"]),), reason="conflicting_provenance")
        return _decision(str(left["key"]), "confirmed", right_keys=(str(right["key"]),), reason="stable_identifier")
    if composite_keys:
        composite_matches = tuple(right for right in rights if _record_value(left, composite_keys) == _record_value(right, composite_keys))
        if len(composite_matches) == 1:
            return _decision(str(left["key"]), "confirmed", right_keys=(str(composite_matches[0]["key"]),), reason="composite_identifier")
    near = tuple(right for right in rights if _similar(left, right))
    if near and behavior == "name_similarity_without_corroboration":
        return _decision(str(left["key"]), "confirmed", right_keys=(str(near[0]["key"]),), reason="name_similarity_without_corroboration")
    if near and any(left.get("entity_class") and right.get("entity_class") and left.get("entity_class") != right.get("entity_class") for right in near):
        return _decision(str(left["key"]), "unmatched", reason="incompatible_entity_class")
    if near:
        return _decision(str(left["key"]), "ambiguous", right_keys=tuple(str(item["key"]) for item in near), reason="near_match_without_corroboration")
    return _decision(str(left["key"]), "unmatched", reason="no_valid_match")


def execute_record_strategy(strategy: Mapping[str, Any], evaluator: Mapping[str, Any], *, visible_cases: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    behavior = str(strategy.get("behavior_profile") or "")
    results: dict[str, Any] = {}
    for case in tuple(visible_cases or evaluator.get("record_level_cases") or ()):
        visible = dict(case.get("strategy_visible_input") or {})
        decisions = tuple(_strategy_decision_for_left(left, tuple(visible.get("right_records") or ()), visible, behavior) for left in tuple(visible.get("left_records") or ()))
        output = _digest_record({
            "schema": "autonomy_4_record_level_strategy_output_v1",
            "case_id": case.get("case_id"),
            "case_category": case.get("case_category"),
            "strategy_id": strategy.get("strategy_id"),
            "evaluator_digest": evaluator.get("artifact_digest"),
            "decisions": decisions,
            "hidden_expected_outputs_seen": False,
            "created_at": FIXED_TIMESTAMP,
        })
        results[str(case["case_id"])] = output
    return results


def _grade_record_case(case: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, Any]:
    expected = tuple(dict(item) for item in tuple(case.get("expected_decisions") or ()))
    actual = tuple(dict(item) for item in tuple(output.get("decisions") or ()))
    failed: list[str] = []
    passed: list[str] = []
    actual_by_left = {str(item.get("left_key")): item for item in actual}
    for expected_item in expected:
        left_key = str(expected_item.get("left_key"))
        actual_item = actual_by_left.get(left_key)
        if not actual_item:
            failed.append(f"missing_decision:{left_key}")
            continue
        for field in ("status", "right_keys"):
            if tuple(actual_item.get(field) or ()) != tuple(expected_item.get(field) or ()) if field == "right_keys" else actual_item.get(field) != expected_item.get(field):
                failed.append(f"{field}_mismatch:{left_key}")
            else:
                passed.append(f"{field}_matched:{left_key}")
        if not tuple(actual_item.get("provenance") or ()):
            failed.append(f"missing_provenance:{left_key}")
        else:
            passed.append(f"provenance_present:{left_key}")
        if actual_item.get("status") == "confirmed" and expected_item.get("status") in {"ambiguous", "unmatched"}:
            failed.append(f"negative_control_false_positive:{left_key}")
    unexpected_confirmed = tuple(item for item in actual if item.get("status") == "confirmed" and str(item.get("left_key")) not in {str(exp.get("left_key")) for exp in expected})
    if unexpected_confirmed:
        failed.append("unexpected_confirmed_match")
    score = max(0, len(passed) - len(failed))
    disposition = "passed" if not failed else "failed"
    return {
        "schema": "autonomy_4_record_level_case_observation_v1",
        "case_id": case.get("case_id"),
        "case_category": case.get("case_category"),
        "strategy_output": output,
        "expected_output_digest": bootstrap_digest(expected),
        "strategy_output_digest": output.get("artifact_digest") or bootstrap_digest(output),
        "passed_assertions": tuple(passed),
        "failed_assertions": tuple(failed),
        "score": score,
        "disposition": disposition,
    }


def compile_fixed_evaluator(plan: Mapping[str, Any]) -> dict[str, Any]:
    cases = _record_level_cases()
    case_categories = tuple(str(case["case_category"]) for case in cases)
    sealed_expected = tuple({"case_id": case["case_id"], "case_category": case["case_category"], "expected_decisions": case["expected_decisions"]} for case in cases)
    return _digest_record({
        "schema": "autonomy_4_fixed_evaluator_v1",
        "evaluator_id": stable_id("autonomy-4-evaluator", plan["plan_id"], tuple(case["semantic_key"] for case in cases)),
        "plan_id": plan["plan_id"],
        "sealed_before_strategy": True,
        "case_categories": case_categories,
        "record_level_cases": cases,
        "sealed_expected_outputs": sealed_expected,
        "sealed_expected_output_digest": bootstrap_digest(sealed_expected),
        "scoring_rules": (
            "confirmed decisions must match expected left and right record keys",
            "ambiguous decisions must preserve all candidate right record keys",
            "unmatched decisions must not fabricate a right record",
            "every decision must include provenance",
            "unsupported input shapes must be rejected instead of matched",
        ),
        "visible_cases": ("exact_stable_identifier", "identifier_missing"),
        "hidden_cases": tuple(case for case in case_categories if case not in {"exact_stable_identifier", "identifier_missing"}),
        "negative_controls": True,
        "transfer_cases": True,
        "negative_control_rules": (
            "forced ambiguous match fails",
            "name-only false positive fails",
            "duplicate identifier overconfidence fails",
            "missing evidence certainty fails",
            "fabricated provenance fails",
            "expected-output replay fails",
        ),
        "transfer_threshold": "all record-level cases must pass",
        "evaluator_authority": "approved_plan_validation_strategy",
        "evaluator_provenance": tuple(plan.get("validation_strategy") or ()),
        "leakage_controls": ("strategy receives no expected hidden outputs",),
        "decision_rule": "all case categories must pass",
        "pass_threshold": len(case_categories),
        "created_at": FIXED_TIMESTAMP,
    })


def compile_strategy(plan: Mapping[str, Any], evaluator: Mapping[str, Any], *, version: str) -> dict[str, Any]:
    family_strategy = compile_family_strategy(plan, evaluator, version=version)
    if family_strategy:
        return family_strategy
    if version in {"initial", "revised_failed"}:
        rules = ("match exact stable id", "use normalized name similarity when id absent", "preserve duplicates as ambiguous")
        behavior = "name_similarity_without_corroboration"
    else:
        rules = ("match exact stable id", "use composite keys when declared", "preserve missing or near-match cases as ambiguous unless corroborated", "preserve duplicates as ambiguous")
        behavior = "require_corroborating_identifier_or_preserve_uncertainty"
    return _digest_record({
        "schema": "autonomy_4_reconciliation_strategy_v1",
        "strategy_id": stable_id("autonomy-4-strategy", plan["plan_id"], evaluator["artifact_digest"], version),
        "plan_id": plan["plan_id"],
        "evaluator_digest": evaluator["artifact_digest"],
        "version": version,
        "behavior_profile": behavior,
        "rules": rules,
        "hidden_expected_outputs_seen": False,
        "created_at": FIXED_TIMESTAMP,
    })


def evaluate_strategy(strategy: Mapping[str, Any], evaluator: Mapping[str, Any]) -> dict[str, Any]:
    family_evaluation = evaluate_family_strategy(strategy, evaluator)
    if family_evaluation:
        return family_evaluation
    integrity = _visible_input_integrity(evaluator)
    if not integrity["passed"]:
        return _digest_record({
            "schema": "autonomy_4_strategy_evaluation_v1",
            "evaluation_id": stable_id("autonomy-4-evaluation", strategy.get("strategy_id"), evaluator.get("artifact_digest"), tuple(integrity["reasons"])),
            "strategy_id": strategy.get("strategy_id"),
            "strategy_digest": strategy.get("artifact_digest"),
            "evaluator_id": evaluator.get("evaluator_id"),
            "evaluator_digest": evaluator.get("artifact_digest"),
            "case_outcomes": (),
            "aggregate_status": "integrity_stop",
            "failed_case_ids": (),
            "failed_case_categories": (),
            "evaluator_weakened": False,
            "integrity_reasons": integrity["reasons"],
            "record_level_evaluation": True,
            "created_at": FIXED_TIMESTAMP,
        })
    outputs = dict(strategy.get("precomputed_outputs") or execute_record_strategy(strategy, evaluator))
    observations = tuple(_grade_record_case(case, dict(outputs.get(str(case["case_id"])) or {})) for case in tuple(evaluator.get("record_level_cases") or ()))
    outcomes = tuple({
        "case_id": observation["case_id"],
        "case_category": observation["case_category"],
        "outcome": "passed" if observation["disposition"] == "passed" else "failed",
        "score": observation["score"],
        "expected_output_digest": observation["expected_output_digest"],
        "strategy_output_digest": observation["strategy_output_digest"],
    } for observation in observations)
    failed = tuple(item for item in outcomes if item["outcome"] != "passed")
    return _digest_record({
        "schema": "autonomy_4_strategy_evaluation_v1",
        "evaluation_id": stable_id("autonomy-4-evaluation", strategy["artifact_digest"], evaluator["artifact_digest"], tuple(item["strategy_output_digest"] for item in outcomes)),
        "strategy_id": strategy["strategy_id"],
        "strategy_digest": strategy["artifact_digest"],
        "evaluator_id": evaluator["evaluator_id"],
        "evaluator_digest": evaluator["artifact_digest"],
        "case_outcomes": outcomes,
        "strategy_outputs": outputs,
        "evaluator_observations": observations,
        "aggregate_status": "passed" if not failed else "revision_required",
        "failed_case_ids": tuple(item["case_id"] for item in failed),
        "failed_case_categories": tuple(item["case_category"] for item in failed),
        "evaluator_weakened": False,
        "record_level_evaluation": True,
        "strategy_identity_used_for_scoring": False,
        "fixture_name_used_for_scoring": False,
        "created_at": FIXED_TIMESTAMP,
    })


def compile_revision(prior_strategy: Mapping[str, Any], evaluation: Mapping[str, Any], evaluator: Mapping[str, Any], *, budget_remaining: int) -> dict[str, Any]:
    family_revision = compile_family_revision(prior_strategy, evaluation, evaluator, budget_remaining=budget_remaining)
    if family_revision:
        return family_revision
    if not evaluation.get("failed_case_ids"):
        raise ValueError("revision_requires_failed_evidence")
    if budget_remaining <= 0:
        raise ValueError("revision_budget_exhausted")
    return _digest_record({
        "schema": "autonomy_4_strategy_revision_v1",
        "revision_id": stable_id("autonomy-4-revision", prior_strategy["strategy_id"], evaluation["artifact_digest"]),
        "prior_strategy_id": prior_strategy["strategy_id"],
        "prior_strategy_digest": prior_strategy["artifact_digest"],
        "failed_evaluator_case_ids": tuple(evaluation["failed_case_ids"]),
        "observed_failure": "near-match similarity was treated as a confirmed match",
        "diagnosed_first_incorrect_transition": "identifier absent -> name similarity -> confirmed match instead of ambiguity",
        "proposed_change": "require corroborating identifier/composite evidence; otherwise preserve ambiguity",
        "expected_effect": "ambiguous and adversarial cases remain unresolved instead of false matched",
        "unchanged_evaluator_digest": evaluator["artifact_digest"],
        "budget_remaining": budget_remaining,
        "authority_confirmation": "within approved one-revision budget",
        "revision_result": "ready_for_revised_strategy",
        "created_at": FIXED_TIMESTAMP,
    })


def final_synthesis(plan: Mapping[str, Any], evaluator: Mapping[str, Any], strategies: Sequence[Mapping[str, Any]], evaluations: Sequence[Mapping[str, Any]], revision: Mapping[str, Any] | None) -> dict[str, Any]:
    final_eval = dict(evaluations[-1])
    disposition = "completed_with_provisional_evidence" if final_eval.get("aggregate_status") == "passed" and revision else "completed_without_revision" if final_eval.get("aggregate_status") == "passed" else "failed_after_revision"
    return _digest_record({
        "schema": "autonomy_4_final_synthesis_v1",
        "cycle_family": evaluator.get("cycle_family") or infer_cycle_family(plan),
        "synthesis_id": stable_id("autonomy-4-final", plan["plan_id"], tuple(ev["artifact_digest"] for ev in evaluations)),
        "goal_id": plan["goal_id"],
        "approved_plan_id": plan["plan_id"],
        "approved_plan_digest": plan["artifact_digest"],
        "actions_completed": tuple(strategy["strategy_id"] for strategy in strategies),
        "strategy_versions": tuple(strategy["version"] for strategy in strategies),
        "evaluator_id": evaluator["evaluator_id"],
        "evaluator_digest": evaluator["artifact_digest"],
        "evaluator_results": tuple(evaluations),
        "failed_cases": tuple(final_eval.get("failed_case_categories") or ()),
        "passed_cases": tuple(item["case_category"] for item in tuple(final_eval.get("case_outcomes") or ()) if item["outcome"] == "passed"),
        "revision_rationale": revision.get("diagnosed_first_incorrect_transition", "") if revision else "",
        "unresolved_limitations": () if disposition != "failed_after_revision" else tuple(final_eval.get("failed_case_categories") or ()),
        "budget_used": {"strategy_attempts": len(strategies), "revisions": 1 if revision else 0},
        "provider_calls": 0,
        "learning_attempts": 1,
        "source_mutation_count": 0,
        "trusted_admission": False,
        "capability_promotion": False,
        "capability_claim": dict(evaluator.get("capability_statement") or {}).get("statement", ""),
        "supported_task_class": dict(evaluator.get("capability_statement") or {}).get("supported_task_class", plan.get("supported_task_class", "")),
        "final_disposition": disposition,
        "provisional_capability_evidence": disposition != "failed_after_revision",
        "created_at": FIXED_TIMESTAMP,
    })


def _prepared_journal(plan: Mapping[str, Any]) -> dict[str, Any]:
    first = tuple(plan.get("proposed_work_items") or ())[0]
    return _digest_record({
        "schema": "autonomy_4_work_item_journal_v1",
        "journal_id": stable_id("autonomy-4-journal", plan["plan_id"], first["work_item_id"], "prepared"),
        "plan_id": plan["plan_id"],
        "plan_digest": plan["artifact_digest"],
        "work_item_id": first["work_item_id"],
        "previous_state": "ready",
        "next_state": "running",
        "phase": "prepared_not_applied",
        "semantic_execution_started": False,
        "created_at": FIXED_TIMESTAMP,
    })


def _expired(authority: Mapping[str, Any], now: Callable[[], datetime] | None) -> bool:
    expires_at = _parse_time(authority.get("expires_at"))
    return bool(expires_at and (now or _utc_now)() >= expires_at)


def _already_terminal(output_root: Path) -> dict[str, Any] | None:
    finals = tuple((Path(output_root) / "final_synthesis").glob("*.json"))
    if not finals:
        return None
    final = _read_json(sorted(finals)[-1])
    return {"status": final.get("final_disposition"), "final_synthesis": final} if final else None


def _existing_boundary_stop(output_root: Path) -> dict[str, Any] | None:
    stops = tuple((Path(output_root) / "boundary_stops").glob("*.json"))
    if not stops:
        return None
    return _read_json(sorted(stops)[-1])


def _persist_strategy_outputs(output_root: Path, evaluation: Mapping[str, Any]) -> None:
    for output in dict(evaluation.get("strategy_outputs") or {}).values():
        if isinstance(output, Mapping):
            _write_json(Path(output_root) / "strategy_outputs" / f"{output['artifact_digest']}.json", output)


def _transition_stage(
    output_root: Path,
    *,
    execution_id: str,
    plan: Mapping[str, Any],
    authority: Mapping[str, Any],
    stage: str,
    previous_state: str,
    next_state: str,
    reason: str,
    source: Mapping[str, Any],
    controller_cycle: int,
) -> dict[str, Any]:
    return persist_work_item_transition(
        output_root,
        execution_id=execution_id,
        goal_id=str(plan["goal_id"]),
        plan_id=str(plan["plan_id"]),
        work_item_id=STAGE_WORK_ITEM_IDS[stage],
        previous_state=previous_state,
        next_state=next_state,
        reason=reason,
        source_artifact_id=str(source.get("journal_id") or source.get("evaluator_id") or source.get("strategy_id") or source.get("evaluation_id") or source.get("revision_id") or source.get("synthesis_id") or source.get("authority_id") or source.get("plan_id")),
        source_artifact_digest=str(source.get("artifact_digest")),
        authority_id=str(authority["authority_id"]),
        controller_cycle=controller_cycle,
    )


def _safe_boundary_stop(
    output_root: Path,
    *,
    status: str,
    reason: str,
    execution_id: str,
    plan: Mapping[str, Any],
    authority: Mapping[str, Any],
    controller_cycle: int,
) -> dict[str, Any]:
    next_state = "paused_operator" if status == "paused_operator" else "stopped_by_operator" if status == "stopped_by_operator" else "authority_expired"
    transition = _transition_stage(
        output_root,
        execution_id=execution_id,
        plan=plan,
        authority=authority,
        stage="execution",
        previous_state="running",
        next_state=next_state,
        reason=reason,
        source=authority,
        controller_cycle=controller_cycle,
    )
    stop = _digest_record({
        "schema": "autonomy_4_execution_boundary_stop_v1",
        "execution_id": execution_id,
        "goal_id": plan["goal_id"],
        "plan_id": plan["plan_id"],
        "authority_id": authority["authority_id"],
        "status": status,
        "reason": reason,
        "transition_id": transition["transition_id"],
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(Path(output_root) / "boundary_stops" / f"{stop['execution_id']}.{status}.json", stop)
    release_execution_lock(output_root)
    return {"status": status, "authority": authority, "boundary_stop": stop, "lifecycle": reconstruct_lifecycle_state(output_root)}


def run_approved_plan_execution(
    plan: Mapping[str, Any],
    approval: Mapping[str, Any],
    *,
    output_root: Path = AUTONOMY_4_ROOT,
    force_revision_fail: bool = False,
    initial_pass: bool = False,
    crash_after_prepared: bool = False,
    pause_after_stage: str | None = None,
    stop_after_stage: str | None = None,
    authority: Mapping[str, Any] | None = None,
    now: Callable[[], datetime] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    output_root = Path(output_root)
    terminal = _already_terminal(output_root)
    if terminal:
        terminal["lifecycle"] = reconstruct_lifecycle_state(output_root)
        return terminal
    existing_stop = _existing_boundary_stop(output_root)
    if existing_stop and existing_stop.get("status") != "paused_operator":
        return {"status": existing_stop.get("status"), "boundary_stop": existing_stop, "lifecycle": reconstruct_lifecycle_state(output_root)}
    if existing_stop and not resume:
        return {"status": "paused_operator", "boundary_stop": existing_stop, "lifecycle": reconstruct_lifecycle_state(output_root)}
    _write_json(output_root / "inputs" / f"{plan['plan_id']}.plan.json", plan)
    _write_json(output_root / "inputs" / f"{approval['approval_id']}.approval.json", approval)
    authority = dict(authority or compile_execution_authority(plan, approval))
    execution_id = stable_id("autonomy-4-execution", authority["authority_id"])
    lock = acquire_execution_lock(output_root, authority)
    if not lock["acquired"]:
        eligibility = validate_execution_eligibility(plan, approval, authority, active_runner_exists=True, now=now)
        _write_json(output_root / "eligibility" / f"{eligibility['eligibility_id']}.json", eligibility)
        return {"status": "duplicate_active_runner", "authority": authority, "eligibility": eligibility, "lock": lock}
    eligibility = validate_execution_eligibility(plan, approval, authority, now=now)
    _write_json(output_root / "authority" / f"{authority['authority_id']}.json", authority)
    _write_json(output_root / "eligibility" / f"{eligibility['eligibility_id']}.json", eligibility)
    if not eligibility["eligible"]:
        release_execution_lock(output_root)
        return {"status": "integrity_stop", "authority": authority, "eligibility": eligibility}
    try:
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="execution", previous_state="ready", next_state="running", reason="operator_approved_plan_execution_started", source=authority, controller_cycle=0)

        def boundary(stage: str, cycle: int) -> dict[str, Any] | None:
            if _expired(authority, now):
                return _safe_boundary_stop(output_root, status="authority_expired", reason=f"authority_expired_before_{stage}", execution_id=execution_id, plan=plan, authority=authority, controller_cycle=cycle)
            if stop_after_stage == stage:
                return _safe_boundary_stop(output_root, status="stopped_by_operator", reason=f"operator_stop_after_{stage}", execution_id=execution_id, plan=plan, authority=authority, controller_cycle=cycle)
            if pause_after_stage == stage:
                return _safe_boundary_stop(output_root, status="paused_operator", reason=f"operator_pause_after_{stage}", execution_id=execution_id, plan=plan, authority=authority, controller_cycle=cycle)
            return None

        journal = _prepared_journal(plan)
        _write_json(output_root / "journal" / f"{journal['journal_id']}.json", journal)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="prepared", previous_state="ready", next_state="running", reason="prepared_journal_started", source=journal, controller_cycle=1)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="prepared", previous_state="running", next_state="completed", reason="prepared_journal_persisted", source=journal, controller_cycle=2)
        if crash_after_prepared:
            return {"status": "interrupted_after_prepared_journal", "authority": authority, "eligibility": eligibility, "journal": journal}
        stopped = boundary("prepared", 2)
        if stopped:
            return stopped

        evaluator = compile_family_evaluator(plan, output_root) or compile_fixed_evaluator(plan)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="evaluator", previous_state="ready", next_state="running", reason="sealed_evaluator_started", source=evaluator, controller_cycle=3)
        _write_json(output_root / "evaluator" / f"{evaluator['evaluator_id']}.json", evaluator)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="evaluator", previous_state="running", next_state="completed", reason="sealed_evaluator_persisted", source=evaluator, controller_cycle=4)
        stopped = boundary("evaluator", 4)
        if stopped:
            return stopped

        initial = compile_strategy(plan, evaluator, version="revised" if initial_pass else "initial")
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="initial_strategy", previous_state="ready", next_state="running", reason="initial_strategy_started", source=initial, controller_cycle=5)
        _write_json(output_root / "strategies" / f"{initial['strategy_id']}.json", initial)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="initial_strategy", previous_state="running", next_state="completed", reason="initial_strategy_persisted", source=initial, controller_cycle=6)
        stopped = boundary("initial_strategy", 6)
        if stopped:
            return stopped

        initial_eval = evaluate_strategy(initial, evaluator)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="initial_evaluation", previous_state="ready", next_state="running", reason="initial_evaluation_started", source=initial_eval, controller_cycle=7)
        _persist_strategy_outputs(output_root, initial_eval)
        _write_json(output_root / "evaluations" / f"{initial_eval['evaluation_id']}.json", initial_eval)
        initial_state = "completed" if initial_eval["aggregate_status"] == "passed" else "failed_evaluation"
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="initial_evaluation", previous_state="running", next_state=initial_state, reason=f"initial_evaluation_{initial_eval['aggregate_status']}", source=initial_eval, controller_cycle=8)
        stopped = boundary("initial_evaluation", 8)
        if stopped:
            return stopped

        strategies = [initial]
        evaluations = [initial_eval]
        revision = None
        if initial_eval["aggregate_status"] != "passed":
            revision = compile_revision(initial, initial_eval, evaluator, budget_remaining=1)
            _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="revision", previous_state="ready", next_state="running", reason="strategy_revision_started", source=revision, controller_cycle=9)
            _write_json(output_root / "revisions" / f"{revision['revision_id']}.json", revision)
            _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="revision", previous_state="running", next_state="revision_required", reason="strategy_revision_required", source=revision, controller_cycle=10)
            stopped = boundary("revision", 10)
            if stopped:
                return stopped

            revised = compile_strategy(plan, evaluator, version="revised_failed" if force_revision_fail else "revised")
            strategies.append(revised)
            _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="revised_strategy", previous_state="revision_required", next_state="running", reason="revised_strategy_started", source=revised, controller_cycle=11)
            _write_json(output_root / "strategies" / f"{revised['strategy_id']}.json", revised)
            _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="revised_strategy", previous_state="running", next_state="completed", reason="revised_strategy_persisted", source=revised, controller_cycle=12)
            stopped = boundary("revised_strategy", 12)
            if stopped:
                return stopped

            revised_eval = evaluate_strategy(revised, evaluator)
            evaluations.append(revised_eval)
            _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="revised_evaluation", previous_state="ready", next_state="running", reason="revised_evaluation_started", source=revised_eval, controller_cycle=13)
            _persist_strategy_outputs(output_root, revised_eval)
            _write_json(output_root / "evaluations" / f"{revised_eval['evaluation_id']}.json", revised_eval)
            revised_state = "completed" if revised_eval["aggregate_status"] == "passed" else "failed_evaluation"
            _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="revised_evaluation", previous_state="running", next_state=revised_state, reason=f"revised_evaluation_{revised_eval['aggregate_status']}", source=revised_eval, controller_cycle=14)
            stopped = boundary("revised_evaluation", 14)
            if stopped:
                return stopped

        synthesis = final_synthesis(plan, evaluator, strategies, evaluations, revision)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="final_synthesis", previous_state="ready", next_state="running", reason="final_synthesis_started", source=synthesis, controller_cycle=15)
        _write_json(output_root / "final_synthesis" / f"{synthesis['synthesis_id']}.json", synthesis)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="final_synthesis", previous_state="running", next_state="completed", reason="final_synthesis_persisted", source=synthesis, controller_cycle=16)
        _transition_stage(output_root, execution_id=execution_id, plan=plan, authority=authority, stage="execution", previous_state="running", next_state="terminal", reason=synthesis["final_disposition"], source=synthesis, controller_cycle=17)
        return {"status": synthesis["final_disposition"], "authority": authority, "eligibility": eligibility, "evaluator": evaluator, "strategies": tuple(strategies), "evaluations": tuple(evaluations), "revision": revision, "final_synthesis": synthesis, "lifecycle": reconstruct_lifecycle_state(output_root)}
    finally:
        if not crash_after_prepared:
            release_execution_lock(output_root)


def resume_paused_execution(
    plan: Mapping[str, Any],
    approval: Mapping[str, Any],
    *,
    output_root: Path = AUTONOMY_4_ROOT,
    **kwargs: Any,
) -> dict[str, Any]:
    return run_approved_plan_execution(plan, approval, output_root=output_root, resume=True, **kwargs)


def recover_prepared_execution(output_root: Path) -> dict[str, Any]:
    output_root = Path(output_root)
    if tuple((output_root / "final_synthesis").glob("*.json")):
        final = _read_json(sorted((output_root / "final_synthesis").glob("*.json"))[-1])
        return {"status": "already_terminal", "final_synthesis": final}
    journals = tuple((output_root / "journal").glob("*.json"))
    if not journals:
        return {"status": "no_recovery_needed"}
    journal = _read_json(sorted(journals)[-1])
    strategies = tuple((output_root / "strategies").glob("*.json"))
    if journal and journal.get("semantic_execution_started") is False and not strategies:
        plan = _read_json(next((output_root / "inputs").glob("*.plan.json")))
        approval = _read_json(next((output_root / "inputs").glob("*.approval.json")))
        release_execution_lock(output_root)
        resumed = run_approved_plan_execution(plan, approval, output_root=output_root)
        return {"status": "resumed_prepared_not_applied", "classification": "prepared_not_applied", "result": resumed}
    return {"status": "integrity_stop", "classification": "applied_state_unknown"}
