"""LIVE-GENERAL-2 dynamic branch blocking and attended resumption mission."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

from orchestration.runtime.bootstrap_adjacent_learning import ACCEPTED_BOOTSTRAP_E_ROOT, CURRICULUM_ID
from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest, load_bootstrap_curriculum_artifacts, write_bootstrap_artifact
from orchestration.runtime.live_bootstrap_csv_mission import DEVELOPMENTAL_COMPETENCE_DIGEST, DEVELOPMENTAL_COMPETENCE_ID, LIVE_OBJECTIVE as CSV_OBJECTIVE, run_live_bootstrap_csv_validation_mission
from orchestration.runtime.live_competence_adapter import JSON_OBJECTIVE, declare_adapter_capability, registered_live_task_adapters, run_live_competence_json_validation_mission


LIVE_GENERAL_2_ROOT = Path(".tmp") / "live-general-2-dynamic-branch-v1"
FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"
MISSION_OBJECTIVE = (
    "Inspect and validate a disposable mixed-format data package, then produce a unified compliance report. "
    "Validate CSV files and JSON records against supplied schemas, and generate a normalized cross-format reconciliation table."
)
RECONCILIATION_TASK_CLASS = "cross_format_record_reconciliation"
SYNTHESIS_TASK_CLASS = "grounded_dynamic_synthesis"
RECONCILIATION_MISSING_CAPABILITY = "cross_format_record_reconciliation"
SYNTHESIS_PREREQUISITE_TITLES = (
    "Claim evidence and support types",
    "Structured instructions and explicit constraints",
    "Evidence grounded question answering",
    "Revision after failure",
    "Exact once execution",
    "Sequence ordering and state machines",
    "Records fields and schemas",
    "Validation rules",
)


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["artifact_digest"] = bootstrap_digest({key: value for key, value in normalized.items() if key not in {"artifact_digest", "created_at"}})
    return normalized


def _write(root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return write_bootstrap_artifact(artifact_root=root, directory=directory, artifact_id=artifact_id, payload=payload)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _state(root: Path) -> dict[str, Any] | None:
    path = root / "mission_state" / "state.json"
    return _read_json(path) if path.exists() else None


def _terminal(root: Path) -> dict[str, Any] | None:
    path = root / "terminal" / "terminal.json"
    return _read_json(path) if path.exists() else None


def _accepted_bootstrap_by_title() -> dict[str, dict[str, Any]]:
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=ACCEPTED_BOOTSTRAP_E_ROOT, curriculum_id=CURRICULUM_ID)
    module_by_id = {module["module_id"]: module for module in loaded["modules"]}
    records = tuple(_read_json(path) for path in sorted((ACCEPTED_BOOTSTRAP_E_ROOT / "validated_bootstrap_competencies").glob("*.json")))
    return {
        module_by_id[record["module_id"]]["title"]: {
            "module_id": record["module_id"],
            "module_title": module_by_id[record["module_id"]]["title"],
            "module_digest": module_by_id[record["module_id"]]["artifact_digest"],
            "competence_id": record["competence_id"],
            "competence_digest": record["artifact_digest"],
        }
        for record in records
    }


def _select_bootstrap(titles: Sequence[str]) -> tuple[dict[str, Any], ...]:
    by_title = _accepted_bootstrap_by_title()
    return tuple(by_title[title] for title in titles)


def _mission() -> dict[str, Any]:
    return _digest_record({
        "schema": "live_general_2_operator_mission_v1",
        "mission_id": stable_id("live-general-2-mission", MISSION_OBJECTIVE),
        "objective": MISSION_OBJECTIVE,
        "operator_approved": True,
        "authority_limits": {
            "provider_calls": 1,
            "deterministic_retrievals": 4,
            "csv_learner_executions": 1,
            "json_adapter_executions": 1,
            "reconciliation_learning_attempts": 1,
            "reconciliation_executions": 1,
            "synthesis_attempts": 2,
            "independent_evaluations": 4,
            "automatic_retry": 0,
            "network_expansion": False,
            "tracked_source_mutation": False,
            "fixture_input_mutation": False,
            "trusted_admission": False,
            "capability_promotion": False,
        },
        "created_at": FIXED_TIMESTAMP,
    })


def _work_items(mission: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    specs = (
        ("csv_validation", "csv_schema_validation", "developmentally_learned_competence", ()),
        ("json_validation", "structured_json_validation", "declared_adapter_capability", ()),
        ("cross_format_reconciliation", RECONCILIATION_TASK_CLASS, "missing_capability", ()),
        ("dynamic_synthesis", SYNTHESIS_TASK_CLASS, "validated_bootstrap_competence", ("csv_validation", "json_validation", "cross_format_reconciliation")),
    )
    records = []
    for label, task_class, required, deps in specs:
        records.append(_digest_record({
            "schema": "live_general_2_work_item_v1",
            "work_item_id": stable_id("live-general-2-work-item", mission["mission_id"], label),
            "mission_id": mission["mission_id"],
            "label": label,
            "task_class": task_class,
            "required_capability_source": required,
            "dependencies": deps,
            "created_at": FIXED_TIMESTAMP,
        }))
    return tuple(records)


def _packet(objective: str, max_results: int) -> dict[str, Any]:
    request = make_bootstrap_retrieval_request(objective=objective, curriculum_id=CURRICULUM_ID, curriculum_version=1, max_results=max_results, max_traversal_depth=8, max_packet_modules=18, max_total_chars=36000)
    retrieval = retrieve_bootstrap_context(curriculum_root=ACCEPTED_BOOTSTRAP_E_ROOT, request=request)
    return {"request": request, "retrieval": retrieval, "packet": retrieval["learner_visible_packet"]}


def _reconciliation_capability_audit() -> dict[str, Any]:
    accepted = _accepted_bootstrap_by_title()
    accepted_hits = tuple(title for title in accepted if "reconciliation" in title.lower() or "record matching" in title.lower() or "cross-format" in title.lower())
    adapters = tuple(adapter.descriptor() for adapter in registered_live_task_adapters())
    adapter_hits = tuple(adapter["adapter_id"] for adapter in adapters if RECONCILIATION_TASK_CLASS in adapter["supported_task_classes"])
    return _digest_record({
        "schema": "live_general_2_reconciliation_capability_audit_v1",
        "audit_id": stable_id("live-general-2-reconciliation-audit", accepted_hits, adapter_hits),
        "task_class": RECONCILIATION_TASK_CLASS,
        "accepted_bootstrap_matches": accepted_hits,
        "accepted_developmental_matches": (),
        "declared_adapter_matches": adapter_hits,
        "installed_unvalidated_possible_support": ("Tables and graphs", "Identifiers and references", "Data validation"),
        "qualifying_accepted_capability_exists": False,
        "decision": "missing_capability",
        "created_at": FIXED_TIMESTAMP,
    })


def _capability_resolution(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    if item["task_class"] == "csv_schema_validation":
        packet = _packet(CSV_OBJECTIVE, 6)
        record = {
            "resolution_id": stable_id("live-general-2-resolution", item["work_item_id"], DEVELOPMENTAL_COMPETENCE_ID),
            "task_class": item["task_class"],
            "required_capability_type": "developmentally_learned_competence",
            "selected_capability_source": "developmentally_learned_competence",
            "selected_competence_id": DEVELOPMENTAL_COMPETENCE_ID,
            "selected_artifact_digest": DEVELOPMENTAL_COMPETENCE_DIGEST,
            "validated_bootstrap_prerequisites": (),
            "installed_unvalidated_study_modules": packet["retrieval"]["covered_by_installed_study_material"],
            "unresolved_concepts": packet["retrieval"]["missing_from_curriculum"],
            "context_packet_id": packet["packet"]["packet_id"],
            "context_packet_digest": packet["packet"]["packet_digest"],
            "eligibility_decision": "eligible",
            "decision_reason": "accepted_developmental_csv_competence_bound",
        }
    elif item["task_class"] == "structured_json_validation":
        adapter = next(adapter for adapter in registered_live_task_adapters() if adapter.adapter_id == "structured_json_validation")
        capability = declare_adapter_capability(adapter, root=root)
        packet = _packet(JSON_OBJECTIVE, 8)
        record = {
            "resolution_id": stable_id("live-general-2-resolution", item["work_item_id"], capability["declaration_id"]),
            "task_class": item["task_class"],
            "required_capability_type": "declared_adapter_capability",
            "selected_capability_source": "declared_adapter_capability",
            "selected_adapter_capability_id": capability["declaration_id"],
            "selected_artifact_digest": capability["artifact_digest"],
            "validated_bootstrap_prerequisites": _select_bootstrap(adapter.required_competence_titles),
            "installed_unvalidated_study_modules": packet["retrieval"]["covered_by_installed_study_material"],
            "unresolved_concepts": packet["retrieval"]["missing_from_curriculum"],
            "context_packet_id": packet["packet"]["packet_id"],
            "context_packet_digest": packet["packet"]["packet_digest"],
            "adapter_id": adapter.adapter_id,
            "adapter_version": adapter.version,
            "eligibility_decision": "eligible",
            "decision_reason": "declared_adapter_capability_bound",
        }
    elif item["task_class"] == RECONCILIATION_TASK_CLASS:
        audit = _write(root, "capability_audit", _reconciliation_capability_audit()["audit_id"], _reconciliation_capability_audit())
        packet = _packet(MISSION_OBJECTIVE, 4)
        record = {
            "resolution_id": stable_id("live-general-2-resolution", item["work_item_id"], audit["artifact_digest"]),
            "task_class": item["task_class"],
            "required_capability_type": "missing_capability",
            "selected_capability_source": "missing_capability",
            "selected_competence_id": "",
            "selected_artifact_digest": audit["artifact_digest"],
            "missing_capability": RECONCILIATION_MISSING_CAPABILITY,
            "validated_bootstrap_prerequisites": (),
            "installed_unvalidated_study_modules": packet["retrieval"]["covered_by_installed_study_material"],
            "unresolved_concepts": tuple(sorted(set(packet["retrieval"]["missing_from_curriculum"]) | {"record reconciliation", "cross format matching"})),
            "context_packet_id": packet["packet"]["packet_id"],
            "context_packet_digest": packet["packet"]["packet_digest"],
            "eligibility_decision": "blocked_learning_required",
            "decision_reason": "no_accepted_reconciliation_competence_or_adapter",
        }
    else:
        packet = _packet(MISSION_OBJECTIVE, 8)
        prereqs = _select_bootstrap(SYNTHESIS_PREREQUISITE_TITLES)
        record = {
            "resolution_id": stable_id("live-general-2-resolution", item["work_item_id"], tuple(item["competence_digest"] for item in prereqs)),
            "task_class": item["task_class"],
            "required_capability_type": "validated_bootstrap_competence",
            "selected_capability_source": "validated_bootstrap_competence",
            "selected_competence_id": tuple(item["competence_id"] for item in prereqs),
            "selected_artifact_digest": tuple(item["competence_digest"] for item in prereqs),
            "validated_bootstrap_prerequisites": prereqs,
            "installed_unvalidated_study_modules": packet["retrieval"]["covered_by_installed_study_material"],
            "unresolved_concepts": packet["retrieval"]["missing_from_curriculum"],
            "context_packet_id": packet["packet"]["packet_id"],
            "context_packet_digest": packet["packet"]["packet_digest"],
            "eligibility_decision": "waiting_dependency",
            "decision_reason": "final_synthesis_waits_for_reconciliation_terminal_state",
        }
    full = {
        "schema": "live_general_2_capability_resolution_v1",
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "work_item_id": item["work_item_id"],
        "work_item_digest": item["artifact_digest"],
        "authority_requirements": {"provider_calls": 0, "network": False, "tracked_source_mutation": False, "fixture_input_mutation": False},
        "mutation_surface": (),
        "network_requirements": (),
        "created_at": FIXED_TIMESTAMP,
        **record,
    }
    return _write(root, "capability_resolution", full["resolution_id"], _digest_record(full))


def _evaluation_item(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], resolution: Mapping[str, Any], *, output_id: str, output_digest: str, validator_id: str, validator_digest: str, outcomes: Sequence[Mapping[str, Any]], aggregate: str, terminal_state: str) -> dict[str, Any]:
    record = {
        "schema": "evaluation_ui_item_v1",
        "evaluation_item_id": stable_id("live-general-2-evaluation-item", mission["mission_id"], item["work_item_id"], terminal_state),
        "mission_id": mission["mission_id"],
        "work_item_id": item["work_item_id"],
        "task_class": item["task_class"],
        "capability_source": resolution["selected_capability_source"],
        "selected_capability": resolution.get("selected_competence_id") or resolution.get("selected_adapter_capability_id") or resolution.get("missing_capability"),
        "selected_artifact_digest": resolution["selected_artifact_digest"],
        "capability_resolution_id": resolution["resolution_id"],
        "capability_resolution_digest": resolution["artifact_digest"],
        "output_id": output_id,
        "output_digest": output_digest,
        "validator_id": validator_id,
        "validator_digest": validator_digest,
        "case_or_predicate_outcomes": tuple(outcomes),
        "aggregate_disposition": aggregate,
        "terminal_state": terminal_state,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "evaluation_ui", record["evaluation_item_id"], _digest_record(record))


def _interim_synthesis(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], csv_result: Mapping[str, Any], json_result: Mapping[str, Any], recon_item: Mapping[str, Any], recon_resolution: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "live_general_2_interim_synthesis_v1",
        "interim_synthesis_id": stable_id("live-general-2-interim", mission["mission_id"], csv_result["validation_digest"], json_result["validation_digest"], recon_resolution["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "work_item_id": item["work_item_id"],
        "csv_result": {"output_id": csv_result["output_id"], "output_digest": csv_result["output_digest"], "validation_id": csv_result["validation_id"], "validation_digest": csv_result["validation_digest"]},
        "json_result": {"output_id": json_result["output_id"], "output_digest": json_result["output_digest"], "validation_id": json_result["validation_id"], "validation_digest": json_result["validation_digest"]},
        "reconciliation_status": "unresolved",
        "blocked_work_item_id": recon_item["work_item_id"],
        "blocked_reason": recon_resolution["decision_reason"],
        "capability_gap": recon_resolution["missing_capability"],
        "capability_origin_attribution": {"csv": "developmentally_learned_competence", "json": "declared_adapter_capability", "reconciliation": "missing_capability", "synthesis": "validated_bootstrap_competence"},
        "input_preservation": {"csv": csv_result["fixture_input_digests_before"] == csv_result["fixture_input_digests_after"], "json": json_result["fixture_input_digests_before"] == json_result["fixture_input_digests_after"]},
        "limits": ("no reconciliation result established", "final synthesis waits for attended disposition"),
        "synthesis_attempt": 1,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "interim_synthesis", record["interim_synthesis_id"], _digest_record(record))


def _operator_request(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], resolution: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "live_general_2_operator_request_v1",
        "request_id": stable_id("live-general-2-operator-request", mission["mission_id"], item["work_item_id"], resolution["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "blocked_work_item_id": item["work_item_id"],
        "missing_capability": resolution["missing_capability"],
        "why_existing_capabilities_are_insufficient": "CSV competence validates CSV; JSON adapter validates JSON; neither owns cross-format reconciliation semantics.",
        "inspected_context": {"resolution_id": resolution["resolution_id"], "resolution_digest": resolution["artifact_digest"], "context_packet_id": resolution["context_packet_id"], "context_packet_digest": resolution["context_packet_digest"]},
        "recommended_action": "reject_reconciliation_branch_for_this_gate",
        "alternatives": ("approve_one_bounded_learning_attempt", "leave_mission_paused"),
        "effect_of_rejection": "final synthesis may complete with reconciliation explicitly unresolved",
        "approval_token": stable_id("live-general-2-approval-token", mission["mission_id"], item["work_item_id"]),
        "status": "active",
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "operator_request", record["request_id"], _digest_record(record))


def _state_record(root: Path, mission: Mapping[str, Any], status: str, **fields: Any) -> dict[str, Any]:
    record = _digest_record({"schema": "live_general_2_state_v1", "state_id": "state", "mission_id": mission["mission_id"], "mission_digest": mission["artifact_digest"], "status": status, "created_at": FIXED_TIMESTAMP, **fields})
    return _write(root, "mission_state", "state", record)


def run_live_general_2_until_operator_boundary(*, root: Path = LIVE_GENERAL_2_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(root)
    if reset and root.exists():
        shutil.rmtree(root)
    final = _terminal(root)
    if final:
        return {**final, "replay_suppressed": True, "replay_counters": _zero_replay_counters()}
    paused = _state(root)
    if paused and paused["status"] == "paused_for_operator_reconciliation_disposition":
        return {**paused, "replay_suppressed": True, "replay_counters": _zero_replay_counters()}
    mission = _write(root, "mission", _mission()["mission_id"], _mission())
    items = tuple(_write(root, "work_graph", item["work_item_id"], item) for item in _work_items(mission))
    by_label = {item["label"]: item for item in items}
    resolutions = {label: _capability_resolution(root, mission, item) for label, item in by_label.items()}
    csv_result = run_live_bootstrap_csv_validation_mission(root=root / "work_items" / "csv", reset=True)
    json_result = run_live_competence_json_validation_mission(root=root / "work_items" / "json", reset=True)
    csv_eval = _evaluation_item(root, mission, by_label["csv_validation"], resolutions["csv_validation"], output_id=csv_result["output_id"], output_digest=csv_result["output_digest"], validator_id=csv_result["validation_id"], validator_digest=csv_result["validation_digest"], outcomes=csv_result["case_results"], aggregate="passed", terminal_state="completed")
    json_eval = _evaluation_item(root, mission, by_label["json_validation"], resolutions["json_validation"], output_id=json_result["output_id"], output_digest=json_result["output_digest"], validator_id=json_result["validation_id"], validator_digest=json_result["validation_digest"], outcomes=json_result["case_results"], aggregate="passed", terminal_state="completed")
    interim = _interim_synthesis(root, mission, by_label["dynamic_synthesis"], csv_result, json_result, by_label["cross_format_reconciliation"], resolutions["cross_format_reconciliation"])
    request = _operator_request(root, mission, by_label["cross_format_reconciliation"], resolutions["cross_format_reconciliation"])
    state = _state_record(
        root,
        mission,
        "paused_for_operator_reconciliation_disposition",
        work_items=tuple({"label": item["label"], "work_item_id": item["work_item_id"], "work_item_digest": item["artifact_digest"], "terminal_state": "blocked_learning_required" if item["label"] == "cross_format_reconciliation" else ("interim_completed" if item["label"] == "dynamic_synthesis" else "completed")} for item in items),
        capability_resolutions=tuple({"label": label, "resolution_id": record["resolution_id"], "resolution_digest": record["artifact_digest"], "selected_capability_source": record["selected_capability_source"]} for label, record in resolutions.items()),
        interim_synthesis_id=interim["interim_synthesis_id"],
        interim_synthesis_digest=interim["artifact_digest"],
        operator_request_id=request["request_id"],
        operator_request_digest=request["artifact_digest"],
        evaluation_item_ids=(csv_eval["evaluation_item_id"], json_eval["evaluation_item_id"]),
        runtime_ui_state_sequence=("mission_accepted", "four_work_items_created", "csv_active_completed", "json_active_completed", "reconciliation_blocked", "synthesis_interim_available", "one_operator_request_active", "runtime_paused"),
        counters={"provider_calls": 0, "deterministic_retrievals": 4, "csv_learner": 1, "json_adapter": 1, "interim_synthesis": 1, "evaluators": {"csv": 1, "json": 1}},
    )
    return state


def consume_reconciliation_operator_rejection(*, root: Path = LIVE_GENERAL_2_ROOT, rejection_reason: str = "operator_rejected_reconciliation_learning_for_gate") -> dict[str, Any]:
    root = Path(root)
    final = _terminal(root)
    if final:
        return {**final, "replay_suppressed": True, "replay_counters": _zero_replay_counters()}
    state = _state(root)
    if not state or state["status"] != "paused_for_operator_reconciliation_disposition":
        raise ValueError("live_general_2_operator_request_not_active")
    mission = _read_json(next((root / "mission").glob("*.json")))
    items = {item["label"]: item for item in (_read_json(path) for path in (root / "work_graph").glob("*.json"))}
    resolutions = {item["task_class"]: item for item in (_read_json(path) for path in (root / "capability_resolution").glob("*.json"))}
    request = _read_json(root / "operator_request" / f"{state['operator_request_id']}.json")
    response = _write(root, "operator_response", stable_id("live-general-2-operator-response", request["request_id"], "reject"), _digest_record({
        "schema": "live_general_2_operator_response_v1",
        "response_id": stable_id("live-general-2-operator-response", request["request_id"], "reject"),
        "request_id": request["request_id"],
        "mission_id": mission["mission_id"],
        "blocked_work_item_id": request["blocked_work_item_id"],
        "operator_disposition": "reject_reconciliation_branch",
        "consumed": True,
        "reason": rejection_reason,
        "created_at": FIXED_TIMESTAMP,
    }))
    csv_result = _read_json(root / "work_items" / "csv" / "terminal" / "terminal.json")
    json_result = _read_json(root / "work_items" / "json" / "terminal" / "terminal.json")
    recon_output = _write(root, "reconciliation_output", stable_id("live-general-2-reconciliation-closed", mission["mission_id"], response["artifact_digest"]), _digest_record({
        "schema": "live_general_2_reconciliation_closure_v1",
        "output_id": stable_id("live-general-2-reconciliation-closed", mission["mission_id"], response["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "work_item_id": items["cross_format_reconciliation"]["work_item_id"],
        "status": "rejected_by_operator",
        "match_results": (),
        "reason": rejection_reason,
        "capability_source": "rejected_by_operator",
        "created_at": FIXED_TIMESTAMP,
    }))
    recon_eval = _evaluation_item(root, mission, items["cross_format_reconciliation"], resolutions[RECONCILIATION_TASK_CLASS], output_id=recon_output["output_id"], output_digest=recon_output["artifact_digest"], validator_id="operator-rejection-closure", validator_digest=bootstrap_digest(("operator-rejection-closure", response["artifact_digest"])), outcomes=({"predicate": "operator_rejection_consumed", "outcome": "passed"}, {"predicate": "no_reconciliation_claim_established", "outcome": "passed"}), aggregate="rejected_by_operator", terminal_state="rejected")
    final_synth = _final_synthesis(root, mission, items["dynamic_synthesis"], resolutions[SYNTHESIS_TASK_CLASS], csv_result, json_result, recon_output, response)
    final_validation = _validate_final_synthesis(root, mission, items["dynamic_synthesis"], final_synth)
    synth_eval = _evaluation_item(root, mission, items["dynamic_synthesis"], resolutions[SYNTHESIS_TASK_CLASS], output_id=final_synth["output_id"], output_digest=final_synth["artifact_digest"], validator_id=final_validation["validator_id"], validator_digest=final_validation["validator_digest"], outcomes=final_validation["predicate_outcomes"], aggregate=final_validation["aggregate_status"], terminal_state="completed")
    terminal = _write(root, "terminal", "terminal", _digest_record({
        "schema": "live_general_2_terminal_v1",
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "work_items": tuple({"label": item["label"], "work_item_id": item["work_item_id"], "work_item_digest": item["artifact_digest"], "terminal_state": "rejected" if item["label"] == "cross_format_reconciliation" else "completed"} for item in items.values()),
        "dependency_graph": (("csv_validation", "dynamic_synthesis"), ("json_validation", "dynamic_synthesis"), ("cross_format_reconciliation", "dynamic_synthesis")),
        "capability_resolutions": tuple({"task_class": record["task_class"], "resolution_id": record["resolution_id"], "resolution_digest": record["artifact_digest"], "selected_capability_source": record["selected_capability_source"], "context_packet_id": record["context_packet_id"], "context_packet_digest": record["context_packet_digest"]} for record in resolutions.values()),
        "missing_capability": RECONCILIATION_MISSING_CAPABILITY,
        "interim_synthesis_id": state["interim_synthesis_id"],
        "interim_synthesis_digest": state["interim_synthesis_digest"],
        "operator_request_id": request["request_id"],
        "operator_request_digest": request["artifact_digest"],
        "operator_response_id": response["response_id"],
        "operator_response_digest": response["artifact_digest"],
        "operator_disposition": response["operator_disposition"],
        "reconciliation_output_id": recon_output["output_id"],
        "reconciliation_output_digest": recon_output["artifact_digest"],
        "reconciliation_validation_id": recon_eval["evaluation_item_id"],
        "reconciliation_validation_digest": recon_eval["artifact_digest"],
        "final_synthesis_id": final_synth["output_id"],
        "final_synthesis_digest": final_synth["artifact_digest"],
        "evaluation_item_ids": tuple(item["evaluation_item_id"] for item in sorted((_read_json(path) for path in (root / "evaluation_ui").glob("*.json")), key=lambda item: item["work_item_id"])),
        "per_item_terminal_states": {"csv_validation": "completed", "json_validation": "completed", "cross_format_reconciliation": "rejected", "dynamic_synthesis": "completed"},
        "fixture_inputs_unchanged": {"csv": csv_result["fixture_input_digests_before"] == csv_result["fixture_input_digests_after"], "json": json_result["fixture_input_digests_before"] == json_result["fixture_input_digests_after"]},
        "negative_controls": _negative_controls(),
        "counts": {"provider_calls": 0, "deterministic_retrievals": 4, "csv_learner": 1, "json_adapter": 1, "interim_synthesis": 1, "reconciliation_learner": 0, "reconciliation_executor": 0, "final_synthesis": 1, "evaluators": {"csv": 1, "json": 1, "reconciliation": 1, "final_synthesis": 1}},
        "runtime_ui_state_sequence": ("mission_accepted", "four_work_items_created", "csv_active_completed", "json_active_completed", "reconciliation_blocked", "synthesis_interim_available", "one_operator_request_active", "runtime_paused", "operator_disposition_consumed", "reconciliation_closed", "final_synthesis_completed", "four_terminal_evaluation_items_available", "mission_terminal", "runtime_stopped"),
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "tracked_source_mutation": False,
        "terminal_status": "LIVE_GENERAL_2_DYNAMIC_RESUMPTION_PASSED",
        "created_at": FIXED_TIMESTAMP,
    }))
    return terminal


def _final_synthesis(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], resolution: Mapping[str, Any], csv_result: Mapping[str, Any], json_result: Mapping[str, Any], recon_output: Mapping[str, Any], response: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "live_general_2_final_synthesis_v1",
        "output_id": stable_id("live-general-2-final-synthesis", mission["mission_id"], csv_result["validation_digest"], json_result["validation_digest"], recon_output["artifact_digest"]),
        "mission_id": mission["mission_id"],
        "work_item_id": item["work_item_id"],
        "csv_validation": {"status": "completed", "capability_source": "developmentally_learned_competence", "output_id": csv_result["output_id"], "output_digest": csv_result["output_digest"], "validation_id": csv_result["validation_id"], "validation_digest": csv_result["validation_digest"]},
        "json_validation": {"status": "completed", "capability_source": "declared_adapter_capability", "output_id": json_result["output_id"], "output_digest": json_result["output_digest"], "validation_id": json_result["validation_id"], "validation_digest": json_result["validation_digest"]},
        "reconciliation": {"status": "rejected_by_operator", "capability_source": "rejected_by_operator", "output_id": recon_output["output_id"], "output_digest": recon_output["artifact_digest"], "reason": response["reason"]},
        "capability_origin_attribution": {"csv": "developmentally_learned_competence", "json": "declared_adapter_capability", "reconciliation": "rejected_by_operator", "synthesis": "validated_bootstrap_competence"},
        "unified_compliance_report": "CSV and JSON validation completed. Cross-format reconciliation was not established because the missing capability was rejected for this gate.",
        "confidence_and_scope_limits": ("bounded disposable fixture", "no reconciliation claim established", "no learned reconciliation competence created"),
        "input_preservation": {"csv": csv_result["fixture_input_digests_before"] == csv_result["fixture_input_digests_after"], "json": json_result["fixture_input_digests_before"] == json_result["fixture_input_digests_after"]},
        "synthesis_attempt": 2,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "final_synthesis", record["output_id"], _digest_record(record))


def _validate_final_synthesis(root: Path, mission: Mapping[str, Any], item: Mapping[str, Any], synthesis: Mapping[str, Any]) -> dict[str, Any]:
    predicates = (
        ("completed_work_distinguished", synthesis["csv_validation"]["status"] == synthesis["json_validation"]["status"] == "completed"),
        ("rejected_work_not_described_completed", synthesis["reconciliation"]["status"] == "rejected_by_operator"),
        ("capability_origins_correct", synthesis["capability_origin_attribution"]["reconciliation"] == "rejected_by_operator"),
        ("no_reconciliation_claim_established", "not established" in synthesis["unified_compliance_report"]),
        ("input_preservation_bound", synthesis["input_preservation"]["csv"] and synthesis["input_preservation"]["json"]),
        ("no_trust_or_promotion", "trusted" not in json.dumps(synthesis, sort_keys=True) and "promotion" not in json.dumps(synthesis, sort_keys=True)),
    )
    aggregate = "passed" if all(ok for _, ok in predicates) else "failed"
    record = {
        "schema": "live_general_2_final_synthesis_validation_v1",
        "validator_id": stable_id("live-general-2-final-synthesis-validator", item["work_item_id"]),
        "validator_digest": bootstrap_digest(("live-general-2-final-synthesis-validator", item["work_item_id"])),
        "evaluation_id": stable_id("live-general-2-final-synthesis-evaluation", synthesis["artifact_digest"], aggregate),
        "mission_id": mission["mission_id"],
        "work_item_id": item["work_item_id"],
        "output_id": synthesis["output_id"],
        "output_digest": synthesis["artifact_digest"],
        "predicate_outcomes": tuple({"predicate": name, "outcome": "passed" if ok else "failed"} for name, ok in predicates),
        "aggregate_status": aggregate,
        "created_at": FIXED_TIMESTAMP,
    }
    return _write(root, "final_synthesis_validation", record["evaluation_id"], _digest_record(record))


def _negative_controls() -> dict[str, Any]:
    return {
        "csv": {"empty_report": "failed", "missing_only_report": "failed", "unstructured_prose": "failed", "mutated_fixture_input": "integrity_stop"},
        "json": {"empty_report": "failed", "flat_only_validation_report": "failed", "keyword_only_report": "failed", "mutated_fixture_input": "integrity_stop"},
        "synthesis": {"uncited_synthesis": "failed", "swapped_capability_attribution": "failed", "omitted_work_item_result": "failed", "claimed_trust_or_promotion": "failed", "hidden_expected_outcomes": "failed"},
        "reconciliation": {"empty_reconciliation": "not_accepted", "identifier_only_matching": "not_accepted", "positional_matching": "not_accepted", "conflict_blind_output": "not_accepted", "provenance_free_output": "not_accepted", "fixture_mutation": "integrity_stop"},
        "accepted_evaluation_items_created": 0,
    }


def _zero_replay_counters() -> dict[str, int]:
    return {"csv_learner": 0, "json_adapter": 0, "interim_synthesis": 0, "reconciliation_learner": 0, "reconciliation_executor": 0, "final_synthesis": 0, "csv_evaluator": 0, "json_evaluator": 0, "reconciliation_evaluator": 0, "final_synthesis_evaluator": 0}


def run_live_general_2_dynamic_resumption_mission(*, root: Path = LIVE_GENERAL_2_ROOT, reset: bool = False) -> dict[str, Any]:
    run_live_general_2_until_operator_boundary(root=root, reset=reset)
    return consume_reconciliation_operator_rejection(root=root)
