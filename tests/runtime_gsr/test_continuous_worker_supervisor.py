from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestration.runtime.continuous_mission_foundation import make_satisfied_transfer_record
from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_runtime,
    attach_continuous_mission,
    export_continuous_mission_restart_state,
    exit_observation_with_action_derivation,
    mark_continuous_api_unavailable,
    pause_continuous_mission_for_application,
    queue_continuous_mission_sandbox_work,
    refresh_continuous_mission_frontier,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)
from orchestration.runtime.isolated_evaluator_authoring import compile_isolated_evaluator_authoring_request
from orchestration.runtime.continuous_worker_supervisor import (
    _capability_id_from_subgoal,
    _execute_isolated_evaluator_authoring_provider_call,
    _repository_root_from_supervisor_root,
    ISOLATED_EVALUATOR_AUTHORING_MAX_TOKENS,
    _restart_contract_kind,
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


def _developmental_learning_waiting_for_evaluator(session_id: str = "worker-learning-recovery"):
    contract = {
        "mission_id": "developmental-learning-mission-recovery",
        "mission_type": "developmental_learning",
        "protocol": "developmental_learning_mission_v1",
        "operator_instruction": "Learn spectral theorem.",
        "topic": "spectral_theorem",
    }
    return replace(
        start_continuous_runtime_controller(session_id=session_id),
        continuous_mission_state="awaiting_operator_insight",
        continuous_mission_contract=contract,
        continuous_learning_state={"mission": contract},
        active_work_item="awaiting_developmental_resource_authority",
        continuous_developmental_insight_requests=(
            {
                "request_id": "developmental-resource-authority-recovery",
                "request_kind": "developmental_resource_authority",
                "status": "pending",
                "permitted_responses": ("approve_scoped_authority", "reject_scoped_authority"),
            },
        ),
    )


def _dispatching_evaluator_controller():
    packet = compile_isolated_evaluator_authoring_request(
        mission_id="worker-root-mission",
        requirement={
            "semantic_identity": "worker-root-requirement",
            "topic": "spectral_theorem",
            "target_capability": "complex_inner_product_space_scope",
            "target_behavior": "answer independently authored spectral-theorem cases",
        },
        provider="openai",
        model="gpt-4.1-mini",
    )
    return replace(
        start_continuous_runtime_controller(session_id="worker-root-dispatch"),
        continuous_mission_state="isolated_evaluator_authoring_dispatching",
        continuous_learning_state={
            "isolated_evaluator_authoring": {
                "request": packet,
                "execution_claim": {"claim_id": "claim-root", "claim_state": "dispatching", "execution_attempt_count": 1},
            },
        },
        continuous_api_authority={"calls_consumed": 1},
    )


def _write_supervisor_status(root: Path, repository_root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "supervisor_status.json").write_text(
        json.dumps({"repository_root": str(repository_root)}), encoding="utf-8"
    )


def test_evaluator_dispatch_uses_supplied_supervisor_root_when_cwd_is_unrelated(tmp_path: Path, monkeypatch):
    supervisor_root = tmp_path / "supervisor"
    repository_root = tmp_path / "repository"
    unrelated_cwd = tmp_path / "unrelated"
    repository_root.mkdir()
    unrelated_cwd.mkdir()
    _write_supervisor_status(supervisor_root, repository_root)
    (unrelated_cwd / "supervisor_status.json").write_text(
        json.dumps({"repository_root": str(unrelated_cwd / "wrong-repository")}), encoding="utf-8"
    )
    controller = _dispatching_evaluator_controller()
    captured: dict[str, object] = {}

    import orchestration.runtime.continuous_worker_supervisor as worker
    import orchestration.runtime.v16_env as evaluator_env
    import orchestration.runtime.v16_external_consolidation_evaluator_api_trial as evaluator_api

    def fake_config(path: Path):
        captured["env_path"] = path
        return SimpleNamespace(live_call_permitted=True, provider="openai", model="gpt-4.1-mini", endpoint="https://example.invalid")

    def fake_transport(endpoint, headers, body, timeout):
        captured["endpoint"] = endpoint
        captured["body"] = body
        return {"choices": [{"message": {"content": "{}"}}], "usage": {"total_tokens": 1}}

    def fake_record(received, *, raw_response, provider_error="", provider_usage=None):
        captured["raw_response"] = raw_response
        captured["provider_error"] = provider_error
        captured["provider_usage"] = provider_usage
        return received

    monkeypatch.setattr(evaluator_env, "load_delta_evaluator_env", fake_config)
    monkeypatch.setattr(evaluator_env, "parse_env_file", lambda path: {"DELTA_EVALUATOR_API_KEY": "test-key"})
    monkeypatch.setattr(evaluator_api, "_default_transport", fake_transport)
    monkeypatch.setattr(worker, "record_isolated_evaluator_authoring_provider_result", fake_record)
    monkeypatch.chdir(unrelated_cwd)

    assert _execute_isolated_evaluator_authoring_provider_call(supervisor_root, controller) == controller
    assert captured["env_path"] == repository_root / ".env.local"
    assert captured["endpoint"] == "https://example.invalid"
    assert captured["body"]["max_tokens"] == ISOLATED_EVALUATOR_AUTHORING_MAX_TOKENS == 6000
    assert captured["raw_response"] == {}
    assert captured["provider_error"] == ""


def test_evaluator_dispatch_fails_closed_when_supplied_root_lacks_status_and_never_uses_cwd(tmp_path: Path, monkeypatch):
    supervisor_root = tmp_path / "missing-supervisor-status"
    unrelated_cwd = tmp_path / "unrelated"
    unrelated_cwd.mkdir()
    (unrelated_cwd / "supervisor_status.json").write_text(
        json.dumps({"repository_root": str(tmp_path / "wrong-repository")}), encoding="utf-8"
    )
    controller = _dispatching_evaluator_controller()
    captured: dict[str, object] = {}

    import orchestration.runtime.continuous_worker_supervisor as worker

    def fake_record(received, *, raw_response, provider_error="", provider_usage=None):
        captured["provider_error"] = provider_error
        return received

    monkeypatch.setattr(worker, "record_isolated_evaluator_authoring_provider_result", fake_record)
    monkeypatch.chdir(unrelated_cwd)

    assert _execute_isolated_evaluator_authoring_provider_call(supervisor_root, controller) == controller
    assert "FileNotFoundError" in str(captured["provider_error"])
    assert "missing-supervisor-status" in str(captured["provider_error"])
    assert "wrong-repository" not in str(captured["provider_error"])
    with pytest.raises(FileNotFoundError):
        _repository_root_from_supervisor_root(supervisor_root)


def test_terminal_evaluator_claim_never_replays_even_with_valid_supervisor_root(tmp_path: Path, monkeypatch):
    supervisor_root = tmp_path / "supervisor"
    _write_supervisor_status(supervisor_root, tmp_path / "repository")
    controller = _dispatching_evaluator_controller()
    state = dict(controller.continuous_learning_state)
    authoring = dict(state["isolated_evaluator_authoring"])
    terminal = replace(
        controller,
        continuous_learning_state={
            **state,
            "isolated_evaluator_authoring": {
                **authoring,
                "execution_claim": {**authoring["execution_claim"], "claim_state": "failed"},
            },
        },
    )
    import orchestration.runtime.continuous_worker_supervisor as worker
    monkeypatch.setattr(worker, "record_isolated_evaluator_authoring_provider_result", lambda *_args, **_kwargs: pytest.fail("terminal claim replayed"))
    assert _execute_isolated_evaluator_authoring_provider_call(supervisor_root, terminal) == terminal


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


def test_restart_contract_discriminator_prefers_explicit_learning_type_and_fails_closed():
    learning = _developmental_learning_waiting_for_evaluator().continuous_mission_contract
    assert _restart_contract_kind({**learning, "normalized_goal": "must_not_select_broad_recovery"}) == "developmental_learning"

    broad = _controller_with_subgoal("worker-broad-discriminator").continuous_mission_contract
    assert _restart_contract_kind(broad) == "broad_mission"

    with pytest.raises(ValueError, match="recovery_contract_unknown"):
        _restart_contract_kind({"mission_id": "unknown", "mission_type": "other"})
    with pytest.raises(ValueError, match="recovery_contract_ambiguous_or_unknown"):
        _restart_contract_kind({"mission_id": "ambiguous"})


def test_learning_restart_preserves_pending_evaluator_authority_without_broad_recovery(tmp_path: Path):
    controller = _developmental_learning_waiting_for_evaluator()
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        status = wait_for_worker_status(tmp_path)
        assert status["worker_state"] == "running"
        assert status["continuous_mission_state"] == "awaiting_operator_insight"
        assert status["active_subgoal"] is None
        restart = json.loads((tmp_path / "restart_state.json").read_text(encoding="utf-8"))
        assert restart["continuous_mission_contract"]["mission_type"] == "developmental_learning"
        pending = [item for item in restart["continuous_developmental_insight_requests"] if item.get("status") == "pending"]
        assert [item["request_id"] for item in pending] == ["developmental-resource-authority-recovery"]
        assert "normalized_goal" not in restart["continuous_mission_contract"]
        assert not (tmp_path / "operator_interaction_wait_recovered.json").exists()
    finally:
        _cleanup(supervisor)


def test_pending_resource_fulfillment_waits_outside_legacy_insight_state(tmp_path: Path):
    controller = replace(
        _developmental_learning_waiting_for_evaluator("worker-fulfillment-recovery"),
        continuous_mission_state="developmental_resource_authority_granted_pending_material",
        active_work_item="awaiting_authorized_resource_or_evaluator_material",
        continuous_developmental_insight_requests=(
            {
                "request_id": "developmental-resource-fulfillment-recovery",
                "request_kind": "developmental_resource_fulfillment",
                "status": "pending",
                "permitted_responses": ("supply_fulfillment", "defer_fulfillment"),
            },
        ),
    )
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        status = wait_for_worker_status(tmp_path)
        assert status["worker_state"] == "running"
        assert status["continuous_mission_state"] == "developmental_resource_authority_granted_pending_material"
        assert not (tmp_path / "operator_interaction_wait_recovered.json").exists()
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
        assert status["continuous_mission_state"] in {"observing_for_new_weaknesses", "subgoal_active", "behavioral_evaluation_active"}
        restart_state = (tmp_path / "restart_state.json").read_text(encoding="utf-8")
        assert "external_worker_relaunch_recovery" in restart_state
    finally:
        _cleanup(supervisor)


def test_worker_reassessment_uses_measurable_capability_name_not_opaque_weakness_id():
    assert (
        _capability_id_from_subgoal(
            {
                "weakness_id": "weakness-opaque",
                "subgoal_id": "subgoal-opaque",
                "measurable_objective": "operator_progress_explanation improves beyond operator_progress_explanation=0.0",
            }
        )
        == "operator_progress_explanation"
    )


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


def test_generated_worker_bootstrap_is_import_safe_for_windows_local_model_spawn(tmp_path: Path):
    controller = _controller_with_subgoal("worker-bootstrap-import-guard")
    initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
    )

    bootstrap = (tmp_path / "continuous_worker_bootstrap.py").read_text(encoding="utf-8")

    assert "if __name__ == '__main__':" in bootstrap
    assert "    raise SystemExit(worker_main())" in bootstrap


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
        assert "external_worker_relaunch_recovery" in marker
        assert controller.continuous_active_subgoal["weakness_id"] not in marker
    finally:
        _cleanup(supervisor)


def test_observation_mode_discovers_evidence_and_executes_new_subgoal(tmp_path: Path):
    controller = start_continuous_runtime_controller(session_id="worker-observation-discovery")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        active_work_item="runtime_currently_stable_no_immediate_high_value_work",
    )
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        ledger_path = tmp_path / "subgoal_execution_ledger.json"
        deadline = time.monotonic() + 10
        ledger = {"executions": []}
        while time.monotonic() < deadline:
            if ledger_path.exists():
                import json

                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                if ledger["executions"]:
                    break
            time.sleep(0.05)

        assert ledger["executions"]
        assert (tmp_path / "observation_requeue.json").exists()
        assert ledger["executions"][0]["accepted"] is False
        assert ledger["executions"][0]["disposition"] == "missing_behavioral_failure_contract"
        requeue = json.loads((tmp_path / "observation_requeue.json").read_text(encoding="utf-8"))
        assert requeue["main_goal"]
    finally:
        _cleanup(supervisor)


def test_application_boundary_subgoal_pauses_for_existing_operator_path(tmp_path: Path):
    controller = start_continuous_runtime_controller(session_id="worker-application-boundary")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(
        controller,
        (
            {
                "evidence_source": "application boundary probe",
                "observed_behavior": "application boundary should pause instead of auto-satisfying",
                "first_incorrect_transition": "validated candidate -> non-application disposition -> operator path untested",
                "affected_capability": "application_gate_exercise_coverage",
                "baseline_metric": "application_gate_exercise_coverage=0.0",
                "confidence": 0.85,
                "operator_value": 0.9,
                "severity": 0.8,
                "estimated_implementation_breadth": "small",
                "validation_method": "worker_application_boundary",
            },
        ),
    )
    controller = queue_continuous_mission_sandbox_work(select_continuous_mission_subgoal(refresh_continuous_mission_frontier(controller)))
    controller = pause_continuous_mission_for_application(
        controller,
        candidate_id="validated-candidate-fixture",
        decision_id="application-decision-fixture",
    )
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        deadline = time.monotonic() + 10
        status = {}
        while time.monotonic() < deadline:
            status = wait_for_worker_status(tmp_path)
            if status["continuous_mission_state"] == "awaiting_operator_application":
                break
            time.sleep(0.05)

        assert status["continuous_mission_state"] == "awaiting_operator_application"
        assert status["pending_application_decision_id"]
        assert status["pending_application_decision_id"] == "application-decision-fixture"
    finally:
        _cleanup(supervisor)


def test_operator_application_reject_response_clears_boundary_and_continues(tmp_path: Path):
    controller = start_continuous_runtime_controller(session_id="worker-operator-reject")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(
        controller,
        (
            {
                "evidence_source": "application boundary probe",
                "observed_behavior": "application boundary should accept operator response",
                "first_incorrect_transition": "application pause -> no worker response bridge",
                "affected_capability": "application_gate_exercise_coverage",
                "baseline_metric": "application_gate_exercise_coverage=0.0",
                "confidence": 0.85,
                "operator_value": 0.9,
                "severity": 0.8,
                "estimated_implementation_breadth": "small",
                "validation_method": "worker_application_boundary",
            },
            {
                "evidence_source": "followup probe",
                "observed_behavior": "next distinct work remains available",
                "first_incorrect_transition": "operator decision -> runner should continue",
                "affected_capability": "post_operator_continuation",
                "baseline_metric": "post_operator_continuation=0.0",
                "confidence": 0.84,
                "operator_value": 0.87,
                "severity": 0.72,
                "estimated_implementation_breadth": "small",
                "validation_method": "worker_application_boundary",
            },
        ),
    )
    controller = queue_continuous_mission_sandbox_work(select_continuous_mission_subgoal(refresh_continuous_mission_frontier(controller)))
    controller = pause_continuous_mission_for_application(
        controller,
        candidate_id="validated-candidate-reject-fixture",
        decision_id="application-decision-reject-fixture",
    )
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        deadline = time.monotonic() + 10
        decision_id = ""
        while time.monotonic() < deadline:
            status = wait_for_worker_status(tmp_path)
            decision_id = status.get("pending_application_decision_id") or ""
            if decision_id:
                break
            time.sleep(0.05)
        assert decision_id
        (tmp_path / "operator_application_decision.json").write_text(
            '{"decision_id": "%s", "action": "REJECT_CANDIDATE"}\n' % decision_id,
            encoding="utf-8-sig",
        )

        deadline = time.monotonic() + 10
        status = {}
        while time.monotonic() < deadline:
            status = wait_for_worker_status(tmp_path)
            if status.get("pending_application_decision_id") == "" and status["continuous_mission_state"] != "awaiting_operator_application":
                break
            time.sleep(0.05)

        assert status.get("pending_application_decision_id") == ""
        assert (tmp_path / "operator_application_decision_ledger.json").exists()
        assert not (tmp_path / "operator_application_decision.json").exists()
    finally:
        _cleanup(supervisor)


def test_operator_insight_response_consumed_once_and_resumes_local_work(tmp_path: Path):
    controller = start_continuous_runtime_controller(session_id="worker-operator-insight")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_developmental_self_assessment={
            "developmental_gaps": ("uncertain operator intent for tracked proof",),
            "needs_additional_insight": True,
            "confidence": 0.62,
        },
    )
    controller = exit_observation_with_action_derivation(controller)
    request_id = controller.continuous_developmental_insight_requests[-1]["request_id"]
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        (tmp_path / "operator_interaction_response.json").write_text(
            json.dumps(
                {
                    "request_id": request_id,
                    "response_kind": "insight",
                    "operator_text": "Continue local simulation only.",
                    "selected_option": "continue local simulation only",
                    "approved_scope": "",
                }
            ),
            encoding="utf-8-sig",
        )

        deadline = time.monotonic() + 10
        status = {}
        while time.monotonic() < deadline:
            status = wait_for_worker_status(tmp_path)
            if not (tmp_path / "operator_interaction_response.json").exists():
                restart = json.loads((tmp_path / "restart_state.json").read_text(encoding="utf-8"))
                if any(
                    item["request_id"] == request_id and item.get("status") == "consumed"
                    for item in restart["continuous_developmental_insight_requests"]
                ):
                    break
            time.sleep(0.05)

        assert status["continuous_mission_state"] != "awaiting_operator_insight"
        assert not (tmp_path / "operator_interaction_response.json").exists()
        ledger = json.loads((tmp_path / "operator_interaction_response_ledger.json").read_text(encoding="utf-8"))
        assert ledger["responses"][0]["request_id"] == request_id
        assert ledger["responses"][0]["authority_granted"] is False
        restart = json.loads((tmp_path / "restart_state.json").read_text(encoding="utf-8"))
        assert any(
            item["request_id"] == request_id and item.get("authority_granted") is False
            for item in restart["continuous_operator_interaction_responses"]
        )
        assert not any(
            item.get("request_source") == "repository_bound_candidate_design"
            for item in restart["continuous_developmental_insight_requests"]
        )
    finally:
        _cleanup(supervisor)


def test_awaiting_insight_without_pending_request_recovers_to_next_transition(tmp_path: Path):
    controller = start_continuous_runtime_controller(session_id="worker-insight-recovery")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_operator_insight",
        continuous_developmental_self_assessment={
            "developmental_gaps": ("fixture_scoped_validation",),
            "needs_additional_insight": True,
            "confidence": 0.7,
        },
        continuous_developmental_insight_requests=(
            {
                "request_id": "operator-insight-old",
                "request_kind": "insight",
                "status": "consumed",
                "affected_gap": "fixture_scoped_validation",
                "permitted_responses": ("continue local simulation only",),
            },
        ),
        continuous_operator_interaction_responses=(
            {
                "request_id": "operator-insight-old",
                "response_kind": "insight",
                "selected_option": "continue local simulation only",
                "operator_text": "already consumed",
                "consumed_at": "2026-07-16T00:44:30+00:00",
                "authority_granted": False,
            },
        ),
    )
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        python_executable=sys.executable,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
        execute_active_subgoal=True,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        deadline = time.monotonic() + 10
        status = {}
        while time.monotonic() < deadline:
            status = wait_for_worker_status(tmp_path)
            if status["continuous_mission_state"] != "awaiting_operator_insight":
                break
            time.sleep(0.05)

        assert status["continuous_mission_state"] == "subgoal_active"
        assert (tmp_path / "operator_interaction_wait_recovered.json").exists()
        restart = json.loads((tmp_path / "restart_state.json").read_text(encoding="utf-8"))
        assert restart["continuous_active_subgoal"]
    finally:
        _cleanup(supervisor)
