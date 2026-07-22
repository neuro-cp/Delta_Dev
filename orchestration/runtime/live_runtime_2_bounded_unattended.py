"""Bounded unattended pilot wrapper for the persistent live runtime.

LIVE-RUNTIME-2 does not introduce new mission semantics. It verifies one
explicit operator authority record, advances the existing LIVE-RUNTIME-1
controller one transition at a time, and stops on terminal or guardrail breach.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
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
from orchestration.runtime.live_general_3_learning_mission import (
    LIVE_GENERAL_3_ROOT,
    NEW_RECONCILIATION_COMPETENCE_ID,
)


LIVE_RUNTIME_2_SESSION_ID = "tk-live-runtime-2"
LIVE_RUNTIME_2_DEFAULT_ROOT = Path(".tmp") / "live-runtime-2-bounded-unattended-v1"
LIVE_RUNTIME_2_MAX_CYCLES = 12
LIVE_RUNTIME_2_MAX_DURATION_SECONDS = 20 * 60
LIVE_RUNTIME_2_ALLOWED_ADAPTERS = ("live-task-adapter-capability-68fa299e4b7c9a9e",)
LIVE_RUNTIME_2_ALLOWED_COMPETENCES = (
    "bootstrap-f-autonomous-competence-d33553b9a4bc5c00",
    NEW_RECONCILIATION_COMPETENCE_ID,
)


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
    checkpoints = root / "unattended_checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    sequence = len(tuple(checkpoints.glob("*.json")))
    record = _digest_record({
        "schema": "live_runtime_2_checkpoint_v1",
        "checkpoint_id": stable_id("live-runtime-2-checkpoint", str(sequence), name, json.dumps(payload, sort_keys=True, default=str)),
        "sequence": sequence,
        "name": name,
        "payload": dict(payload),
        "created_at": "2026-07-22T00:00:00+00:00",
    })
    return _write_json(checkpoints / f"{sequence:03d}-{name}.json", record)


def _runtime_state(controller: Any) -> dict[str, Any]:
    return dict(dict(controller.continuous_learning_state or {}).get("live_runtime_1") or {})


def _load_controller_from_root(root: Path, *, session_id: str = LIVE_RUNTIME_2_SESSION_ID) -> Any:
    restart_path = root / "restart_state.json"
    if not restart_path.exists():
        raise ValueError("live_runtime_2_restart_state_missing")
    restart = json.loads(restart_path.read_text(encoding="utf-8"))
    controller = start_continuous_runtime_controller(session_id=session_id, wake_mode="BOUNDED_BACKGROUND")
    return restore_continuous_mission_restart_state(controller, restart)


def persist_live_runtime_2_state(root: str | Path, controller: Any, *, worker_state: str, stop_reason: str = "") -> None:
    runtime_root = Path(root)
    restart = export_continuous_mission_restart_state(controller)
    _write_json(runtime_root / "restart_state.json", restart)
    _write_json(
        runtime_root / "worker_status.json",
        {
            "schema": "live_runtime_2_worker_status_v1",
            "worker_state": worker_state,
            "stop_reason": stop_reason,
            "timestamp": "2026-07-22T00:00:00+00:00",
            "session_id": controller.session_id,
            "continuous_mission_state": controller.continuous_mission_state,
            "process_id": os.getpid(),
            "pending_application_decision_id": "",
        },
    )
    _write_json(runtime_root / "observation_requeue.json", {"timestamp": "2026-07-22T00:00:00+00:00", "source": "live_runtime_2"})


def prepare_live_runtime_2_mission(
    *,
    runtime_root: str | Path = LIVE_RUNTIME_2_DEFAULT_ROOT,
    accepted_competence_root: str | Path = LIVE_GENERAL_3_ROOT,
    reset: bool = False,
) -> Any:
    root = Path(runtime_root)
    controller = start_continuous_runtime_controller(session_id=LIVE_RUNTIME_2_SESSION_ID, wake_mode="MANUAL")
    controller = attach_live_runtime_1_attended_mission(
        controller,
        runtime_root=root,
        accepted_competence_root=accepted_competence_root,
        reset=reset,
    )
    while len(tuple(_runtime_state(controller).get("phase_history") or ())) < 2:
        controller = advance_live_runtime_1_attended_mission(controller)
    persist_live_runtime_2_state(root, controller, worker_state="awaiting_unattended_authority")
    _append_checkpoint(root, "graph_registered", {"state": controller.continuous_mission_state, "work_items": _runtime_state(controller).get("work_item_status")})
    return controller


def compile_live_runtime_2_unattended_authority(
    controller: Any,
    *,
    runtime_root: str | Path,
    max_cycles: int = LIVE_RUNTIME_2_MAX_CYCLES,
    max_duration_seconds: int = LIVE_RUNTIME_2_MAX_DURATION_SECONDS,
    provider_budget: int = 0,
    operator_approval_token: str = "operator-approved-live-runtime-2-bounded-unattended",
) -> dict[str, Any]:
    state = _runtime_state(controller)
    mission = dict(state.get("mission") or {})
    work_items = tuple(dict(item) for item in (state.get("work_items") or ()))
    if not mission or len(work_items) != 4:
        raise ValueError("live_runtime_2_authority_requires_registered_four_item_graph")
    if provider_budget != 0:
        raise ValueError("live_runtime_2_provider_budget_must_be_zero")
    record = {
        "schema": "live_runtime_2_unattended_authority_v1",
        "authority_id": stable_id("live-runtime-2-unattended-authority", mission["mission_id"], mission["artifact_digest"], operator_approval_token),
        "mission_id": mission["mission_id"],
        "mission_digest": mission["artifact_digest"],
        "operator_approval_token": operator_approval_token,
        "allowed_work_item_ids": tuple(item["work_item_id"] for item in work_items),
        "allowed_work_item_digests": tuple(item["artifact_digest"] for item in work_items),
        "maximum_scheduler_cycles": int(max_cycles),
        "maximum_wall_clock_seconds": int(max_duration_seconds),
        "provider_budget": 0,
        "deterministic_retrieval_budget": 4,
        "allowed_adapters": LIVE_RUNTIME_2_ALLOWED_ADAPTERS,
        "allowed_competence_ids": LIVE_RUNTIME_2_ALLOWED_COMPETENCES,
        "network_allowed": False,
        "tracked_source_mutation_allowed": False,
        "deployment_allowed": False,
        "learning_allowed": False,
        "additional_missions_allowed": False,
        "automatic_retries_allowed": 0,
        "expires_after_monotonic_seconds": int(max_duration_seconds),
        "status": "accepted",
        "created_at": "2026-07-22T00:00:00+00:00",
    }
    authority = _digest_record(record)
    root = Path(runtime_root)
    _write_json(root / "unattended_authority" / f"{authority['authority_id']}.json", authority)
    _append_checkpoint(root, "unattended_authority_accepted", {"authority_id": authority["authority_id"], "authority_digest": authority["artifact_digest"]})
    return authority


def _read_authority(root: Path, authority_id: str | None = None) -> dict[str, Any]:
    authority_dir = root / "unattended_authority"
    if authority_id:
        path = authority_dir / f"{authority_id}.json"
    else:
        matches = sorted(authority_dir.glob("*.json"))
        if not matches:
            raise ValueError("live_runtime_2_authority_missing")
        if len(matches) > 1:
            raise ValueError("live_runtime_2_multiple_authority_records")
        path = matches[0]
    authority = json.loads(path.read_text(encoding="utf-8"))
    expected = _digest_record({key: value for key, value in authority.items() if key != "artifact_digest"})["artifact_digest"]
    if authority.get("artifact_digest") != expected:
        raise ValueError("live_runtime_2_authority_digest_mismatch")
    return authority


def _verify_authority(controller: Any, authority: Mapping[str, Any]) -> None:
    state = _runtime_state(controller)
    mission = dict(state.get("mission") or {})
    work_items = tuple(dict(item) for item in (state.get("work_items") or ()))
    if authority.get("status") != "accepted":
        raise ValueError("live_runtime_2_authority_not_accepted")
    if mission.get("mission_id") != authority.get("mission_id") or mission.get("artifact_digest") != authority.get("mission_digest"):
        raise ValueError("live_runtime_2_authority_mission_mismatch")
    if tuple(item.get("work_item_id") for item in work_items) != tuple(authority.get("allowed_work_item_ids") or ()):
        raise ValueError("live_runtime_2_authority_work_item_mismatch")
    if authority.get("provider_budget") != 0 or authority.get("network_allowed") is not False:
        raise ValueError("live_runtime_2_authority_provider_or_network_mismatch")
    if authority.get("tracked_source_mutation_allowed") is not False or authority.get("deployment_allowed") is not False:
        raise ValueError("live_runtime_2_authority_mutation_or_deployment_mismatch")
    if authority.get("learning_allowed") is not False or authority.get("additional_missions_allowed") is not False:
        raise ValueError("live_runtime_2_authority_learning_or_mission_mismatch")
    if NEW_RECONCILIATION_COMPETENCE_ID not in tuple(authority.get("allowed_competence_ids") or ()):
        raise ValueError("live_runtime_2_authority_reconciliation_competence_missing")


def _fixture_inputs_unchanged(result: Mapping[str, Any]) -> bool:
    return tuple(result.get("fixture_input_digests_before") or ()) == tuple(result.get("fixture_input_digests_after") or ())


def _classify_guardrail_stop(controller: Any, authority: Mapping[str, Any]) -> str:
    state = _runtime_state(controller)
    counts = dict(state.get("counts") or {})
    evaluators = dict(counts.get("evaluators") or {})
    if int(counts.get("provider_calls") or 0) > int(authority.get("provider_budget") or 0):
        return "provider_call_attempt"
    if int(state.get("learning_attempts_created") or 0) > 0 or dict(dict(controller.continuous_learning_state or {}).get("developmental_learning") or {}):
        return "learning_attempt_creation"
    if int(state.get("operator_requests_created") or 0) > 0 or tuple(controller.continuous_developmental_insight_requests or ()):
        return "unexpected_operator_request"
    if int(state.get("mission_registrations") or 0) > 1:
        return "second_mission_detection"
    if state.get("tracked_source_mutation") is not False:
        return "tracked_source_mutation"
    if int(state.get("trusted_admissions") or 0) > 0:
        return "trusted_admission_changed"
    if int(state.get("capability_promotions") or 0) > 0:
        return "capability_promotion_changed"
    if int(counts.get("csv_learner") or 0) > 1 or int(counts.get("json_adapter") or 0) > 1:
        return "duplicate_branch_execution"
    if int(counts.get("reconciliation_executor") or 0) > 1 or int(counts.get("final_synthesis") or 0) > 1:
        return "duplicate_dependent_execution"
    if any(int(evaluators.get(key) or 0) > 1 for key in ("csv", "json", "reconciliation", "final_synthesis")):
        return "evaluator_leakage"
    artifacts = dict(state.get("artifacts") or {})
    for key in ("csv_result", "json_result"):
        if key in artifacts and not _fixture_inputs_unchanged(dict(artifacts[key])):
            return "fixture_input_mutation"
    if state.get("accepted_reconciliation_competence_digest") != LIVE_RUNTIME_1_RECONCILIATION_COMPETENCE_DIGEST:
        return "missing_or_mismatched_capability_record"
    return ""


def _write_stop(root: Path, controller: Any, authority: Mapping[str, Any], *, stop_reason: str, started: float, cycles_advanced: int) -> dict[str, Any]:
    state = _runtime_state(controller)
    result_status = (
        "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PASSED"
        if stop_reason == "terminal"
        else "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PARTIAL"
        if stop_reason in {"cycle_limit", "wall_clock_expired"}
        else "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_INTEGRITY_STOP"
    )
    stop = _digest_record({
        "schema": "live_runtime_2_stop_v1",
        "stop_id": stable_id("live-runtime-2-stop", authority["authority_id"], stop_reason, str(cycles_advanced)),
        "authority_id": authority["authority_id"],
        "authority_digest": authority["artifact_digest"],
        "mission_id": authority["mission_id"],
        "stop_reason": stop_reason,
        "result_status": result_status,
        "cycles_advanced": int(cycles_advanced),
        "scheduler_cycles": int(state.get("scheduler_cycles") or 0),
        "wall_clock_seconds": round(time.monotonic() - started, 3),
        "continuous_mission_state": controller.continuous_mission_state,
        "evaluation_item_ids": tuple(state.get("evaluation_item_ids") or ()),
        "counts": dict(state.get("counts") or {}),
        "trusted_admissions": int(state.get("trusted_admissions") or 0),
        "capability_promotions": int(state.get("capability_promotions") or 0),
        "tracked_source_mutation": bool(state.get("tracked_source_mutation") or False),
        "created_at": "2026-07-22T00:00:00+00:00",
    })
    _write_json(root / "unattended_stop" / "stop.json", stop)
    _write_json(root / "unattended_authority_consumption" / f"{authority['authority_id']}.json", _digest_record({
        "schema": "live_runtime_2_authority_consumption_v1",
        "authority_id": authority["authority_id"],
        "authority_digest": authority["artifact_digest"],
        "stop_id": stop["stop_id"],
        "stop_digest": stop["artifact_digest"],
        "consumption_status": "consumed_terminal" if stop_reason == "terminal" else "consumed_stopped",
        "created_at": "2026-07-22T00:00:00+00:00",
    }))
    persist_live_runtime_2_state(root, controller, worker_state="stopped", stop_reason=stop_reason)
    _append_checkpoint(root, "terminal_or_bounded_stop", {"stop_reason": stop_reason, "result_status": result_status})
    return stop


def _write_startup_stop(root: Path, *, stop_reason: str, detail: str = "") -> dict[str, Any]:
    stop = _digest_record({
        "schema": "live_runtime_2_stop_v1",
        "stop_id": stable_id("live-runtime-2-startup-stop", str(root), stop_reason, detail),
        "authority_id": "",
        "authority_digest": "",
        "mission_id": "",
        "stop_reason": stop_reason,
        "stop_detail": detail[:500],
        "result_status": "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_BLOCKED"
        if stop_reason in {"authority_missing", "restart_state_missing"}
        else "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_INTEGRITY_STOP",
        "cycles_advanced": 0,
        "scheduler_cycles": 0,
        "wall_clock_seconds": 0.0,
        "continuous_mission_state": "startup_blocked",
        "evaluation_item_ids": (),
        "counts": {},
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "tracked_source_mutation": False,
        "created_at": "2026-07-22T00:00:00+00:00",
    })
    _write_json(root / "unattended_stop" / "stop.json", stop)
    _write_json(root / "worker_status.json", {
        "schema": "live_runtime_2_worker_status_v1",
        "worker_state": "stopped",
        "stop_reason": stop_reason,
        "timestamp": "2026-07-22T00:00:00+00:00",
        "session_id": LIVE_RUNTIME_2_SESSION_ID,
        "continuous_mission_state": "startup_blocked",
        "process_id": os.getpid(),
        "pending_application_decision_id": "",
    })
    return stop


def run_live_runtime_2_bounded_unattended(
    *,
    runtime_root: str | Path = LIVE_RUNTIME_2_DEFAULT_ROOT,
    authority_id: str | None = None,
    session_id: str = LIVE_RUNTIME_2_SESSION_ID,
) -> dict[str, Any]:
    root = Path(runtime_root)
    if (root / "unattended_authority_consumption").exists():
        matches = tuple((root / "unattended_authority_consumption").glob("*.json"))
        if matches:
            return json.loads((root / "unattended_stop" / "stop.json").read_text(encoding="utf-8"))
    try:
        authority = _read_authority(root, authority_id)
    except Exception as exc:  # noqa: BLE001 - startup must produce durable blocked evidence.
        return _write_startup_stop(root, stop_reason="authority_missing", detail=f"{type(exc).__name__}: {exc}")
    try:
        controller = _load_controller_from_root(root, session_id=session_id)
        _verify_authority(controller, authority)
    except Exception as exc:  # noqa: BLE001 - invalid authority fails closed before execution.
        return _write_startup_stop(root, stop_reason="authority_verification_failed", detail=f"{type(exc).__name__}: {exc}")
    started = time.monotonic()
    cycles_advanced = 0
    max_cycles = int(authority["maximum_scheduler_cycles"])
    max_seconds = int(authority["maximum_wall_clock_seconds"])
    _append_checkpoint(root, "runner_started", {"authority_id": authority["authority_id"], "pid": os.getpid()})
    persist_live_runtime_2_state(root, controller, worker_state="running")

    while True:
        guard = _classify_guardrail_stop(controller, authority)
        if guard:
            return _write_stop(root, controller, authority, stop_reason=guard, started=started, cycles_advanced=cycles_advanced)
        if _runtime_state(controller).get("status") == "terminal":
            return _write_stop(root, controller, authority, stop_reason="terminal", started=started, cycles_advanced=cycles_advanced)
        if cycles_advanced >= max_cycles:
            return _write_stop(root, controller, authority, stop_reason="cycle_limit", started=started, cycles_advanced=cycles_advanced)
        if time.monotonic() - started >= max_seconds:
            return _write_stop(root, controller, authority, stop_reason="wall_clock_expired", started=started, cycles_advanced=cycles_advanced)
        try:
            before_history = tuple(_runtime_state(controller).get("phase_history") or ())
            controller = advance_live_runtime_1_attended_mission(controller)
            cycles_advanced += 1
            state = _runtime_state(controller)
            phase = tuple(state.get("phase_history") or before_history)[-1]
            persist_live_runtime_2_state(root, controller, worker_state="running")
            if phase in {"work_graph_registered", "csv_completed", "json_completed", "reconciliation_completed", "final_synthesis_completed"}:
                _append_checkpoint(root, phase, {"scheduler_cycles": state.get("scheduler_cycles"), "work_items": state.get("work_item_status")})
        except Exception as exc:  # noqa: BLE001 - unattended pilot must fail closed.
            _append_checkpoint(root, "runtime_exception", {"exception_type": type(exc).__name__, "exception_message": str(exc)[:500]})
            return _write_stop(root, controller, authority, stop_reason="runtime_exception", started=started, cycles_advanced=cycles_advanced)


def start_live_runtime_2_process(*, runtime_root: str | Path, python_executable: str | None = None) -> subprocess.Popen[Any]:
    cmd = [
        python_executable or sys.executable,
        "-m",
        "orchestration.runtime.live_runtime_2_bounded_unattended",
        "--root",
        str(Path(runtime_root)),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parents[2]), creationflags=creationflags)


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    root = LIVE_RUNTIME_2_DEFAULT_ROOT
    if "--root" in args:
        index = args.index("--root")
        root = Path(args[index + 1])
    result = run_live_runtime_2_bounded_unattended(runtime_root=root)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("result_status") in {"LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PASSED", "LIVE_RUNTIME_2_BOUNDED_UNATTENDED_PARTIAL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
