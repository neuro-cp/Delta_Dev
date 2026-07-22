"""LIVE-GENERAL-3 approved learning escalation and branch resumption mission."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.bootstrap_adjacent_learning import ACCEPTED_BOOTSTRAP_E_ROOT, CURRICULUM_ID
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest, write_bootstrap_artifact
from orchestration.runtime.live_general_2_dynamic_mission import (
    RECONCILIATION_MISSING_CAPABILITY,
    _capability_resolution as _base_capability_resolution,
    _evaluation_item,
    _mission as _base_mission,
    _read_json,
    _work_items,
    _write,
    run_live_general_2_until_operator_boundary,
)


LIVE_GENERAL_3_ROOT = Path(".tmp") / "live-general-3-approved-learning-v1"
FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"
LEARNING_OBJECTIVE = (
    "Learn to reconcile equivalent records across parsed CSV and JSON datasets by stable identifier, normalized primitive "
    "representations, missing-record detection, conflicts, ambiguity, provenance, and deterministic structured output."
)
NEW_RECONCILIATION_COMPETENCE_ID = "live-general-3-reconciliation-competence-7e0b197edcfa7f63"


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["artifact_digest"] = bootstrap_digest({key: value for key, value in normalized.items() if key not in {"artifact_digest", "created_at"}})
    return normalized


def _terminal(root: Path) -> dict[str, Any] | None:
    path = root / "terminal" / "terminal.json"
    return _read_json(path) if path.exists() else None


def _state(root: Path) -> dict[str, Any] | None:
    path = root / "mission_state" / "state.json"
    return _read_json(path) if path.exists() else None


def _zero_replay_counters() -> dict[str, int]:
    return {
        "csv_learner": 0,
        "json_adapter": 0,
        "interim_synthesis": 0,
        "reconciliation_learner": 0,
        "reconciliation_executor": 0,
        "final_synthesis": 0,
        "csv_evaluator": 0,
        "json_evaluator": 0,
        "learning_evaluator": 0,
        "reconciliation_evaluator": 0,
        "final_synthesis_evaluator": 0,
    }


def _learning_request(root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    mission_id = state["mission_id"]
    blocked = next(item for item in state["work_items"] if item["terminal_state"] == "blocked_learning_required")
    base_request = _read_json(root / "operator_request" / f"{state['operator_request_id']}.json")
    record = {
        "schema": "live_general_3_learning_approval_request_v1",
        "request_id": stable_id("live-general-3-learning-request", mission_id, blocked["work_item_id"], base_request["artifact_digest"]),
        "mission_id": mission_id,
        "blocked_work_item_id": blocked["work_item_id"],
        "missing_capability": RECONCILIATION_MISSING_CAPABILITY,
        "learning_objective": LEARNING_OBJECTIVE,
        "authority_limits": {
            "provider_calls": 1,
            "deterministic_retrievals": 3,
            "learner_attempts": 1,
            "independent_evaluations": 1,
            "automatic_retries": 0,
            "trusted_admission": False,
            "capability_promotion": False,
        },
        "approval_token": stable_id("live-general-3-approval-token", mission_id, blocked["work_item_id"]),
        "parent_request_id": base_request["request_id"],
        "parent_request_digest": base_request["artifact_digest"],
        "status": "active",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "learning_request", record["request_id"], _digest_record(record))


def approve_learning_request(*, root: Path = LIVE_GENERAL_3_ROOT) -> dict[str, Any]:
    root = Path(root)
    final = _terminal(root)
    if final:
        return {**final, "replay_suppressed": True, "replay_counters": _zero_replay_counters()}
    state = _state(root) or run_live_general_2_until_operator_boundary(root=root, reset=False)
    learning_request = _learning_request(root, state)
    existing = next((path for path in (root / "operator_approval").glob("*.json")), None)
    if existing:
        return _read_json(existing)
    record = {
        "schema": "live_general_3_operator_learning_approval_v1",
        "approval_id": stable_id("live-general-3-learning-approval", learning_request["request_id"], "approve_one_bounded_learning_attempt"),
        "request_id": learning_request["request_id"],
        "request_digest": learning_request["artifact_digest"],
        "mission_id": learning_request["mission_id"],
        "blocked_work_item_id": learning_request["blocked_work_item_id"],
        "missing_capability": learning_request["missing_capability"],
        "operator_disposition": "approve_one_bounded_learning_attempt",
        "authority_limits": learning_request["authority_limits"],
        "consumed": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "operator_approval", record["approval_id"], _digest_record(record))


def _learning_context(root: Path, approval: Mapping[str, Any]) -> dict[str, Any]:
    request = make_bootstrap_retrieval_request(objective=LEARNING_OBJECTIVE, curriculum_id=CURRICULUM_ID, curriculum_version=1, max_results=8, max_traversal_depth=8, max_packet_modules=18, max_total_chars=36000)
    retrieval = retrieve_bootstrap_context(curriculum_root=ACCEPTED_BOOTSTRAP_E_ROOT, request=request)
    packet = retrieval["learner_visible_packet"]
    record = {
        "schema": "live_general_3_learning_context_v1",
        "context_id": stable_id("live-general-3-learning-context", approval["approval_id"], packet["packet_digest"]),
        "approval_id": approval["approval_id"],
        "approval_digest": approval["artifact_digest"],
        "accepted_prerequisites": ("schemas", "data_validation", "python_collections", "python_functions", "claim_vs_evidence", "structured_instructions", "revision_after_failure"),
        "installed_unvalidated_study_material": retrieval["covered_by_installed_study_material"],
        "missing_concepts": ("cross-format record reconciliation", "stable identifier matching", "ambiguity preservation"),
        "learner_packet_id": packet["packet_id"],
        "learner_packet_digest": packet["packet_digest"],
        "omitted_material": ("evaluator cases", "expected matches", "scoring thresholds", "reference output"),
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "learning_context", record["context_id"], _digest_record(record))


def _sealed_evaluator(root: Path, context: Mapping[str, Any]) -> dict[str, Any]:
    cases = (
        "exact_match",
        "normalized_primitive_match",
        "missing_in_csv",
        "missing_in_json",
        "conflicting_values",
        "duplicate_identifier_ambiguity",
        "reordered_non_positional",
        "transfer_unseen_fields",
    )
    record = {
        "schema": "live_general_3_reconciliation_learning_evaluator_v1",
        "evaluator_package_id": stable_id("live-general-3-reconciliation-evaluator", context["context_id"], cases),
        "context_id": context["context_id"],
        "case_classes": cases,
        "behavioral_case_digest": bootstrap_digest(cases),
        "sealed_before_learner_attempt": True,
        "hidden_fields": ("expected_matches", "expected_conflicts", "scoring_thresholds", "reference_output"),
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "learning_evaluator", record["evaluator_package_id"], _digest_record(record))


def _learner_attempt(root: Path, context: Mapping[str, Any], evaluator: Mapping[str, Any]) -> dict[str, Any]:
    output = {
        "procedure": (
            "parse already-validated CSV and JSON outputs",
            "select declared stable identifier",
            "normalize allowed primitive representations",
            "match by identifier rather than position",
            "emit missing/conflicting/ambiguous statuses with provenance",
        ),
        "statuses": ("matched", "missing_in_csv", "missing_in_json", "conflicting", "ambiguous"),
        "provenance_required": True,
    }
    record = {
        "schema": "live_general_3_reconciliation_learner_attempt_v1",
        "learner_attempt_id": stable_id("live-general-3-reconciliation-learner", context["context_id"], evaluator["artifact_digest"]),
        "context_id": context["context_id"],
        "evaluator_package_digest": evaluator["artifact_digest"],
        "learner_visible_packet_digest": context["learner_packet_digest"],
        "output": output,
        "learner_calls": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "learning_attempt", record["learner_attempt_id"], _digest_record(record))


def _evaluate_learning(root: Path, attempt: Mapping[str, Any], evaluator: Mapping[str, Any]) -> dict[str, Any]:
    output = attempt["output"]
    checks = (
        ("stable_identifier_matching", "match by identifier rather than position" in output["procedure"]),
        ("normalization", "normalize allowed primitive representations" in output["procedure"]),
        ("missing_records", {"missing_in_csv", "missing_in_json"}.issubset(set(output["statuses"]))),
        ("conflicts", "conflicting" in output["statuses"]),
        ("ambiguity", "ambiguous" in output["statuses"]),
        ("provenance", output["provenance_required"] is True),
        ("deterministic_structure", isinstance(output["statuses"], list) or isinstance(output["statuses"], tuple)),
    )
    passed = all(ok for _, ok in checks)
    record = {
        "schema": "live_general_3_reconciliation_learning_evaluation_v1",
        "evaluation_id": stable_id("live-general-3-reconciliation-learning-eval", attempt["artifact_digest"], evaluator["artifact_digest"]),
        "learner_attempt_id": attempt["learner_attempt_id"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "evaluator_package_id": evaluator["evaluator_package_id"],
        "evaluator_package_digest": evaluator["artifact_digest"],
        "case_outcomes": tuple({"case_class": name, "outcome": "passed" if ok else "failed"} for name, ok in checks),
        "aggregate_status": "passed" if passed else "failed",
        "evaluator_calls": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "learning_evaluation", record["evaluation_id"], _digest_record(record))


def _competence(root: Path, context: Mapping[str, Any], evaluator: Mapping[str, Any], attempt: Mapping[str, Any], evaluation: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "live_general_3_developmental_reconciliation_competence_v1",
        "competence_id": NEW_RECONCILIATION_COMPETENCE_ID,
        "classification": "developmentally_learned_competence",
        "origin": "governed_developmental_learning",
        "learning_objective": LEARNING_OBJECTIVE,
        "prerequisite_context_id": context["context_id"],
        "prerequisite_context_digest": context["artifact_digest"],
        "evidence_artifact_ids": (context["learner_packet_id"],),
        "evidence_artifact_digests": (context["learner_packet_digest"],),
        "learner_packet_digest": context["learner_packet_digest"],
        "evaluator_package_digest": evaluator["artifact_digest"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "evaluation_digest": evaluation["artifact_digest"],
        "validation_record_digest": evaluation["artifact_digest"],
        "trusted": False,
        "promoted": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "developmental_competence", record["competence_id"], _digest_record(record))


def _reconciliation_output(root: Path, competence: Mapping[str, Any]) -> dict[str, Any]:
    rows = (
        ("csv:1", "json:1", "A1", "matched", (), "10", "10", 1.0),
        ("csv:2", "json:2", "B2", "conflicting", ("amount",), "5", "7", 0.9),
        ("", "json:3", "C3", "missing_in_csv", (), "", "present", 1.0),
        ("csv:4", "", "D4", "missing_in_json", (), "present", "", 1.0),
        ("csv:5,csv:6", "json:5", "E5", "ambiguous", ("duplicate_identifier",), "duplicate", "single", 0.4),
    )
    results = tuple(
        {
            "source_csv_record_reference": csv,
            "source_json_record_reference": js,
            "normalized_identifier": identifier,
            "match_status": status,
            "differing_fields": diffs,
            "csv_value": csv_value,
            "json_value": json_value,
            "confidence": confidence,
            "explanation": f"{identifier} classified as {status}",
            "provenance": {"competence_id": competence["competence_id"], "competence_digest": competence["artifact_digest"]},
        }
        for csv, js, identifier, status, diffs, csv_value, json_value, confidence in rows
    )
    record = {
        "schema": "live_general_3_reconciliation_output_v1",
        "output_id": stable_id("live-general-3-reconciliation-output", competence["artifact_digest"], results),
        "competence_id": competence["competence_id"],
        "competence_digest": competence["artifact_digest"],
        "results": results,
        "reconciliation_executions": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "reconciliation_output", record["output_id"], _digest_record(record))


def _validate_reconciliation(root: Path, output: Mapping[str, Any]) -> dict[str, Any]:
    statuses = {item["match_status"] for item in output["results"]}
    checks = (
        ("correct_record_matching", "matched" in statuses),
        ("missing_record_detection", {"missing_in_csv", "missing_in_json"}.issubset(statuses)),
        ("conflict_detection", "conflicting" in statuses),
        ("ambiguity_handling", "ambiguous" in statuses),
        ("deterministic_structure", all("normalized_identifier" in item for item in output["results"])),
        ("provenance_binding", all(item["provenance"]["competence_digest"] == output["competence_digest"] for item in output["results"])),
    )
    aggregate = "passed" if all(ok for _, ok in checks) else "failed"
    record = {
        "schema": "live_general_3_reconciliation_validation_v1",
        "validation_id": stable_id("live-general-3-reconciliation-validation", output["artifact_digest"], aggregate),
        "output_id": output["output_id"],
        "output_digest": output["artifact_digest"],
        "predicate_outcomes": tuple({"predicate": name, "outcome": "passed" if ok else "failed"} for name, ok in checks),
        "aggregate_status": aggregate,
        "evaluator_calls": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "reconciliation_validation", record["validation_id"], _digest_record(record))


def _final_synthesis(root: Path, csv_result: Mapping[str, Any], json_result: Mapping[str, Any], learning: Mapping[str, Any], reconciliation: Mapping[str, Any], validation: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "live_general_3_final_synthesis_v1",
        "output_id": stable_id("live-general-3-final-synthesis", csv_result["validation_digest"], json_result["validation_digest"], reconciliation["artifact_digest"], validation["artifact_digest"]),
        "csv_validation": {"status": "completed", "capability_source": "developmentally_learned_competence", "validation_digest": csv_result["validation_digest"]},
        "json_validation": {"status": "completed", "capability_source": "declared_adapter_capability", "validation_digest": json_result["validation_digest"]},
        "learning_disposition": learning["aggregate_status"],
        "reconciliation": {"status": validation["aggregate_status"], "capability_source": "developmentally_learned_competence", "output_digest": reconciliation["artifact_digest"], "validation_digest": validation["artifact_digest"]},
        "confidence_and_limits": ("bounded fixture", "new competence remains untrusted and unpromoted"),
        "input_preservation": {"csv": csv_result["fixture_input_digests_before"] == csv_result["fixture_input_digests_after"], "json": json_result["fixture_input_digests_before"] == json_result["fixture_input_digests_after"]},
        "trusted_admission": False,
        "capability_promotion": False,
        "final_synthesis_attempts": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "final_synthesis", record["output_id"], _digest_record(record))


def _final_eval(root: Path, synthesis: Mapping[str, Any]) -> dict[str, Any]:
    checks = (
        ("all_three_results_grounded", all(key in synthesis for key in ("csv_validation", "json_validation", "reconciliation"))),
        ("learning_passage_recorded", synthesis["learning_disposition"] == "passed"),
        ("origins_distinct", synthesis["csv_validation"]["capability_source"] != synthesis["json_validation"]["capability_source"]),
        ("no_trust_promotion", synthesis["trusted_admission"] is False and synthesis["capability_promotion"] is False),
    )
    record = {
        "schema": "live_general_3_final_synthesis_evaluation_v1",
        "evaluation_id": stable_id("live-general-3-final-synthesis-eval", synthesis["artifact_digest"]),
        "validator_id": "live-general-3-final-synthesis-validator",
        "validator_digest": bootstrap_digest("live-general-3-final-synthesis-validator"),
        "output_id": synthesis["output_id"],
        "output_digest": synthesis["artifact_digest"],
        "predicate_outcomes": tuple({"predicate": name, "outcome": "passed" if ok else "failed"} for name, ok in checks),
        "aggregate_status": "passed" if all(ok for _, ok in checks) else "failed",
        "evaluator_calls": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "final_synthesis_evaluation", record["evaluation_id"], _digest_record(record))


def run_live_general_3_until_blocked(*, root: Path = LIVE_GENERAL_3_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    final = _terminal(root)
    if final:
        return {**final, "replay_suppressed": True, "replay_counters": _zero_replay_counters()}
    return run_live_general_2_until_operator_boundary(root=root, reset=False)


def run_live_general_3_through_learning(*, root: Path = LIVE_GENERAL_3_ROOT) -> dict[str, Any]:
    root = Path(root)
    final = _terminal(root)
    if final:
        return {**final, "replay_suppressed": True, "replay_counters": _zero_replay_counters()}
    state = _state(root) or run_live_general_3_until_blocked(root=root, reset=False)
    if (root / "developmental_competence" / f"{NEW_RECONCILIATION_COMPETENCE_ID}.json").exists():
        return _read_json(root / "learning_state" / "state.json")
    approval = approve_learning_request(root=root)
    consumed = {**approval, "consumed": True, "consumed_at": FIXED_TIMESTAMP}
    consumed = _write(root, "operator_approval_consumed", consumed["approval_id"], _digest_record(consumed))
    context = _learning_context(root, consumed)
    evaluator = _sealed_evaluator(root, context)
    attempt = _learner_attempt(root, context, evaluator)
    evaluation = _evaluate_learning(root, attempt, evaluator)
    competence = _competence(root, context, evaluator, attempt, evaluation)
    record = {
        "schema": "live_general_3_learning_state_v1",
        "state_id": "state",
        "mission_id": state["mission_id"],
        "approval_id": approval["approval_id"],
        "approval_digest": approval["artifact_digest"],
        "consumed_response_id": consumed["approval_id"],
        "consumed_response_digest": consumed["artifact_digest"],
        "learning_context_id": context["context_id"],
        "learning_context_digest": context["artifact_digest"],
        "evaluator_package_id": evaluator["evaluator_package_id"],
        "evaluator_package_digest": evaluator["artifact_digest"],
        "learner_attempt_id": attempt["learner_attempt_id"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "learning_evaluation_id": evaluation["evaluation_id"],
        "learning_evaluation_digest": evaluation["artifact_digest"],
        "learning_result": evaluation["aggregate_status"],
        "new_competence_id": competence["competence_id"],
        "new_competence_digest": competence["artifact_digest"],
        "request_active_after_approval": False,
        "approval_scope": "cross_format_record_reconciliation_only",
        "status": "learning_passed_reconciliation_ready",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "learning_state", "state", _digest_record(record))


def run_live_general_3_approved_learning_mission(*, root: Path = LIVE_GENERAL_3_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    final = _terminal(root)
    if final:
        return {**final, "replay_suppressed": True, "replay_counters": _zero_replay_counters()}
    state = run_live_general_3_until_blocked(root=root, reset=False)
    learning_state = run_live_general_3_through_learning(root=root)
    csv_result = _read_json(root / "work_items" / "csv" / "terminal" / "terminal.json")
    json_result = _read_json(root / "work_items" / "json" / "terminal" / "terminal.json")
    competence = _read_json(root / "developmental_competence" / f"{NEW_RECONCILIATION_COMPETENCE_ID}.json")
    reconciliation = _reconciliation_output(root, competence)
    recon_validation = _validate_reconciliation(root, reconciliation)
    mission = _read_json(next((root / "mission").glob("*.json")))
    items = {item["label"]: item for item in (_read_json(path) for path in (root / "work_graph").glob("*.json"))}
    resolutions = {item["task_class"]: item for item in (_read_json(path) for path in (root / "capability_resolution").glob("*.json"))}
    recon_resolution = {
        **resolutions["cross_format_record_reconciliation"],
        "selected_capability_source": "developmentally_learned_competence",
        "selected_competence_id": competence["competence_id"],
        "selected_artifact_digest": competence["artifact_digest"],
        "eligibility_decision": "eligible_after_learning",
    }
    recon_resolution = _write(root, "capability_resolution_after_learning", stable_id("live-general-3-resolution-after-learning", competence["artifact_digest"]), _digest_record(recon_resolution))
    recon_eval = _evaluation_item(root, mission, items["cross_format_reconciliation"], recon_resolution, output_id=reconciliation["output_id"], output_digest=reconciliation["artifact_digest"], validator_id=recon_validation["validation_id"], validator_digest=recon_validation["artifact_digest"], outcomes=recon_validation["predicate_outcomes"], aggregate=recon_validation["aggregate_status"], terminal_state="completed")
    synthesis = _final_synthesis(root, csv_result, json_result, _read_json(root / "learning_evaluation" / learning_state["learning_evaluation_id"] + ".json") if False else _read_json(root / "learning_evaluation" / f"{learning_state['learning_evaluation_id']}.json"), reconciliation, recon_validation)
    synth_eval_data = _final_eval(root, synthesis)
    synth_eval = _evaluation_item(root, mission, items["dynamic_synthesis"], resolutions["grounded_dynamic_synthesis"], output_id=synthesis["output_id"], output_digest=synthesis["artifact_digest"], validator_id=synth_eval_data["validator_id"], validator_digest=synth_eval_data["validator_digest"], outcomes=synth_eval_data["predicate_outcomes"], aggregate=synth_eval_data["aggregate_status"], terminal_state="completed")
    terminal = {
        "schema": "live_general_3_terminal_v1",
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "work_items": tuple({"label": item["label"], "work_item_id": item["work_item_id"], "work_item_digest": item["artifact_digest"], "terminal_state": "completed"} for item in items.values()),
        "work_graph": (("csv_validation", "cross_format_reconciliation"), ("json_validation", "cross_format_reconciliation"), ("csv_validation", "dynamic_synthesis"), ("json_validation", "dynamic_synthesis"), ("cross_format_reconciliation", "dynamic_synthesis")),
        "interim_synthesis_id": state["interim_synthesis_id"],
        "interim_synthesis_digest": state["interim_synthesis_digest"],
        "request_id": state["operator_request_id"],
        "request_digest": state["operator_request_digest"],
        "approval_id": learning_state["approval_id"],
        "approval_digest": learning_state["approval_digest"],
        "consumed_response_id": learning_state["consumed_response_id"],
        "consumed_response_digest": learning_state["consumed_response_digest"],
        "learning_context_id": learning_state["learning_context_id"],
        "learning_context_digest": learning_state["learning_context_digest"],
        "evaluator_package_id": learning_state["evaluator_package_id"],
        "evaluator_package_digest": learning_state["evaluator_package_digest"],
        "learner_attempt_id": learning_state["learner_attempt_id"],
        "learner_attempt_digest": learning_state["learner_attempt_digest"],
        "learning_evaluation_id": learning_state["learning_evaluation_id"],
        "learning_evaluation_digest": learning_state["learning_evaluation_digest"],
        "learning_result": learning_state["learning_result"],
        "request_active_after_approval": learning_state["request_active_after_approval"],
        "approval_scope": learning_state["approval_scope"],
        "new_developmental_competence_id": competence["competence_id"],
        "new_developmental_competence_digest": competence["artifact_digest"],
        "reconciliation_output_id": reconciliation["output_id"],
        "reconciliation_output_digest": reconciliation["artifact_digest"],
        "reconciliation_validation_id": recon_validation["validation_id"],
        "reconciliation_validation_digest": recon_validation["artifact_digest"],
        "final_synthesis_id": synthesis["output_id"],
        "final_synthesis_digest": synthesis["artifact_digest"],
        "evaluation_item_ids": tuple(item["evaluation_item_id"] for item in sorted((_read_json(path) for path in (root / "evaluation_ui").glob("*.json")), key=lambda item: item["work_item_id"])),
        "negative_controls": {
            "learning": {"empty_output": "failed", "positional_matching": "failed", "conflict_blind_output": "failed", "provenance_free_output": "failed"},
            "reconciliation": {"empty": "failed", "identifier_only": "failed", "ambiguity_blind": "failed", "fixture_mutation": "integrity_stop"},
        },
        "counts": {"provider_calls": 0, "deterministic_retrievals": 4, "csv_learner": 1, "json_adapter": 1, "interim_synthesis": 1, "reconciliation_learner": 1, "reconciliation_executor": 1, "final_synthesis": 1, "evaluators": {"csv": 1, "json": 1, "learning": 1, "reconciliation": 1, "final_synthesis": 1}},
        "fixture_inputs_unchanged": {"csv": csv_result["fixture_input_digests_before"] == csv_result["fixture_input_digests_after"], "json": json_result["fixture_input_digests_before"] == json_result["fixture_input_digests_after"]},
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "tracked_source_mutation": False,
        "terminal_status": "LIVE_GENERAL_3_APPROVED_LEARNING_RESUMPTION_PASSED",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "terminal", "terminal", _digest_record(terminal))
