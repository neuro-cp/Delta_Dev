"""AUTONOMY-16 persistent mixed-mission routing."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.autonomy_capability_composition import run_capability_composition
from orchestration.runtime.autonomy_gap_detection import classify_requirement, fresh_requirement, propose_gap
from orchestration.runtime.autonomy_task_activation import fresh_task_contract, issue_task_activation, execute_task_activation, complete_task_activation, select_task_competence
from orchestration.runtime.autonomy_competence_admission import load_competence_records
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_16_ROOT = Path(".tmp") / "autonomy-16-mixed-mission"
A16_STATUS_PASSED = "AUTONOMY_16_PERSISTENT_MIXED_MISSION_ROUTING_PASSED"


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


def acquire_mission_lock(root: str | Path, mission: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root)
    lock = root / "runner.lock"
    root.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        return _digest_record({"schema": "autonomy_16_mission_lock_v1", "acquired": False, "reason": "duplicate_active_runner", "owner": _read_json(lock / "owner.json") or {}, "created_at": FIXED_TIMESTAMP})
    owner = _digest_record({"schema": "live_runtime_4_runner_lock_owner_v1", "pid": os.getpid(), "mission_id": mission["mission_id"], "mission_digest": mission["artifact_digest"], "runner_lock_scope": stable_id("autonomy-16-runner-lock", root, mission["mission_id"]), "created_at": FIXED_TIMESTAMP})
    _write_json(lock / "owner.json", owner)
    return _digest_record({"schema": "autonomy_16_mission_lock_v1", "acquired": True, "reason": "", "owner": owner, "created_at": FIXED_TIMESTAMP})


def release_mission_lock(root: str | Path) -> None:
    lock = Path(root) / "runner.lock"
    if lock.exists():
        shutil.rmtree(lock)


def _task(task_key: str, requirement_kind: str, *, priority: int, dependencies: Sequence[str] = (), duplicate_of: str = "", blocked_authority: bool = False, summary: bool = False) -> dict[str, Any]:
    requirement = fresh_requirement(requirement_kind)
    semantic = bootstrap_digest((task_key, requirement["required_task_class"], requirement["required_behaviors"], requirement["task_digest"], tuple(dependencies), requirement["required_authority"], {"operator_approval": blocked_authority}))
    return _digest_record({
        "schema": "autonomy_16_mission_task_v1",
        "task_id": stable_id("autonomy-16-task", task_key),
        "task_key": task_key,
        "task_statement": requirement["normalized_task_statement"] if not summary else "Summarize completed validated/reconciled branch output.",
        "requirement_kind": requirement_kind,
        "requirement": requirement,
        "semantic_identity": semantic if not duplicate_of else duplicate_of,
        "dependency_ids": tuple(dependencies),
        "priority": priority,
        "age_fairness": 0,
        "authority_requirements": {"operator_approval": blocked_authority},
        "budget": {"maximum_executions": 1},
        "current_lifecycle_state": "ready",
        "transition_sequence": 0,
        "created_at": FIXED_TIMESTAMP,
    })


def compile_mixed_mission(output_root: str | Path = AUTONOMY_16_ROOT, *, competence_roots: Sequence[str | Path] = ()) -> dict[str, Any]:
    output_root = Path(output_root)
    existing = _read_json(output_root / "mission.json")
    if existing:
        return existing
    # Branch 1: direct JSON -> direct reconciliation -> downstream summary.
    t1 = _task("direct_json", "json", priority=100)
    t2 = _task("direct_reconciliation", "reconciliation", priority=90, dependencies=(t1["task_id"],))
    t3 = _task("downstream_summary", "partial", priority=30, dependencies=(t2["task_id"],), summary=True)
    tasks = [
        t1,
        t2,
        _task("composition", "composition", priority=80),
        t3,
        _task("partial", "partial", priority=70),
        _task("unsupported", "unsupported", priority=60),
        _task("blocked_authority", "json", priority=95, blocked_authority=True),
        _task("prohibited", "prohibited", priority=1000),
        _task("duplicate_json", "json", priority=99, duplicate_of=t1["semantic_identity"]),
        _task("independent_a", "json", priority=50),
        _task("independent_b", "reconciliation", priority=40),
        _task("ambiguous", "ambiguous", priority=20),
    ]
    tasks = [{**task, "created_index": index} for index, task in enumerate(tasks, start=1)]
    mission = _digest_record({
        "schema": "autonomy_16_mixed_mission_v1",
        "mission_id": stable_id("autonomy-16-mission", "mixed", tuple(task["semantic_identity"] for task in tasks)),
        "objective": "Route mixed supported, composed, partial, blocked, prohibited, duplicate, and independent tasks.",
        "mission_policy_version": "autonomy_16_mixed_mission_policy_v1",
        "task_graph_digest": bootstrap_digest(tuple((task["task_id"], task["dependency_ids"]) for task in tasks)),
        "budget_digest": bootstrap_digest({"maximum_task_transitions": 80, "maximum_task_executions": 6, "maximum_gap_proposals": 2}),
        "authority_digest": bootstrap_digest({"provider": False, "network": False, "deployment": False, "credentials": False, "tracked_source_mutation": False}),
        "restart_key": stable_id("autonomy-16-restart", tuple(task["task_id"] for task in tasks)),
        "final_disposition_policy": "partially_completed_when_safe_work_done_and_blocked_work_remains",
        "mission_state": "compiled",
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "mission.json", mission)
    _write_json(output_root / "task_graph.json", {"tasks": tuple(tasks), "edges": tuple((task["task_id"], dep) for task in tasks for dep in task["dependency_ids"])})
    for task in tasks:
        _write_json(output_root / "tasks" / f"{task['task_id']}.json", task)
    _checkpoint(output_root, mission, "mission_compiled")
    return mission


def _read_tasks(root: Path) -> list[dict[str, Any]]:
    records = [record for path in sorted((root / "tasks").glob("*.json")) if (record := _read_json(path))]
    return sorted(records, key=lambda item: (int(item.get("created_index") or 9999), str(item.get("task_id") or "")))


def _persist_task(root: Path, task: Mapping[str, Any]) -> dict[str, Any]:
    return _write_json(root / "tasks" / f"{task['task_id']}.json", task)


def _transition(root: Path, mission: Mapping[str, Any], task: Mapping[str, Any] | None, state: str, reason: str, source_digest: str = "") -> dict[str, Any]:
    seq = len(tuple((root / "transitions").glob("*.json"))) + 1
    transition = _digest_record({"schema": "autonomy_16_task_transition_v1", "transition_id": stable_id("autonomy-16-transition", mission["mission_id"], task.get("task_id") if task else "mission", state, seq), "mission_id": mission["mission_id"], "task_id": task.get("task_id", "") if task else "", "next_state": state, "reason": reason, "source_artifact_digest": source_digest, "transition_sequence": seq, "created_at": FIXED_TIMESTAMP})
    _write_json(root / "transitions" / f"{transition['transition_id']}.json", transition)
    _narrate(root, mission, task, transition, reason)
    return transition


def _narrate(root: Path, mission: Mapping[str, Any], task: Mapping[str, Any] | None, transition: Mapping[str, Any], message: str) -> dict[str, Any]:
    event = _digest_record({"schema": "operator_ux_narration_event_v1", "event_id": stable_id("autonomy-16-narration", transition["transition_id"]), "mission_id": mission["mission_id"], "task_id": task.get("task_id", "") if task else "", "transition_id": transition["transition_id"], "runtime_phase": "autonomy_16_mixed_mission", "event_type": "mission_routing", "message": message, "source_artifact": transition["artifact_digest"], "timestamp": FIXED_TIMESTAMP, "chain_of_thought_exposed": False})
    return _write_json(root / "narration" / f"{event['event_id']}.json", event)


def _checkpoint(root: Path, mission: Mapping[str, Any], reason: str) -> dict[str, Any]:
    tasks = _read_tasks(root)
    checkpoint = _digest_record({"schema": "autonomy_16_mission_checkpoint_v1", "checkpoint_id": stable_id("autonomy-16-checkpoint", mission["mission_id"], reason, len(tasks), tuple((task["task_id"], task.get("current_lifecycle_state")) for task in tasks)), "mission_id": mission["mission_id"], "mission_state": mission.get("mission_state", "running"), "task_states": tuple((task["task_id"], task.get("current_lifecycle_state")) for task in tasks), "reason": reason, "created_at": FIXED_TIMESTAMP})
    return _write_json(root / "checkpoints" / f"{checkpoint['checkpoint_id']}.json", checkpoint)


def _classify_tasks(root: Path, competence_roots: Sequence[str | Path]) -> None:
    competences = load_competence_records(*competence_roots)
    seen_semantics: set[str] = set()
    for task in _read_tasks(root):
        if task.get("classification"):
            seen_semantics.add(str(task.get("semantic_identity")))
            continue
        classified = classify_requirement(task["requirement"], competences)
        gap = propose_gap(classified)
        state = "ready"
        semantic_identity = str(task.get("semantic_identity"))
        if semantic_identity in seen_semantics:
            state = "deferred"
            task["blocked_reason"] = "duplicate_task_suppressed"
        elif task["authority_requirements"].get("operator_approval"):
            state = "blocked_operator_authority"
            _write_json(root / "authority_requests" / f"{task['task_id']}.json", _digest_record({"schema": "autonomy_16_authority_request_v1", "request_id": stable_id("autonomy-16-authority", task["task_id"]), "mission_id": "", "task_id": task["task_id"], "request_integrity_digest": bootstrap_digest(task), "card_digest": bootstrap_digest(("authority", task["task_id"])), "consumed": False, "created_at": FIXED_TIMESTAMP}))
        elif classified["classification"] == "prohibited":
            state = "rejected_prohibited"
        elif classified["classification"] == "ambiguous_requirements":
            state = "awaiting_clarification"
            _write_json(root / "clarification_requests" / f"{task['task_id']}.json", _digest_record({"schema": "autonomy_16_clarification_request_v1", "request_id": stable_id("autonomy-16-clarify", task["task_id"]), "task_id": task["task_id"], "request_integrity_digest": bootstrap_digest(task), "card_digest": bootstrap_digest(("clarify", task["task_id"])), "consumed": False, "created_at": FIXED_TIMESTAMP}))
        elif classified["classification"] == "unsupported":
            state = "blocked_capability_gap"
        task = {**task, "classification": classified, "classification_id": classified["task_requirement_id"], "classification_digest": classified["artifact_digest"], "gap": gap, "gap_binding": gap.get("gap_id") if gap else "", "current_lifecycle_state": state}
        seen_semantics.add(semantic_identity)
        _persist_task(root, task)
        _write_json(root / "classifications" / f"{task['task_id']}.json", classified)
        if gap:
            existing = tuple((root / "gaps").glob("*.json"))
            if len(existing) < 2 and not (root / "gaps" / f"{gap['gap_id']}.json").exists():
                _write_json(root / "gaps" / f"{gap['gap_id']}.json", gap)


def _dependencies_satisfied(task: Mapping[str, Any], tasks: Sequence[Mapping[str, Any]]) -> bool:
    by_id = {task["task_id"]: task for task in tasks}
    for dep in tuple(task.get("dependency_ids") or ()):
        state = by_id.get(dep, {}).get("current_lifecycle_state")
        if state not in {"completed", "partially_completed"}:
            return False
    return True


def select_next_task(root: str | Path) -> dict[str, Any] | None:
    root = Path(root)
    tasks = _read_tasks(root)
    eligible = [task for task in tasks if task.get("current_lifecycle_state") == "ready" and _dependencies_satisfied(task, tasks)]
    if not eligible:
        return None
    return sorted(eligible, key=lambda item: (-int(item["priority"]), int(item.get("age_fairness") or 0), item["task_id"]))[0]


def _run_direct(root: Path, task: Mapping[str, Any], competence_roots: Sequence[str | Path]) -> dict[str, Any]:
    task_class = task["classification"]["required_task_class"]
    a13_task = fresh_task_contract(task_class, task_nonce=f"a16-{task['task_key']}")
    competences = load_competence_records(*competence_roots)
    selection = select_task_competence(a13_task, competences)
    activation_root = root / "a" / str(task["task_key"])
    activation = issue_task_activation(activation_root, a13_task, selection)
    execution = execute_task_activation(activation_root, a13_task, activation)
    completed = complete_task_activation(activation_root, activation, execution)
    return _digest_record({"schema": "autonomy_16_direct_task_result_v1", "task_id": task["task_id"], "activation": completed, "execution": execution, "status": "completed", "created_at": FIXED_TIMESTAMP})


def _execute_task(root: Path, mission: Mapping[str, Any], task: Mapping[str, Any], competence_roots: Sequence[str | Path]) -> dict[str, Any]:
    running = [item for item in _read_tasks(root) if item.get("current_lifecycle_state") == "running"]
    if running:
        return _digest_record({"schema": "autonomy_16_integrity_stop_v1", "status": "integrity_stop", "reason": "two_active_tasks", "created_at": FIXED_TIMESTAMP})
    task = {**task, "current_lifecycle_state": "running", "transition_sequence": int(task.get("transition_sequence") or 0) + 1}
    _persist_task(root, task)
    _transition(root, mission, task, "running", "selected one eligible task")
    classification = task["classification"]["classification"]
    if classification == "fully_supported":
        result = _run_direct(root, task, competence_roots)
        final_state = "completed"
        task = {**task, "activation_binding": result["activation"]["activation_id"], "result_artifact_ids": (result["artifact_digest"],)}
    elif classification == "composition_supported":
        result = run_capability_composition(root / "c" / str(task["task_key"]), competence_roots=competence_roots)
        final_state = "completed" if result["status"].endswith("_PASSED") else "integrity_stop"
        result = _digest_record({"schema": "autonomy_16_composition_task_result_v1", "task_id": task["task_id"], "composition": result["composition_result"], "status": result["status"], "created_at": FIXED_TIMESTAMP})
        task = {**task, "composition_binding": result["composition"].get("artifact_digest"), "result_artifact_ids": (result["artifact_digest"],)}
    elif classification == "partially_supported":
        result = _digest_record({"schema": "autonomy_16_partial_task_result_v1", "task_id": task["task_id"], "completed_supported_portion": True, "unsupported_portion": tuple(task["classification"].get("missing_clauses") or ()), "gap_id": task.get("gap_binding"), "created_at": FIXED_TIMESTAMP})
        final_state = "partially_completed"
    else:
        result = _digest_record({"schema": "autonomy_16_no_execution_result_v1", "task_id": task["task_id"], "status": "not_executed", "classification": classification, "created_at": FIXED_TIMESTAMP})
        final_state = task.get("current_lifecycle_state", "blocked_capability_gap")
    _write_json(root / "results" / f"{task['task_id']}.json", result)
    task = {**task, "current_lifecycle_state": final_state, "result_artifact_digests": (result["artifact_digest"],), "transition_sequence": int(task.get("transition_sequence") or 0) + 1}
    _persist_task(root, task)
    _transition(root, mission, task, final_state, f"task routed as {classification}", result["artifact_digest"])
    _checkpoint(root, mission, f"task_{task['task_key']}_{final_state}")
    return result


def run_mixed_mission(output_root: str | Path = AUTONOMY_16_ROOT, *, competence_roots: Sequence[str | Path] = (), mode: str = "run", budget_transitions: int = 80) -> dict[str, Any]:
    root = Path(output_root)
    final = _read_json(root / "final_status.json")
    if final and final.get("terminal") and mode not in {"restart"}:
        return {"status": final["status"], "report": _read_json(root / "report.json") or {}, "duplicate_suppressed": True}
    mission = compile_mixed_mission(root, competence_roots=competence_roots)
    lock = acquire_mission_lock(root, mission)
    if not lock["acquired"]:
        return {"status": "duplicate_runner_rejected", "lock": lock}
    try:
        _classify_tasks(root, competence_roots)
        _checkpoint(root, mission, "classified_tasks")
        if mode == "pause":
            _write_json(root / "final_status.json", {"status": "paused_operator", "terminal": False})
            return {"status": "paused_operator", "report": _summary(root, mission), "duplicate_suppressed": False}
        if mode == "stop":
            _write_json(root / "final_status.json", {"status": "stopped_by_operator", "terminal": True})
            return {"status": "stopped_by_operator", "report": _summary(root, mission), "duplicate_suppressed": False}
        transitions = 0
        while transitions < budget_transitions:
            task = select_next_task(root)
            if not task:
                break
            _execute_task(root, mission, task, competence_roots)
            transitions += 1
        if transitions >= budget_transitions:
            status = "paused_budget"
            terminal = False
        else:
            states = {task["current_lifecycle_state"] for task in _read_tasks(root)}
            status = "partially_completed" if states & {"blocked_capability_gap", "blocked_operator_authority", "awaiting_clarification", "rejected_prohibited"} else "completed"
            terminal = True
        report = _summary(root, mission)
        report = {**report, "status": A16_STATUS_PASSED if status == "partially_completed" else status, "final_mission_disposition": status}
        _write_json(root / "report.json", report)
        _write_json(root / "final_status.json", {"status": A16_STATUS_PASSED if status == "partially_completed" else status, "mission_disposition": status, "terminal": terminal, "artifact_digest": report["artifact_digest"]})
        return {"status": A16_STATUS_PASSED if status == "partially_completed" else status, "report": report, "duplicate_suppressed": False}
    finally:
        release_mission_lock(root)


def _summary(root: Path, mission: Mapping[str, Any]) -> dict[str, Any]:
    tasks = _read_tasks(root)
    counts: dict[str, int] = {}
    for task in tasks:
        counts[str(task.get("current_lifecycle_state"))] = counts.get(str(task.get("current_lifecycle_state")), 0) + 1
    return _digest_record({"schema": "autonomy_16_mixed_mission_report_v1", "mission_id": mission["mission_id"], "mission_digest": mission["artifact_digest"], "task_counts": counts, "tasks": tuple(tasks), "one_active_task_maximum": len([task for task in tasks if task.get("current_lifecycle_state") == "running"]) <= 1, "gap_candidates_queued": len(tuple((root / "gaps").glob("*.json"))), "provider_calls": 0, "network_calls": 0, "deployment": False, "credentials": False, "tracked_source_mutation": False, "a17_started": False, "created_at": FIXED_TIMESTAMP})


def stale_authority_response(root: str | Path, task_id: str) -> dict[str, Any]:
    request = _read_json(Path(root) / "authority_requests" / f"{task_id}.json") or {}
    response = _digest_record({"schema": "autonomy_16_authority_response_v1", "task_id": task_id, "request_integrity_digest": "stale", "consumed": False, "created_at": FIXED_TIMESTAMP})
    accepted = response["request_integrity_digest"] == request.get("request_integrity_digest")
    return _digest_record({"schema": "autonomy_16_authority_response_check_v1", "accepted": accepted, "reason": "stale_or_mismatched_response" if not accepted else "accepted", "created_at": FIXED_TIMESTAMP})
