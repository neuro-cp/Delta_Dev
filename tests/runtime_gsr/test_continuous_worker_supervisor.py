from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

from orchestration.runtime.continuous_mission_foundation import make_satisfied_transfer_record
from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_runtime,
    attach_continuous_mission,
    export_continuous_mission_restart_state,
    mark_continuous_api_unavailable,
    pause_continuous_mission_for_application,
    queue_continuous_mission_sandbox_work,
    refresh_continuous_mission_frontier,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_worker_supervisor import (
    initialize_supervisor_state,
    poll_supervisor_once,
    request_intentional_worker_stop,
    start_supervised_worker,
    wait_for_worker_status,
)


def _json_shape(value):
    import json

    return json.loads(json.dumps(value, sort_keys=True))


def _wait_for_worker_pid(tmp_path: Path, previous_pid: int, *, timeout_seconds: float = 5.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = wait_for_worker_status(tmp_path)
        if int(status["pid"]) != previous_pid:
            return status
        time.sleep(0.05)
    raise TimeoutError("replacement worker did not publish a fresh pid")


def _evidence():
    return (
        {
            "evidence_source": "supervisor pilot",
            "observed_behavior": "worker restart field restoration does not relaunch a dead process",
            "first_incorrect_transition": "worker process terminates -> no external supervisor detects and relaunches it",
            "affected_capability": "external_worker_relaunch_recovery",
            "baseline_metric": "external_worker_relaunch_recovery=0.0",
            "confidence": 0.9,
            "operator_value": 0.95,
            "severity": 0.85,
            "estimated_implementation_breadth": "small",
            "validation_method": "process_relaunch_pilot",
        },
    )


def _controller_with_subgoal(session_id: str = "continuous-worker-supervisor"):
    controller = start_continuous_runtime_controller(session_id=session_id)
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(controller, _evidence())
    controller = refresh_continuous_mission_frontier(controller)
    controller = select_continuous_mission_subgoal(controller)
    return queue_continuous_mission_sandbox_work(controller)


def _start_supervisor(tmp_path: Path, *, restart_state: dict, complete_transition_once: bool = False):
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=restart_state,
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.05,
        max_relaunches=2,
        complete_transition_once=complete_transition_once,
    )
    return start_supervised_worker(supervisor)


def _cleanup(supervisor):
    request_intentional_worker_stop(supervisor.supervisor_root, reason="test_cleanup")
    if supervisor.process is not None:
        try:
            supervisor.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            supervisor.process.kill()
            supervisor.process.wait(timeout=5)


def test_worker_launch_restores_same_mission_without_manual_pythonpath(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PYTHONPATH", raising=False)
    root = tmp_path / "root with spaces"
    controller = _controller_with_subgoal("worker-launch-paths")
    restart_state = export_continuous_mission_restart_state(controller)
    supervisor = _start_supervisor(root, restart_state=restart_state)
    try:
        status = wait_for_worker_status(root)

        assert status["worker_state"] == "running"
        assert status["session_id"] == "worker-launch-paths"
        assert status["mission_id"] == controller.continuous_mission_contract["mission_id"]
        assert status["continuous_mission_state"] == controller.continuous_mission_state
        assert status["active_subgoal"] == _json_shape(controller.continuous_active_subgoal)
        assert status["tracked_source_mutation_authorized"] is False
        assert "PYTHONPATH" not in os.environ
    finally:
        _cleanup(supervisor)


def test_unexpected_worker_exit_relaunches_and_preserves_controller_state(tmp_path: Path):
    controller = _controller_with_subgoal("worker-relaunch")
    restart_state = export_continuous_mission_restart_state(controller)
    supervisor = _start_supervisor(tmp_path, restart_state=restart_state)
    try:
        first_status = wait_for_worker_status(tmp_path)
        first_pid = int(first_status["pid"])
        assert supervisor.process is not None
        supervisor.process.terminate()
        supervisor.process.wait(timeout=5)

        supervisor = poll_supervisor_once(supervisor)
        second_status = _wait_for_worker_pid(tmp_path, first_pid)

        assert supervisor.process is not None
        assert supervisor.process.poll() is None
        assert int(second_status["pid"]) != first_pid
        assert second_status["session_id"] == "worker-relaunch"
        assert second_status["active_subgoal"] == _json_shape(controller.continuous_active_subgoal)
        assert supervisor.relaunch_count == 1
    finally:
        _cleanup(supervisor)


def test_intentional_stop_prevents_relaunch(tmp_path: Path):
    controller = _controller_with_subgoal("worker-intentional-stop")
    supervisor = _start_supervisor(tmp_path, restart_state=export_continuous_mission_restart_state(controller))
    try:
        wait_for_worker_status(tmp_path)
        request_intentional_worker_stop(tmp_path, reason="operator_requested_stop")
        assert supervisor.process is not None
        supervisor.process.wait(timeout=5)
        supervisor = poll_supervisor_once(supervisor)
        status = (tmp_path / "supervisor_status.json").read_text(encoding="utf-8")

        assert "worker_stopped_intentionally" in status
        assert supervisor.relaunch_count == 0
    finally:
        _cleanup(supervisor)


def test_crash_loop_backoff_blocks_after_configured_relaunches(tmp_path: Path):
    restart_state = {"session_id": "crash-loop-invalid"}
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=restart_state,
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
    )
    supervisor = start_supervised_worker(supervisor)
    assert supervisor.process is not None
    supervisor.process.wait(timeout=5)
    supervisor = poll_supervisor_once(supervisor)
    assert supervisor.process is not None
    supervisor.process.wait(timeout=5)
    supervisor = poll_supervisor_once(supervisor)

    text = (tmp_path / "supervisor_status.json").read_text(encoding="utf-8")
    assert "relaunch_blocked_crash_loop" in text
    worker = wait_for_worker_status(tmp_path)
    assert worker["worker_state"] == "worker_failed_recovery"


def test_pending_application_recovery_preserves_exact_decision_once(tmp_path: Path):
    controller = pause_continuous_mission_for_application(
        _controller_with_subgoal("worker-pending-application"),
        candidate_id="candidate-1",
        decision_id="decision-1",
    )
    supervisor = _start_supervisor(tmp_path, restart_state=export_continuous_mission_restart_state(controller))
    try:
        status = wait_for_worker_status(tmp_path)

        assert status["continuous_mission_state"] == "awaiting_operator_application"
        assert status["pending_application_decision_id"] == "decision-1"
        assert status["active_subgoal"] == _json_shape(controller.continuous_active_subgoal)
    finally:
        _cleanup(supervisor)


def test_observation_and_api_unavailable_states_recover_without_new_authority(tmp_path: Path):
    controller = _controller_with_subgoal("worker-api-unavailable")
    controller = mark_continuous_api_unavailable(controller, pending_task="provider-critique-1", reason="quota_exhausted")
    supervisor = _start_supervisor(tmp_path, restart_state=export_continuous_mission_restart_state(controller))
    try:
        status = wait_for_worker_status(tmp_path)

        assert status["api_authority"]["pending_provider_tasks"] == ["provider-critique-1"]
        assert status["api_authority"]["unavailability_reason"] == "quota_exhausted"
        assert status["git_or_deployment_authorized"] is False
    finally:
        _cleanup(supervisor)


def test_worker_can_complete_one_controller_owned_transition_after_relaunch(tmp_path: Path):
    controller = _controller_with_subgoal("worker-transition")
    supervisor = _start_supervisor(
        tmp_path,
        restart_state=export_continuous_mission_restart_state(controller),
        complete_transition_once=True,
    )
    try:
        status = wait_for_worker_status(tmp_path)

        assert (tmp_path / "transition_completed.json").exists()
        assert status["session_id"] == "worker-transition"
        assert status["continuous_mission_state"] in {"observing_for_new_weaknesses", "subgoal_active"}
        restart_state = (tmp_path / "restart_state.json").read_text(encoding="utf-8")
        assert "external_worker_relaunch_recovery" in restart_state
    finally:
        _cleanup(supervisor)


def test_invalid_restart_state_fails_closed_without_fresh_mission(tmp_path: Path):
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state={"session_id": "invalid-state", "continuous_mission_state": "subgoal_active"},
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=0,
    )
    supervisor = start_supervised_worker(supervisor)
    assert supervisor.process is not None
    supervisor.process.wait(timeout=5)
    status = wait_for_worker_status(tmp_path)

    assert status["worker_state"] == "worker_failed_recovery"
    assert "restart state missing required fields" in status["error"]
    assert "KeyError" not in status["error"]


def test_reassessment_record_uses_current_subgoal_not_duplicate_lifecycle(tmp_path: Path):
    controller = _controller_with_subgoal("worker-record")
    controller = replace(controller, continuous_consumed_weakness_signatures=())
    supervisor = _start_supervisor(
        tmp_path,
        restart_state=export_continuous_mission_restart_state(controller),
        complete_transition_once=True,
    )
    try:
        transition = wait_for_worker_status(tmp_path)
        marker = (tmp_path / "transition_completed.json").read_text(encoding="utf-8")

        assert transition["lifecycle_owner"] == "continuous_runtime_controller"
        assert controller.continuous_active_subgoal["weakness_id"] in marker
    finally:
        _cleanup(supervisor)
