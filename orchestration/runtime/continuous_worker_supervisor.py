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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.continuous_mission_foundation import CapabilityKnowledgeRecord
from orchestration.runtime.continuous_runtime_controller import (
    assess_and_advance_continuous_main_goal,
    continue_continuous_mission_after_reassessment,
    consume_continuous_capability_reassessment,
    consume_continuous_mission_application_decision,
    consume_continuous_operator_interaction_response,
    execute_governed_learning_strategy_exact_source_acquisition,
    compile_governed_isolated_evaluator_authoring_api_request,
    begin_isolated_evaluator_authoring_execution,
    begin_constructive_teaching_provider_execution,
    handoff_sealed_isolated_evaluator_to_resource_fulfillment,
    record_isolated_evaluator_authoring_provider_result,
    record_constructive_teaching_provider_result,
    controller_snapshot,
    exit_observation_with_action_derivation,
    export_continuous_mission_restart_state,
    recover_developmental_resource_fulfillment_clarification,
    recover_nonexecutable_sealed_evaluator_execution,
    recover_validated_sealed_evaluator_learning_execution,
    recover_misaligned_v3_learning_execution,
    recover_accepted_boundary_operator_requests,
    recover_missing_continuous_application_review_request,
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
OBSERVATION_EVIDENCE_LEDGER = "observation_evidence_ledger.json"
OPERATOR_APPLICATION_DECISION = "operator_application_decision.json"
OPERATOR_APPLICATION_DECISION_LEDGER = "operator_application_decision_ledger.json"
OPERATOR_INTERACTION_RESPONSE = "operator_interaction_response.json"
OPERATOR_INTERACTION_RESPONSE_LEDGER = "operator_interaction_response_ledger.json"
ISOLATED_EVALUATOR_AUTHORING_MAX_TOKENS = 6000

_BROAD_MISSION_REQUIRED_FIELDS = frozenset(
    {
        "mission_id",
        "original_operator_goal",
        "normalized_goal",
        "accepted_at",
        "local_authority",
        "api_authority",
    }
)
_DEVELOPMENTAL_LEARNING_REQUIRED_FIELDS = frozenset(
    {
        "mission_id",
        "mission_type",
        "protocol",
        "operator_instruction",
        "topic",
    }
)
_OPERATOR_INTERACTION_KINDS = frozenset(
    {
        "insight",
        "clarification",
        "priority_choice",
        "tracked_application_authority",
        "developmental_goal_approval",
        "developmental_resource_authority",
        "developmental_resource_fulfillment",
        "developmental_evaluator_authoring_api",
        "governed_learning_strategy_authority",
    }
)


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
    allow_local_model_execution: bool = False
    process: subprocess.Popen[str] | None = None
    relaunch_count: int = 0
    last_worker_pid: int = 0


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    last_error: OSError | None = None
    for _ in range(10):
        try:
            os.replace(tmp, path)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    try:
        tmp.unlink(missing_ok=True)
    finally:
        if last_error is not None:
            raise last_error


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    allow_local_model_execution: bool = False,
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
        allow_local_model_execution=allow_local_model_execution,
    )


def _write_worker_bootstrap(path: Path, repository_root: Path) -> None:
    script = (
        "from __future__ import annotations\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"repo = Path({str(repository_root)!r})\n"
        "sys.path.insert(0, str(repo))\n"
        "from orchestration.runtime.continuous_worker_supervisor import worker_main\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(worker_main())\n"
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
    if supervisor.allow_local_model_execution:
        command.append("--execute-local-model")
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
            try:
                return _read_json(path)
            except (OSError, ValueError, json.JSONDecodeError):
                # A concurrent atomic replacement can briefly leave the reader
                # between existence and replacement on Windows.
                time.sleep(0.02)
        time.sleep(0.05)
    raise TimeoutError("worker status was not written")


def worker_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Continuous mission worker supervised by liveness wrapper")
    parser.add_argument("--supervisor-root", required=True)
    parser.add_argument("--heartbeat-interval", type=float, default=0.25)
    parser.add_argument("--complete-transition-once", action="store_true")
    parser.add_argument("--execute-active-subgoal", action="store_true")
    parser.add_argument("--execute-local-model", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.supervisor_root)
    try:
        restart_state = _read_json(root / RESTART_STATE)
        _validate_restart_state(restart_state)
        session_id = str(restart_state.get("session_id") or "")
        contract_kind = _restart_contract_kind(dict(restart_state.get("continuous_mission_contract") or {}))
        controller = start_continuous_runtime_controller(session_id=session_id)
        controller = restore_continuous_mission_restart_state(controller, restart_state)
        if contract_kind == "broad_mission":
            controller = recover_missing_continuous_application_review_request(controller)
            controller = recover_accepted_boundary_operator_requests(controller)
        else:
            controller = recover_developmental_resource_fulfillment_clarification(controller)
            controller = recover_nonexecutable_sealed_evaluator_execution(controller)
            controller = recover_validated_sealed_evaluator_learning_execution(controller)
            controller = recover_misaligned_v3_learning_execution(controller)
        _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
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
            if args.execute_active_subgoal and controller.continuous_mission_state == "awaiting_operator_application":
                controller = recover_missing_continuous_application_review_request(controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
                controller = _consume_operator_application_decision_if_present(root, controller)
            elif args.execute_active_subgoal and (
                controller.continuous_mission_state == "awaiting_operator_insight"
                or _has_pending_operator_interaction(controller)
            ):
                if contract_kind == "broad_mission" and controller.continuous_mission_state == "awaiting_operator_insight":
                    controller = recover_accepted_boundary_operator_requests(controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
                controller = _consume_operator_interaction_response_if_present(root, controller)
            elif args.execute_active_subgoal and controller.continuous_mission_state == "developmental_resource_fulfillment_deferred":
                controller = compile_governed_isolated_evaluator_authoring_api_request(controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
            elif args.execute_active_subgoal and controller.continuous_mission_state == "awaiting_isolated_evaluator_authoring_execution":
                controller = begin_isolated_evaluator_authoring_execution(controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
                controller = _execute_isolated_evaluator_authoring_provider_call(root, controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
            elif args.execute_active_subgoal and controller.continuous_mission_state == "constructive_teaching_provider_execution_pending":
                controller = begin_constructive_teaching_provider_execution(controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
                controller = _execute_constructive_teaching_provider_call(root, controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
                _write_worker_status(root, controller, "constructive_teaching_provider_terminal")
                return 0
            elif args.execute_active_subgoal and controller.continuous_mission_state == "constructive_teaching_provider_dispatching":
                controller = record_constructive_teaching_provider_result(controller, raw_response=None, provider_error="provider_dispatch_outcome_indeterminate_after_restart_no_retry")
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
                _write_worker_status(root, controller, "constructive_teaching_provider_indeterminate_terminal")
                return 0
            elif args.execute_active_subgoal and controller.continuous_mission_state == "isolated_evaluator_authoring_dispatching":
                controller = record_isolated_evaluator_authoring_provider_result(
                    controller,
                    raw_response=None,
                    provider_error="provider_dispatch_outcome_indeterminate_after_restart_no_retry",
                )
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
            elif args.execute_active_subgoal and controller.continuous_mission_state == "isolated_evaluator_authoring_result_sealed":
                controller = handoff_sealed_isolated_evaluator_to_resource_fulfillment(controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
            elif args.execute_active_subgoal and controller.continuous_mission_state == "learning_strategy_acquisition_ready":
                controller = execute_governed_learning_strategy_exact_source_acquisition(controller)
                _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(controller))
                _write_worker_status(root, controller, "learning_strategy_acquisition_completed")
                return 0
            elif args.execute_active_subgoal and controller.continuous_active_subgoal:
                _write_worker_status(root, controller, "executing_active_subgoal")
                controller = _execute_next_worker_subgoal(
                    root,
                    controller,
                    allow_local_model_execution=args.execute_local_model,
                )
            elif args.execute_active_subgoal and controller.continuous_mission_state == "observing_for_new_weaknesses":
                controller = _observe_runtime_and_requeue(root, controller)
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


def _repository_root_from_supervisor_root(supervisor_root: Path) -> Path:
    """Resolve the repository only from the worker's persisted supervisor root."""

    status_path = Path(supervisor_root) / SUPERVISOR_STATUS
    supervisor = _read_json(status_path)
    repository_root = str(supervisor.get("repository_root") or "").strip()
    if not repository_root:
        raise ValueError("supervisor_status_missing_repository_root")
    return Path(repository_root).resolve()


def _execute_isolated_evaluator_authoring_provider_call(supervisor_root: Path, controller: Any) -> Any:
    """Use the existing OpenAI transport for one already-persisted claim."""

    state = dict(controller.continuous_learning_state or {})
    authoring = dict(state.get("isolated_evaluator_authoring") or {})
    packet = dict(authoring.get("request") or {})
    claim = dict(authoring.get("execution_claim") or {})
    if claim.get("claim_state") != "dispatching" or not packet:
        return controller
    try:
        from orchestration.runtime.v16_env import load_delta_evaluator_env
        from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport

        repository_root = _repository_root_from_supervisor_root(supervisor_root)
        config = load_delta_evaluator_env(repository_root / ".env.local")
        if (
            not config.live_call_permitted
            or str(config.provider).lower() != str(packet.get("provider") or "").lower()
            or str(config.model) != str(packet.get("model") or "")
        ):
            return record_isolated_evaluator_authoring_provider_result(
                controller,
                raw_response=None,
                provider_error="provider_configuration_not_permitted_or_does_not_match_approved_packet",
            )
        import json
        import os
        from orchestration.runtime.v16_env import parse_env_file

        api_key = os.environ.get("DELTA_EVALUATOR_API_KEY") or parse_env_file(repository_root / ".env.local").get("DELTA_EVALUATOR_API_KEY", "")
        body = {
            "model": packet["model"],
            "temperature": 0,
            # Five fully bound learner/evaluator cases exceed the former
            # completion budget before the strict JSON object can close.
            "max_tokens": ISOLATED_EVALUATOR_AUTHORING_MAX_TOKENS,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "isolated_evaluator_authoring_response",
                    "strict": True,
                    "schema": packet["output_contract"]["native_json_schema"],
                },
            },
            "messages": (
                {"role": "system", "content": packet["system_prompt"]},
                {"role": "user", "content": packet["user_prompt"]},
            ),
        }
        response = _default_transport(
            config.endpoint or "https://api.openai.com/v1/chat/completions",
            {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            body,
            45,
        )
        choices = response.get("choices") if isinstance(response, Mapping) else ()
        message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], Mapping) else {}
        content = str(message.get("content") or "") if isinstance(message, Mapping) else ""
        raw = json.loads(content)
        usage = dict(response.get("usage") or {}) if isinstance(response, Mapping) else {}
        return record_isolated_evaluator_authoring_provider_result(controller, raw_response=raw, provider_usage=usage)
    except Exception as exc:  # noqa: BLE001 - a one-use claim must fail closed.
        return record_isolated_evaluator_authoring_provider_result(
            controller,
            raw_response=None,
            provider_error=f"{type(exc).__name__}: {str(exc)[:240]}",
        )


def _execute_constructive_teaching_provider_call(supervisor_root: Path, controller: Any) -> Any:
    """Dispatch one controller-claimed advisory packet through the established transport."""
    state = dict(controller.continuous_learning_state or {})
    assessment = dict(state.get("governed_constructive_grounding") or {})
    execution = dict(assessment.get("constructive_teaching_provider") or {})
    packet = dict(execution.get("provider_packet") or {})
    claim = dict(execution.get("execution_claim") or {})
    if claim.get("claim_state") != "dispatching" or not packet:
        return controller
    try:
        from orchestration.runtime.v16_env import load_delta_evaluator_env, parse_env_file
        from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport

        repository_root = _repository_root_from_supervisor_root(supervisor_root)
        config = load_delta_evaluator_env(repository_root / ".env.local")
        request = dict(execution.get("authority_request") or {})
        if not config.live_call_permitted or str(config.provider).lower() != str(request.get("provider") or "").lower() or str(config.model) != str(request.get("model") or ""):
            return record_constructive_teaching_provider_result(controller, raw_response=None, provider_error="provider_configuration_not_permitted_or_does_not_match_approved_packet")
        import json
        api_key = os.environ.get("DELTA_EVALUATOR_API_KEY") or parse_env_file(repository_root / ".env.local").get("DELTA_EVALUATOR_API_KEY", "")
        body = {"model": request["model"], "temperature": 0, "max_tokens": int(request.get("maximum_tokens") or 1800), "response_format": {"type": "json_schema", "json_schema": {"name": "constructive_teaching_response", "strict": True, "schema": packet["native_json_schema"]}}, "messages": ({"role": "system", "content": execution["system_prompt"]}, {"role": "user", "content": execution["user_prompt"]})}
        response = _default_transport(config.endpoint or "https://api.openai.com/v1/chat/completions", {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, body, 45)
        choices = response.get("choices") if isinstance(response, Mapping) else ()
        message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], Mapping) else {}
        raw = json.loads(str(message.get("content") or "{}")) if isinstance(message, Mapping) else {}
        return record_constructive_teaching_provider_result(controller, raw_response=raw, provider_usage=dict(response.get("usage") or {}) if isinstance(response, Mapping) else {})
    except Exception as exc:  # noqa: BLE001 - a one-use claim must remain terminal.
        return record_constructive_teaching_provider_result(controller, raw_response=None, provider_error=f"{type(exc).__name__}: {str(exc)[:240]}")


def _execute_next_worker_subgoal(root: Path, controller: Any, *, allow_local_model_execution: bool = False) -> Any:
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
        create_application_request=_subgoal_requires_application_boundary(subgoal),
        allow_local_model_execution=allow_local_model_execution,
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


def _subgoal_requires_application_boundary(subgoal: Mapping[str, Any]) -> bool:
    text = json.dumps(subgoal, sort_keys=True).lower()
    return "application_gate" in text or "operator application path" in text or "application boundary" in text


def _consume_operator_application_decision_if_present(root: Path, controller: Any) -> Any:
    decision_path = root / OPERATOR_APPLICATION_DECISION
    if not decision_path.exists():
        return controller
    payload = _read_json(decision_path)
    decision_id = str(payload.get("decision_id") or "")
    action = str(payload.get("action") or "")
    if decision_id != controller.pending_application_decision_id:
        _atomic_write_json(
            root / "operator_application_decision_rejected.json",
            {
                "timestamp": utc_now(),
                "reason": "decision_id_does_not_match_pending_application_boundary",
                "received_decision_id": decision_id,
                "pending_decision_id": controller.pending_application_decision_id,
            },
        )
        return controller
    consumed = consume_continuous_mission_application_decision(controller, decision_id=decision_id, action=action)
    record = _operator_application_reassessment_record(controller, action, decision_id)
    reassessed = consume_continuous_capability_reassessment(consumed, record)
    continued = continue_continuous_mission_after_reassessment(reassessed)
    ledger_path = root / OPERATOR_APPLICATION_DECISION_LEDGER
    ledger = _read_json(ledger_path) if ledger_path.exists() else {"decisions": []}
    ledger["decisions"] = list(ledger.get("decisions", [])) + [
        {
            "timestamp": utc_now(),
            "decision_id": decision_id,
            "action": action,
            "capability_id": record.capability_id,
            "next_state": continued.continuous_mission_state,
            "next_subgoal_id": (continued.continuous_active_subgoal or {}).get("subgoal_id", ""),
            "tracked_source_mutated": False,
        }
    ]
    _atomic_write_json(ledger_path, ledger)
    processed_path = root / f"operator_application_decision_consumed_{decision_id}.json"
    _atomic_write_json(processed_path, {**payload, "consumed_at": utc_now(), "tracked_source_mutated": False})
    try:
        decision_path.unlink()
    except FileNotFoundError:
        pass
    _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(continued))
    return continued


def _consume_operator_interaction_response_if_present(root: Path, controller: Any) -> Any:
    response_path = root / OPERATOR_INTERACTION_RESPONSE
    pending_runtime_requests = tuple(
        item
        for item in (controller.continuous_developmental_insight_requests or ())
        if item.get("status") == "pending" and item.get("request_kind") in _OPERATOR_INTERACTION_KINDS
    )
    if not response_path.exists() and not pending_runtime_requests:
        recovered = exit_observation_with_action_derivation(
            replace(
                controller,
                continuous_mission_state="observing_for_new_weaknesses",
                active_work_item="runtime_currently_stable_no_immediate_high_value_work",
            )
        )
        _atomic_write_json(
            root / "operator_interaction_wait_recovered.json",
            {
                "timestamp": utc_now(),
                "reason": "awaiting_operator_insight_without_pending_runtime_request",
                "next_state": recovered.continuous_mission_state,
                "next_subgoal_id": (recovered.continuous_active_subgoal or {}).get("subgoal_id", ""),
            },
        )
        _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(recovered))
        return recovered
    if not response_path.exists():
        return controller
    payload = _read_json(response_path)
    request_id = str(payload.get("request_id") or "")
    selected_option = str(payload.get("selected_option") or "")
    pending = tuple(
        item
        for item in (controller.continuous_developmental_insight_requests or ())
        if item.get("request_id") == request_id and item.get("status") == "pending"
    )
    if not pending:
        _atomic_write_json(
            root / "operator_interaction_response_rejected.json",
            {
                "timestamp": utc_now(),
                "reason": "request_id_does_not_match_pending_interaction",
                "received_request_id": request_id,
            },
        )
        return controller
    consumed = consume_continuous_operator_interaction_response(
        controller,
        request_id=request_id,
        response_kind=str(payload.get("response_kind") or "insight"),
        operator_text=str(payload.get("operator_text") or ""),
        selected_option=selected_option,
        approved_scope=str(payload.get("approved_scope") or ""),
    )
    ledger_path = root / OPERATOR_INTERACTION_RESPONSE_LEDGER
    ledger = _read_json(ledger_path) if ledger_path.exists() else {"responses": []}
    ledger["responses"] = list(ledger.get("responses", [])) + [
        {
            "timestamp": utc_now(),
            "request_id": request_id,
            "selected_option": selected_option,
            "next_state": consumed.continuous_mission_state,
            "next_subgoal_id": (consumed.continuous_active_subgoal or {}).get("subgoal_id", ""),
            "authority_granted": False,
        }
    ]
    _atomic_write_json(ledger_path, ledger)
    _atomic_write_json(root / f"operator_interaction_response_consumed_{request_id}.json", {**payload, "consumed_at": utc_now(), "authority_granted": False})
    try:
        response_path.unlink()
    except FileNotFoundError:
        pass
    _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(consumed))
    return consumed


def _has_pending_operator_interaction(controller: Any) -> bool:
    return any(
        item.get("status") == "pending" and item.get("request_kind") in _OPERATOR_INTERACTION_KINDS
        for item in (controller.continuous_developmental_insight_requests or ())
    )


def _operator_application_reassessment_record(controller: Any, action: str, decision_id: str) -> CapabilityKnowledgeRecord:
    subgoal = dict(controller.continuous_active_subgoal or {})
    objective = str(subgoal.get("measurable_objective") or "operator application decision")
    capability_id = _capability_id_from_subgoal(subgoal)
    satisfied = action == "APPLY_VALIDATED_CANDIDATE"
    return CapabilityKnowledgeRecord(
        capability_id=capability_id,
        original_weakness=objective,
        evidence=(f"operator_application_decision:{decision_id}:{action}",),
        first_incorrect_transition=str(subgoal.get("first_incorrect_transition") or "application boundary -> no running operator response bridge"),
        strategies_attempted=("existing_live45_application_boundary", "worker_operator_response_bridge"),
        failed_approaches=() if satisfied else (f"operator_action:{action}",),
        successful_mechanism="operator application decision consumed through existing controller boundary",
        exact_candidate="operator_application_decision.json",
        tests_added=("tests/runtime_gsr/test_continuous_worker_supervisor.py",),
        metrics_before_after={"operator_decision_consumed": True, "tracked_source_mutated": False},
        controls=("tracked_source_remains_operator_controlled",),
        adversarial_evidence=("mismatched decision id rejected",),
        held_out_evidence={"decision_consumed_once": True},
        reproduction_evidence=str(decision_id),
        provider_contribution="none",
        local_repair_contribution="file-bound operator response bridge",
        application_evidence="tracked application not performed by worker",
        regression_evidence="focused continuous worker supervisor tests",
        reassessment="satisfied" if satisfied else "rejected",
        residual_uncertainty="tracked-source apply remains outside worker authority",
        reusable_process_rules=("operator responses must be one-use and decision-id bound",),
    )


def _observe_runtime_and_requeue(root: Path, controller: Any) -> Any:
    observation = dict(controller.continuous_observation_state or {})
    if observation.get("candidate_design_evidence_exhausted"):
        marker = root / "repository_bound_candidate_design_blocked.json"
        if not marker.exists():
            _atomic_write_json(
                marker,
                {
                    "timestamp": utc_now(),
                    "reason": "no_new_repository_bound_evidence_after_untrusted_candidate_design_rejection",
                    "scope_signature": observation.get("candidate_design_evidence_scope_signature"),
                    "blocked_subgoal_id": observation.get("blocked_subgoal_id", ""),
                },
            )
        return controller
    queued = assess_and_advance_continuous_main_goal(controller)
    _atomic_write_json(
        root / "observation_requeue.json",
        {
            "timestamp": utc_now(),
            "next_state": queued.continuous_mission_state,
            "main_goal": queued.continuous_main_goal or None,
            "completed_main_goal_count": len(queued.continuous_completed_main_goals),
            "active_subgoal": queued.continuous_active_subgoal or None,
        },
    )
    _atomic_write_json(root / RESTART_STATE, export_continuous_mission_restart_state(queued))
    return queued


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


def _restart_contract_kind(contract: Mapping[str, Any]) -> str:
    """Classify a persisted contract before selecting its recovery owner.

    Broad missions predate an explicit type field, so their bounded legacy
    signature is accepted only when every required field is present. The
    developmental-learning discriminator always takes precedence.
    """

    declared_type = str(contract.get("mission_type") or "")
    if declared_type:
        if declared_type != "developmental_learning":
            raise ValueError(f"recovery_contract_unknown:{declared_type}")
        missing = sorted(_DEVELOPMENTAL_LEARNING_REQUIRED_FIELDS - set(contract))
        if missing:
            raise ValueError(f"recovery_required_field_missing:developmental_learning:{','.join(missing)}")
        if str(contract.get("protocol") or "") != "developmental_learning_mission_v1":
            raise ValueError("recovery_schema_unsupported:developmental_learning")
        return "developmental_learning"

    missing = sorted(_BROAD_MISSION_REQUIRED_FIELDS - set(contract))
    if not missing:
        return "broad_mission"
    raise ValueError(f"recovery_contract_ambiguous_or_unknown:missing:{','.join(missing)}")


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
        "pending_operator_interactions": mission["developmental_insight_requests"],
        "api_authority": mission["api_authority"],
            "lifecycle_owner": "continuous_runtime_controller",
            "tracked_source_mutation_authorized": False,
            "git_or_deployment_authorized": False,
        },
    )


def _worker_reassessment_record(controller: Any) -> CapabilityKnowledgeRecord:
    subgoal = controller.continuous_active_subgoal
    objective = str(subgoal.get("measurable_objective") or "supervised recovery transition")
    capability_id = _capability_id_from_subgoal(subgoal)
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


def _capability_id_from_subgoal(subgoal: Mapping[str, Any]) -> str:
    objective = str(subgoal.get("measurable_objective") or "")
    if " improves beyond " in objective:
        capability = objective.split(" improves beyond ", 1)[0].strip()
        if capability:
            return capability
    if objective:
        return stable_id("capability", objective)
    return str(subgoal.get("weakness_id") or subgoal.get("subgoal_id") or "continuous-supervised-transition")


__all__ = [
    "ContinuousWorkerSupervisor",
    "initialize_supervisor_state",
    "poll_supervisor_once",
    "request_intentional_worker_stop",
    "start_supervised_worker",
    "wait_for_worker_status",
    "worker_main",
]
