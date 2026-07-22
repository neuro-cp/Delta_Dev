"""LIVE-RUNTIME-3 interruption and explicit resumption pilot.

This module keeps the LIVE-RUNTIME-1 controller as the mission execution owner.
It adds two bounded unattended authority generations, nonterminal stop handling,
runner locking, and explicit recovery from an interrupted runner.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping

from orchestration.runtime.continuous_runtime_controller import (
    LIVE_RUNTIME_1_RECONCILIATION_COMPETENCE_DIGEST,
    advance_live_runtime_1_attended_mission,
    attach_live_runtime_1_attended_mission,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.live_general_3_learning_mission import LIVE_GENERAL_3_ROOT, NEW_RECONCILIATION_COMPETENCE_ID


LIVE_RUNTIME_3_SESSION_ID = "tk-live-runtime-3"
LIVE_RUNTIME_3_DEFAULT_ROOT = Path(".tmp") / "live-runtime-3-interruption-resumption-v1"


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    data = dict(payload)
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return data


def _append_checkpoint(root: Path, name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    checkpoint_dir = root / "unattended_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    sequence = len(tuple(checkpoint_dir.glob("*.json")))
    record = _digest_record({
        "schema": "live_runtime_3_checkpoint_v1",
        "checkpoint_id": stable_id("live-runtime-3-checkpoint", str(sequence), name, json.dumps(payload, sort_keys=True, default=str)),
        "sequence": sequence,
        "name": name,
        "payload": dict(payload),
        "created_at": "2026-07-22T00:00:00+00:00",
    })
    return _write_json(checkpoint_dir / f"{sequence:03d}-{name}.json", record)


def _runtime_state(controller: Any) -> dict[str, Any]:
    return dict(dict(controller.continuous_learning_state or {}).get("live_runtime_1") or {})


def _load_controller(root: Path) -> Any:
    restart = json.loads((root / "restart_state.json").read_text(encoding="utf-8"))
    controller = start_continuous_runtime_controller(session_id=LIVE_RUNTIME_3_SESSION_ID, wake_mode="BOUNDED_BACKGROUND")
    return restore_continuous_mission_restart_state(controller, restart)


def _persist(root: Path, controller: Any, *, worker_state: str, stop_reason: str = "", authority_id: str = "") -> None:
    _write_json(root / "restart_state.json", export_continuous_mission_restart_state(controller))
    _write_json(root / "worker_status.json", {
        "schema": "live_runtime_3_worker_status_v1",
        "worker_state": worker_state,
        "stop_reason": stop_reason,
        "authority_id": authority_id,
        "timestamp": "2026-07-22T00:00:00+00:00",
        "session_id": controller.session_id,
        "continuous_mission_state": controller.continuous_mission_state,
        "process_id": os.getpid(),
        "pending_application_decision_id": "",
    })
    _write_json(root / "observation_requeue.json", {"timestamp": "2026-07-22T00:00:00+00:00", "source": "live_runtime_3"})


def prepare_live_runtime_3_mission(
    *,
    runtime_root: str | Path = LIVE_RUNTIME_3_DEFAULT_ROOT,
    accepted_competence_root: str | Path = LIVE_GENERAL_3_ROOT,
    reset: bool = False,
) -> Any:
    root = Path(runtime_root)
    controller = start_continuous_runtime_controller(session_id=LIVE_RUNTIME_3_SESSION_ID, wake_mode="MANUAL")
    controller = attach_live_runtime_1_attended_mission(controller, runtime_root=root, accepted_competence_root=accepted_competence_root, reset=reset)
    while len(tuple(_runtime_state(controller).get("phase_history") or ())) < 2:
        controller = advance_live_runtime_1_attended_mission(controller)
    _persist(root, controller, worker_state="awaiting_first_unattended_authority")
    _append_checkpoint(root, "graph_registered", {"work_items": _runtime_state(controller).get("work_item_status")})
    return controller


def _work_items_by_status(state: Mapping[str, Any], *, completed: bool) -> tuple[dict[str, Any], ...]:
    status = dict(state.get("work_item_status") or {})
    return tuple(
        dict(item)
        for item in tuple(state.get("work_items") or ())
        if (status.get(str(item.get("label"))) == "completed") is completed
    )


def compile_live_runtime_3_unattended_authority(
    controller: Any,
    *,
    runtime_root: str | Path,
    generation: int,
    max_cycles: int,
    max_duration_seconds: int = 10 * 60,
    operator_approval_token: str | None = None,
) -> dict[str, Any]:
    state = _runtime_state(controller)
    mission = dict(state.get("mission") or {})
    all_items = tuple(dict(item) for item in tuple(state.get("work_items") or ()))
    if not mission or len(all_items) != 4:
        raise ValueError("live_runtime_3_authority_requires_registered_four_item_graph")
    if state.get("status") == "terminal":
        raise ValueError("live_runtime_3_terminal_mission_rejects_unattended_authority")
    remaining = _work_items_by_status(state, completed=False)
    completed = _work_items_by_status(state, completed=True)
    allowed = all_items if generation == 1 else remaining
    if generation == 2 and not remaining:
        raise ValueError("live_runtime_3_second_authority_requires_remaining_work")
    token = operator_approval_token or f"operator-approved-live-runtime-3-generation-{generation}"
    record = {
        "schema": "live_runtime_3_unattended_authority_v1",
        "authority_id": stable_id("live-runtime-3-unattended-authority", mission["mission_id"], str(generation), token),
        "authority_generation": int(generation),
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "operator_approval_token": token,
        "allowed_work_item_ids": tuple(item["work_item_id"] for item in allowed),
        "allowed_work_item_digests": tuple(item["artifact_digest"] for item in allowed),
        "completed_work_item_ids_at_authorization": tuple(item["work_item_id"] for item in completed),
        "maximum_scheduler_cycles": int(max_cycles),
        "maximum_wall_clock_seconds": int(max_duration_seconds),
        "provider_budget": 0,
        "retrieval_budget": 0,
        "learning_allowed": False,
        "network_allowed": False,
        "deployment_allowed": False,
        "tracked_source_mutation_allowed": False,
        "fixture_mutation_allowed": False,
        "additional_missions_allowed": False,
        "automatic_retries_allowed": 0,
        "allowed_competence_ids": ("bootstrap-f-autonomous-competence-d33553b9a4bc5c00", NEW_RECONCILIATION_COMPETENCE_ID),
        "allowed_adapters": ("live-task-adapter-capability-68fa299e4b7c9a9e",),
        "status": "accepted",
        "created_at": "2026-07-22T00:00:00+00:00",
    }
    authority = _digest_record(record)
    root = Path(runtime_root)
    _write_json(root / "unattended_authority" / f"{authority['authority_id']}.json", authority)
    _append_checkpoint(root, f"authority_{generation}_accepted", {"authority_id": authority["authority_id"], "allowed_work_item_ids": authority["allowed_work_item_ids"]})
    return authority


def _authority_consumed(root: Path, authority_id: str) -> bool:
    return (root / "unattended_authority_consumption" / f"{authority_id}.json").exists()


def _read_authority(root: Path, authority_id: str | None = None) -> dict[str, Any]:
    authority_dir = root / "unattended_authority"
    if authority_id:
        path = authority_dir / f"{authority_id}.json"
    else:
        candidates = []
        for path in sorted(authority_dir.glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            if not _authority_consumed(root, str(item.get("authority_id") or "")):
                candidates.append((int(item.get("authority_generation") or 0), path))
        if not candidates:
            raise ValueError("live_runtime_3_authority_missing")
        path = sorted(candidates)[-1][1]
    authority = json.loads(path.read_text(encoding="utf-8"))
    expected = _digest_record({key: value for key, value in authority.items() if key != "artifact_digest"})["artifact_digest"]
    if authority.get("artifact_digest") != expected:
        raise ValueError("live_runtime_3_authority_digest_mismatch")
    return authority


def _verify_authority(controller: Any, authority: Mapping[str, Any]) -> None:
    state = _runtime_state(controller)
    mission = dict(state.get("mission") or {})
    work_items = tuple(dict(item) for item in tuple(state.get("work_items") or ()))
    if state.get("status") == "terminal":
        raise ValueError("live_runtime_3_terminal_mission_rejects_unattended_execution")
    if mission.get("mission_id") != authority.get("mission_id") or mission.get("artifact_digest") != authority.get("mission_digest"):
        raise ValueError("live_runtime_3_authority_mission_mismatch")
    allowed = tuple(authority.get("allowed_work_item_ids") or ())
    known_ids = tuple(item["work_item_id"] for item in work_items)
    if any(item_id not in known_ids for item_id in allowed):
        raise ValueError("live_runtime_3_authority_work_item_mismatch")
    if int(authority.get("authority_generation") or 0) >= 2:
        completed_ids = {item["work_item_id"] for item in _work_items_by_status(state, completed=True)}
        if any(item_id in completed_ids for item_id in allowed):
            raise ValueError("live_runtime_3_authority_replays_completed_work")
    if authority.get("provider_budget") != 0 or authority.get("learning_allowed") is not False:
        raise ValueError("live_runtime_3_authority_provider_or_learning_mismatch")
    if authority.get("network_allowed") is not False or authority.get("deployment_allowed") is not False:
        raise ValueError("live_runtime_3_authority_network_or_deployment_mismatch")
    if authority.get("tracked_source_mutation_allowed") is not False or authority.get("fixture_mutation_allowed") is not False:
        raise ValueError("live_runtime_3_authority_mutation_mismatch")


def _guardrail_stop(controller: Any, authority: Mapping[str, Any]) -> str:
    state = _runtime_state(controller)
    counts = dict(state.get("counts") or {})
    evaluators = dict(counts.get("evaluators") or {})
    if int(counts.get("provider_calls") or 0) > 0:
        return "provider_call_attempt"
    if int(state.get("learning_attempts_created") or 0) > 0 or dict(dict(controller.continuous_learning_state or {}).get("developmental_learning") or {}):
        return "learning_attempt_creation"
    if int(state.get("operator_requests_created") or 0) > 0 or tuple(controller.continuous_developmental_insight_requests or ()):
        return "unexpected_operator_request"
    if int(state.get("mission_registrations") or 0) > 1:
        return "unexpected_mission_creation"
    if state.get("tracked_source_mutation") is not False:
        return "tracked_source_mutation"
    if int(state.get("trusted_admissions") or 0) > 0:
        return "trusted_admission_changed"
    if int(state.get("capability_promotions") or 0) > 0:
        return "capability_promotion_changed"
    if int(counts.get("csv_learner") or 0) > 1 or int(counts.get("json_adapter") or 0) > 1:
        return "duplicate_execution"
    if int(counts.get("reconciliation_executor") or 0) > 1 or int(counts.get("final_synthesis") or 0) > 1:
        return "duplicate_execution"
    if any(int(evaluators.get(key) or 0) > 1 for key in ("csv", "json", "reconciliation", "final_synthesis")):
        return "duplicate_evaluation"
    artifacts = dict(state.get("artifacts") or {})
    for key in ("csv_result", "json_result"):
        if key in artifacts and tuple(artifacts[key].get("fixture_input_digests_before") or ()) != tuple(artifacts[key].get("fixture_input_digests_after") or ()):
            return "fixture_mutation"
    if state.get("accepted_reconciliation_competence_digest") != LIVE_RUNTIME_1_RECONCILIATION_COMPETENCE_DIGEST:
        return "artifact_drift"
    return ""


def _result_status(stop_reason: str) -> str:
    if stop_reason == "terminal":
        return "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_PASSED"
    if stop_reason in {"cycle_limit", "authority_expired", "controlled_process_interruption"}:
        return "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_PARTIAL"
    if stop_reason in {"authority_missing", "authority_verification_failed"}:
        return "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_BLOCKED"
    return "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_INTEGRITY_STOP"


def _write_stop(root: Path, controller: Any, authority: Mapping[str, Any], *, stop_reason: str, started: float, cycles_advanced: int) -> dict[str, Any]:
    state = _runtime_state(controller)
    stop = _digest_record({
        "schema": "live_runtime_3_stop_v1",
        "stop_id": stable_id("live-runtime-3-stop", authority["authority_id"], stop_reason, str(cycles_advanced)),
        "authority_id": authority["authority_id"],
        "authority_digest": authority["artifact_digest"],
        "authority_generation": authority["authority_generation"],
        "mission_id": authority["mission_id"],
        "stop_reason": stop_reason,
        "result_status": _result_status(stop_reason),
        "cycles_advanced": int(cycles_advanced),
        "scheduler_cycles": int(state.get("scheduler_cycles") or 0),
        "wall_clock_seconds": round(time.monotonic() - started, 3),
        "continuous_mission_state": controller.continuous_mission_state,
        "work_item_status": dict(state.get("work_item_status") or {}),
        "evaluation_item_ids": tuple(state.get("evaluation_item_ids") or ()),
        "counts": dict(state.get("counts") or {}),
        "created_at": "2026-07-22T00:00:00+00:00",
    })
    _write_json(root / "unattended_stops" / f"{authority['authority_id']}.json", stop)
    _write_json(root / "unattended_stop" / "stop.json", stop)
    _write_json(root / "unattended_authority_consumption" / f"{authority['authority_id']}.json", _digest_record({
        "schema": "live_runtime_3_authority_consumption_v1",
        "authority_id": authority["authority_id"],
        "authority_digest": authority["artifact_digest"],
        "authority_generation": authority["authority_generation"],
        "stop_id": stop["stop_id"],
        "stop_digest": stop["artifact_digest"],
        "consumption_status": "consumed_terminal" if stop_reason == "terminal" else "consumed_stopped",
        "created_at": "2026-07-22T00:00:00+00:00",
    }))
    _persist(root, controller, worker_state="stopped", stop_reason=stop_reason, authority_id=str(authority["authority_id"]))
    _append_checkpoint(root, f"authority_{authority['authority_generation']}_stopped", {"stop_reason": stop_reason, "result_status": stop["result_status"]})
    return stop


def _startup_stop(root: Path, stop_reason: str, detail: str = "") -> dict[str, Any]:
    stop = _digest_record({
        "schema": "live_runtime_3_stop_v1",
        "stop_id": stable_id("live-runtime-3-startup-stop", str(root), stop_reason, detail),
        "authority_id": "",
        "authority_digest": "",
        "authority_generation": 0,
        "mission_id": "",
        "stop_reason": stop_reason,
        "stop_detail": detail[:500],
        "result_status": _result_status(stop_reason),
        "cycles_advanced": 0,
        "scheduler_cycles": 0,
        "wall_clock_seconds": 0.0,
        "continuous_mission_state": "startup_blocked",
        "work_item_status": {},
        "evaluation_item_ids": (),
        "counts": {},
        "created_at": "2026-07-22T00:00:00+00:00",
    })
    _write_json(root / "unattended_stop" / "stop.json", stop)
    return stop


def _acquire_lock(root: Path, authority: Mapping[str, Any]) -> bool:
    lock = root / "runner.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        return False
    _write_json(lock / "owner.json", {"pid": os.getpid(), "authority_id": authority["authority_id"], "created_at": "2026-07-22T00:00:00+00:00"})
    return True


def _release_lock(root: Path) -> None:
    lock = root / "runner.lock"
    if lock.exists():
        shutil.rmtree(lock)


def run_live_runtime_3_bounded_unattended(
    *,
    runtime_root: str | Path = LIVE_RUNTIME_3_DEFAULT_ROOT,
    authority_id: str | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root)
    try:
        authority = _read_authority(root, authority_id)
    except Exception as exc:  # noqa: BLE001 - durable blocked result.
        return _startup_stop(root, "authority_missing", f"{type(exc).__name__}: {exc}")
    if _authority_consumed(root, str(authority["authority_id"])):
        return json.loads((root / "unattended_stops" / f"{authority['authority_id']}.json").read_text(encoding="utf-8"))
    if not _acquire_lock(root, authority):
        return _startup_stop(root, "simultaneous_runner_rejected", str(authority["authority_id"]))
    started = time.monotonic()
    cycles_advanced = 0
    try:
        try:
            controller = _load_controller(root)
            _verify_authority(controller, authority)
        except Exception as exc:  # noqa: BLE001 - invalid authority before execution.
            return _startup_stop(root, "authority_verification_failed", f"{type(exc).__name__}: {exc}")
        _append_checkpoint(root, f"runner_{authority['authority_generation']}_started", {"authority_id": authority["authority_id"], "pid": os.getpid()})
        _persist(root, controller, worker_state="running", authority_id=str(authority["authority_id"]))
        max_cycles = int(authority["maximum_scheduler_cycles"])
        max_seconds = int(authority["maximum_wall_clock_seconds"])
        while True:
            guard = _guardrail_stop(controller, authority)
            if guard:
                return _write_stop(root, controller, authority, stop_reason=guard, started=started, cycles_advanced=cycles_advanced)
            if _runtime_state(controller).get("status") == "terminal":
                return _write_stop(root, controller, authority, stop_reason="terminal", started=started, cycles_advanced=cycles_advanced)
            if cycles_advanced >= max_cycles:
                return _write_stop(root, controller, authority, stop_reason="cycle_limit", started=started, cycles_advanced=cycles_advanced)
            if time.monotonic() - started >= max_seconds:
                return _write_stop(root, controller, authority, stop_reason="authority_expired", started=started, cycles_advanced=cycles_advanced)
            before = tuple(_runtime_state(controller).get("phase_history") or ())
            controller = advance_live_runtime_1_attended_mission(controller)
            cycles_advanced += 1
            phase = tuple(_runtime_state(controller).get("phase_history") or before)[-1]
            _persist(root, controller, worker_state="running", authority_id=str(authority["authority_id"]))
            if phase in {"csv_completed", "json_completed", "reconciliation_completed", "final_synthesis_completed"}:
                _append_checkpoint(root, phase, {"authority_generation": authority["authority_generation"], "work_items": _runtime_state(controller).get("work_item_status")})
    finally:
        _release_lock(root)


def recover_live_runtime_3_interrupted_runner(*, runtime_root: str | Path = LIVE_RUNTIME_3_DEFAULT_ROOT) -> dict[str, Any]:
    root = Path(runtime_root)
    worker = json.loads((root / "worker_status.json").read_text(encoding="utf-8"))
    if worker.get("worker_state") != "running":
        return json.loads((root / "unattended_stop" / "stop.json").read_text(encoding="utf-8"))
    authority = _read_authority(root, str(worker.get("authority_id") or ""))
    controller = _load_controller(root)
    if not _authority_consumed(root, authority["authority_id"]):
        stop = _write_stop(root, controller, authority, stop_reason="controlled_process_interruption", started=time.monotonic(), cycles_advanced=0)
    else:
        stop = json.loads((root / "unattended_stops" / f"{authority['authority_id']}.json").read_text(encoding="utf-8"))
    _release_lock(root)
    return stop


def start_live_runtime_3_process(*, runtime_root: str | Path, authority_id: str | None = None, python_executable: str | None = None) -> subprocess.Popen[Any]:
    cmd = [
        python_executable or sys.executable,
        "-m",
        "orchestration.runtime.live_runtime_3_interruption_resumption",
        "--root",
        str(Path(runtime_root)),
    ]
    if authority_id:
        cmd.extend(["--authority-id", authority_id])
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parents[2]), creationflags=creationflags)


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    root = LIVE_RUNTIME_3_DEFAULT_ROOT
    authority_id = None
    if "--root" in args:
        index = args.index("--root")
        root = Path(args[index + 1])
    if "--authority-id" in args:
        index = args.index("--authority-id")
        authority_id = args[index + 1]
    result = run_live_runtime_3_bounded_unattended(runtime_root=root, authority_id=authority_id)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("result_status") in {"LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_PASSED", "LIVE_RUNTIME_3_INTERRUPTION_RESUMPTION_PARTIAL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
