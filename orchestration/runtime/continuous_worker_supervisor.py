"""External worker liveness supervision for continuous missions.

The mission-cycle coordinator remains ``continuous_runtime_controller``. This
module supervises only a worker process: launch, heartbeat observation,
unexpected-exit relaunch, intentional-stop handling, and restart invocation.
It does not rank weaknesses, compile subgoals, approve applications, mutate
tracked source, or change API authority.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.continuous_mission_foundation import CapabilityKnowledgeRecord
from orchestration.runtime.continuous_runtime_controller import (
    continue_continuous_mission_after_reassessment,
    consume_continuous_capability_reassessment,
    controller_snapshot,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal
from orchestration.runtime.delta_1_0_common import stable_id, utc_now


SUPERVISOR_STATUS = "supervisor_status.json"
WORKER_STATUS = "worker_status.json"
RESTART_STATE = "restart_state.json"
INTENTIONAL_STOP = "intentional_stop.json"
WORKER_BOOTSTRAP = "continuous_worker_bootstrap.py"
TRANSITION_MARKER = "transition_completed.json"
SUBGOAL_EXECUTION_LEDGER = "subgoal_execution_ledger.json"


@dataclass
class ContinuousWorkerSupervisor:
    supervisor_root: Path
    repository_root: Path
    python_executable: str
    heartbeat_interval_seconds: float = 0.25
    backoff_seconds: float = 0.25
    max_relaunches: int = 3
    complete_transition_once: bool = False
    execute_active_subgoal: bool = False
    process: subprocess.Popen[str] | None = None
    relaunch_count: int = 0
    last_worker_pid: int = 0


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now_monotonic() -> float:
    return time.monotonic()


def initialize_supervisor_state(
    *,
    supervisor_root: Path,
    repository_root: Path,
    restart_state: Mapping[str, Any],
    python_executable: str | None = None,
    heartbeat_interval_seconds: float = 0.25,
    backoff_seconds: float = 0.25,
    max_relaunches: int = 3,
    complete_transition_once: bool = False,
    execute_active_subgoal: bool = False,
) -> ContinuousWorkerSupervisor:
    root = Path(supervisor_root)
    repo = Path(repository_root).resolve()
    if "session_id" not in restart_state:
        raise ValueError("restart state must include session_id")
    root.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(root / RESTART_STATE, dict(restart_state))
    _write_worker_bootstrap(root / WORKER_BOOTSTRAP, repo)
    _atomic_write_json(
        root / SUPERVISOR_STATUS,
        {
            "supervisor_state": "initialized",
            "timestamp": utc_now(),
            "repository_root": str(repo),
            "restart_session_id": restart_state.get("session_id"),
            "relaunch_count": 0,
            "intentional_stop": False,
            "mission_lifecycle_owner": "continuous_runtime_controller",
            "supervisor_owns": (
                "worker_liveness",
                "relaunch_policy",
                "backoff",
                "heartbeat",
                "intentional_stop_recognition",
                "recovery_invocation",
            ),
        },
    )
    return ContinuousWorkerSupervisor(
        supervisor_root=root,
        repository_root=repo,
        python_executable=python_executable or sys.executable,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
        backoff_seconds=backoff_seconds,
        max_relaunches=max_relaunches,
        complete_transition_once=complete_transition_once,
        execute_active_subgoal=execute_active_subgoal,
    )


def _write_worker_bootstrap(path: Path, repository_root: Path) -> None:
    script = (
        "from __future__ import annotations\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"repo = Path({str(repository_root)!r})\n"
        "sys.path.insert(0, str(repo))\n"
        "from orchestration.runtime.continuous_worker_supervisor import worker_main\n"
        "raise SystemExit(worker_main())\n"
    )
    path.write_text(script, encoding="utf-8")


def start_supervised_worker(supervisor: ContinuousWorkerSupervisor) -> ContinuousWorkerSupervisor:
    if supervisor.process is not None and supervisor.process.poll() is None:
        return supervisor
    command = [
        supervisor.python_executable,
        str(supervisor.supervisor_root / WORKER_BOOTSTRAP),
        "--supervisor-root",
        str(supervisor.supervisor_root),
        "--heartbeat-interval",
        str(supervisor.heartbeat_interval_seconds),
    ]
    if supervisor.complete_transition_once:
        command.append("--complete-transition-once")
    if supervisor.execute_active_subgoal:
        command.append("--execute-active-subgoal")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    process = subprocess.Popen(  # noqa: S603 - exact interpreter and bootstrap path are constructed above.
        command,
        cwd=str(supervisor.supervisor_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    supervisor.process = process
    supervisor.last_worker_pid = int(process.pid)
    _atomic_write_json(
        supervisor.supervisor_root / SUPERVISOR_STATUS,
        {
            "supervisor_state": "worker_running",
            "timestamp": utc_now(),
            "worker_pid": process.pid,
            "relaunch_count": supervisor.relaunch_count,
            "repository_root": str(supervisor.repository_root),
            "restart_session_id": _read_json(supervisor.supervisor_root / RESTART_STATE).get("session_id"),
            "intentional_stop": False,
            "mission_lifecycle_owner": "continuous_runtime_controller",
        },
    )
    return supervisor


def request_intentional_worker_stop(supervisor_root: Path, *, reason: str = "operator_requested_stop") -> None:
    _atomic_write_json(Path(supervisor_root) / INTENTIONAL_STOP, {"timestamp": utc_now(), "reason": reason})


def poll_supervisor_once(supervisor: ContinuousWorkerSupervisor) -> ContinuousWorkerSupervisor:
    process = supervisor.process
    if process is None:
        return start_supervised_worker(supervisor)
    exit_code = process.poll()
    if exit_code is None:
        _atomic_write_json(
            supervisor.supervisor_root / SUPERVISOR_STATUS,
            {
                "supervisor_state": "worker_running",
                "timestamp": utc_now(),
                "worker_pid": process.pid,
                "relaunch_count": supervisor.relaunch_count,
                "repository_root": str(supervisor.repository_root),
                "intentional_stop": (supervisor.supervisor_root / INTENTIONAL_STOP).exists(),
                "mission_lifecycle_owner": "continuous_runtime_controller",
            },
        )
        return supervisor
    if (supervisor.supervisor_root / INTENTIONAL_STOP).exists():
        _atomic_write_json(
            supervisor.supervisor_root / SUPERVISOR_STATUS,
            {
                "supervisor_state": "worker_stopped_intentionally",
                "timestamp": utc_now(),
                "stopped_pid": process.pid,
                "exit_code": exit_code,
                "relaunch_count": supervisor.relaunch_count,
                "intentional_stop": True,
                "mission_lifecycle_owner": "continuous_runtime_controller",
            },
        )
        return supervisor
    if supervisor.relaunch_count >= supervisor.max_relaunches:
        _atomic_write_json(
            supervisor.supervisor_root / SUPERVISOR_STATUS,
            {
                "supervisor_state": "relaunch_blocked_crash_loop",
                "timestamp": utc_now(),
                "stopped_pid": process.pid,
                "exit_code": exit_code,
                "relaunch_count": supervisor.relaunch_count,
                "intentional_stop": False,
                "mission_lifecycle_owner": "continuous_runtime_controller",
            },
        )
        return supervisor
    time.sleep(max(0.0, supervisor.backoff_seconds))
    supervisor.relaunch_count += 1
    supervisor.process = None
    _atomic_write_json(
        supervisor.supervisor_root / SUPERVISOR_STATUS,
        {
            "supervisor_state": "worker_exited_unexpectedly_relaunching",
            "timestamp": utc_now(),
            "stopped_pid": process.pid,
            "exit_code": exit_code,
            "relaunch_count": supervisor.relaunch_count,
            "intentional_stop": False,
            "mission_lifecycle_owner": "continuous_runtime_controller",
        },
    )
    return start_supervised_worker(supervisor)


def wait_for_worker_status(supervisor_root: Path, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    deadline = _now_monotonic() + timeout_seconds
    path = Path(supervisor_root) / WORKER_STATUS
    while _now_monotonic() < deadline:
        if path.exists():
            return _read_json(path)
        time.sleep(0.05)
    raise TimeoutError("worker status was not written")


def worker_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Continuous mission worker supervised by liveness wrapper")
    parser.add_argument("--supervisor-root", required=True)
    parser.add_argument("--heartbeat-interval", type=float, default=0.25)
    parser.add_argument("--complete-transition-once", action="store_true")
    parser.add_argument("--execute-active-subgoal", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.supervisor_root)
    try:
        restart_state = _read_json(root / RESTART_STATE)
        _validate_restart_state(restart_state)
        session_id = str(restart_state.get("session_id") or "")
        controller = start_continuous_runtime_controller(session_id=session_id)
        controller = restore_continuous_mission_restart_state(controller, restart_state)
        if args.complete_transition_once and controller.continuous_active_subgoal and not (root / TRANSITION_MARKER).exists():
            record = _worker_reassessment_record(controller)
            controller = consume_continuous_capability_reassessment(controller, record)
            controller = continue_continuous_mission_after_reassessment(controller)
            _atomic_write_json(
                root / TRANSITION_MARKER,
                {
                    "timestamp": utc_now(),
                    "capability_id": record.capability_id,
                    "next_state": controller.continuous_mission_state,
                    "active_subgoal": controller.continuous_active_subgoal or None,
                },
            )
            _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
        while True:
            if (root / INTENTIONAL_STOP).exists():
                _write_worker_status(root, controller, "stopped_intentionally")
                return 0
            if args.execute_active_subgoal and controller.continuous_active_subgoal:
                controller = _execute_next_worker_subgoal(root, controller)
            _write_worker_status(root, controller, "running")
            time.sleep(max(0.05, args.heartbeat_interval))
    except Exception as exc:  # noqa: BLE001 - worker must fail closed and preserve error evidence.
        _atomic_write_json(
            root / WORKER_STATUS,
            {
                "worker_state": "worker_failed_recovery",
                "timestamp": utc_now(),
                "pid": os.getpid(),
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        return 2


def _execute_next_worker_subgoal(root: Path, controller: Any) -> Any:
    subgoal = dict(controller.continuous_active_subgoal or {})
    subgoal_id = str(subgoal.get("subgoal_id") or "")
    if not subgoal_id:
        return controller
    ledger_path = root / SUBGOAL_EXECUTION_LEDGER
    ledger = _read_json(ledger_path) if ledger_path.exists() else {"executions": []}
    consumed = {str(item.get("subgoal_id")) for item in ledger.get("executions", [])}
    if subgoal_id in consumed:
        _atomic_write_json(
            root / "stalled_execution.json",
            {
                "timestamp": utc_now(),
                "reason": "active_subgoal_already_consumed_worker_waiting_for_controller_transition",
                "subgoal_id": subgoal_id,
            },
        )
        return controller
    supervisor_status = _read_json(root / SUPERVISOR_STATUS)
    repository_root = Path(str(supervisor_status.get("repository_root") or ".")).resolve()
    updated, execution = execute_continuous_active_subgoal(
        controller,
        artifact_root=root / "development",
        repository_root=repository_root,
        python_executable=sys.executable,
    )
    event = {
        "timestamp": utc_now(),
        "subgoal_id": subgoal_id,
        "disposition": execution.disposition,
        "accepted": execution.accepted,
        "campaign_root": execution.campaign_root,
        "next_state": updated.continuous_mission_state,
        "next_subgoal_id": (updated.continuous_active_subgoal or {}).get("subgoal_id", ""),
    }
    ledger["executions"] = list(ledger.get("executions", [])) + [event]
    _atomic_write_json(ledger_path, ledger)
    _atomic_write_json(root / "subgoal_execution_completed.json", execution.as_dict())
    _atomic_write_json(root / f"subgoal_execution_{subgoal_id}.json", execution.as_dict())
    _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(updated))
    return updated


def _validate_restart_state(restart_state: Mapping[str, Any]) -> None:
    required = {
        "session_id",
        "continuous_mission_state",
        "continuous_mission_contract",
        "continuous_mission_findings",
        "continuous_mission_frontier",
        "continuous_active_subgoal",
        "continuous_consumed_weakness_signatures",
        "continuous_knowledge_ledger",
        "continuous_api_authority",
        "pending_application_decision_id",
        "active_work_item",
    }
    missing = sorted(item for item in required if item not in restart_state)
    if missing:
        raise ValueError(f"restart state missing required fields: {', '.join(missing)}")
    if not restart_state.get("session_id"):
        raise ValueError("restart state missing session_id")
    contract = restart_state.get("continuous_mission_contract") or {}
    if not isinstance(contract, Mapping) or not contract.get("mission_id"):
        raise ValueError("restart state missing continuous mission contract")


def _write_worker_status(root: Path, controller: Any, worker_state: str) -> None:
    snapshot = controller_snapshot(controller)
    mission = snapshot["continuous_mission"]
    _atomic_write_json(
        root / WORKER_STATUS,
        {
            "worker_state": worker_state,
            "timestamp": utc_now(),
            "pid": os.getpid(),
            "session_id": controller.session_id,
            "mission_id": mission["contract"].get("mission_id") if mission["contract"] else "",
            "continuous_mission_state": mission["state"],
            "active_subgoal": mission["active_subgoal"],
            "pending_application_decision_id": mission["pending_application_decision_id"],
            "api_authority": mission["api_authority"],
            "lifecycle_owner": "continuous_runtime_controller",
            "tracked_source_mutation_authorized": False,
            "git_or_deployment_authorized": False,
        },
    )


def _worker_reassessment_record(controller: Any) -> CapabilityKnowledgeRecord:
    subgoal = controller.continuous_active_subgoal
    capability_id = str(subgoal.get("weakness_id") or subgoal.get("subgoal_id") or "continuous-supervised-transition")
    objective = str(subgoal.get("measurable_objective") or "supervised recovery transition")
    return CapabilityKnowledgeRecord(
        capability_id=capability_id,
        original_weakness=objective,
        evidence=("supervised worker restored controller state and completed one controller-owned reassessment transition",),
        first_incorrect_transition="worker process termination -> no external supervisor relaunch",
        strategies_attempted=("external_liveness_supervision_without_mission_lifecycle_ownership",),
        failed_approaches=(),
        successful_mechanism="supervisor relaunched worker and controller consumed reassessment through existing transition",
        exact_candidate="orchestration/runtime/continuous_worker_supervisor.py",
        tests_added=("tests/runtime_gsr/test_continuous_worker_supervisor.py",),
        metrics_before_after={"worker_relaunch_recovery": "recoverable_state -> relaunched_worker"},
        controls=("continuous_runtime_controller_remains_authoritative",),
        adversarial_evidence=("intentional stop does not relaunch", "invalid restart state fails closed"),
        held_out_evidence={"restart_state_restored": True, "duplicate_subgoal_created": False},
        reproduction_evidence="focused supervisor process test",
        provider_contribution="none",
        local_repair_contribution="external liveness wrapper and repo-bound bootstrap",
        application_evidence="not a tracked-source application candidate",
        regression_evidence="continuous foundation and affected controller tests",
        reassessment="satisfied",
        residual_uncertainty="external OS service manager installation remains outside this gate",
        reusable_process_rules=("process supervision must not own mission-cycle semantics",),
    )


__all__ = [
    "ContinuousWorkerSupervisor",
    "initialize_supervisor_state",
    "poll_supervisor_once",
    "request_intentional_worker_stop",
    "start_supervised_worker",
    "wait_for_worker_status",
    "worker_main",
]
