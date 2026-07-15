from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_runtime,
    attach_continuous_mission,
    queue_continuous_mission_sandbox_work,
    refresh_continuous_mission_frontier,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal


def _controller_for_execution(*, session_id: str = "executor-test", capability: str = "continuous_subgoal_execution_bridge"):
    controller = start_continuous_runtime_controller(session_id=session_id)
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(
        controller,
        (
            {
                "evidence_source": "stopped free-run evidence",
                "observed_behavior": "sandbox_development_active does not start a governed development campaign",
                "first_incorrect_transition": "controller-owned active_subgoal -> sandbox_development_active -> no executor consumed it",
                "affected_capability": capability,
                "baseline_metric": f"{capability}=0.0",
                "confidence": 0.91,
                "operator_value": 0.95,
                "severity": 0.9,
                "estimated_implementation_breadth": "small",
                "validation_method": "execution_bridge_focused_validation",
            },
        ),
    )
    controller = refresh_continuous_mission_frontier(controller)
    controller = select_continuous_mission_subgoal(controller)
    return queue_continuous_mission_sandbox_work(controller)


def test_active_subgoal_is_consumed_once_and_creates_real_sandbox_work(tmp_path: Path):
    controller = _controller_for_execution()
    updated, result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
    )
    duplicate_controller, duplicate = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
    )

    assert result.accepted is True
    assert result.consumed_once is True
    assert result.source_inspection["file_count"] > 0
    assert result.baseline["exit_code"] == 0
    assert result.candidate["tracked_source_mutated"] is False
    assert result.candidate["objective_digest"]
    assert result.candidate["capability_key"] == "continuous_subgoal_execution_bridge"
    assert result.reassessment["capability_id"] == "continuous_subgoal_execution_bridge"
    assert "weakness-" not in result.reassessment["capability_id"]
    assert result.validation["passed"] is True
    assert result.clean_reproduction["passed"] is True
    assert "source_inspection_completed" in result.meaningful_transition_timestamps
    assert updated.continuous_mission_state in {"observing_for_new_weaknesses", "subgoal_active"}
    assert duplicate.consumed_once is False
    assert duplicate.disposition == "duplicate_consumption_prevented"
    assert duplicate_controller == controller


def test_liveness_only_subgoal_is_rejected_as_stalled_execution(tmp_path: Path):
    controller = _controller_for_execution(capability="continuous_free_run_operation")
    # Simulate the bad free-run target that only proves the mission is alive.
    controller = replace(
        controller,
        continuous_active_subgoal={
            **controller.continuous_active_subgoal,
            "baseline": "active_continuous_mission=0.0",
            "measurable_objective": "active_continuous_mission improves beyond active_continuous_mission=0.0",
        },
    )
    updated, result = execute_continuous_active_subgoal(controller, artifact_root=tmp_path, repository_root=Path.cwd())

    assert updated == controller
    assert result.accepted is False
    assert result.stalled_execution is True
    assert result.disposition == "rejected_liveness_only_subgoal"
    assert result.source_inspection == {}


def test_existing_controller_application_boundary_is_reused(tmp_path: Path):
    controller = _controller_for_execution(session_id="executor-application")
    updated, result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        create_application_request=True,
    )

    assert result.application_request["state"] == "pending_operator_application_review"
    assert result.application_request["application_path_reused"] == "continuous_runtime_controller.pause_continuous_mission_for_application"
    assert updated.continuous_mission_state == "awaiting_operator_application"
    assert updated.pending_application_decision_id == result.application_request["decision_id"]
    assert result.candidate["tracked_source_mutated"] is False


def test_local_model_and_reference_advisory_resources_are_logged_without_paid_api(tmp_path: Path):
    controller = _controller_for_execution(session_id="executor-resources", capability="model_reference_executor_bridge")
    controller = replace(
        controller,
        continuous_active_subgoal={
            **controller.continuous_active_subgoal,
            "measurable_objective": "use local model and wiki reference to improve model_reference_executor_bridge beyond 0.0",
            "adversarial_tests": "consult local model and reference evidence without paid API authority",
            "wiki_query": "Software testing",
        },
    )

    def local_model(payload):
        return {"model_id": "local-test-model", "result": "diagnosis_complete", "input_keys": tuple(payload)}

    def reference(payload):
        return {"source": "built_in_wiki_reference", "result": "reference_complete", "provenance": "local bounded fixture"}

    _, result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        local_model_adapter=local_model,
        reference_adapter=reference,
    )

    resources = {item.resource_type: item for item in result.resource_usage}
    assert resources["local_model"].resource_id == "local-test-model"
    assert resources["local_model"].provenance["authoritative"] is False
    assert resources["built_in_reference"].resource_id == "built_in_wiki_reference"
    assert "local model/reference" in result.reassessment["reassessment"] or result.reassessment["reassessment"] == "satisfied"
    assert controller.continuous_api_authority["enabled"] is False


def test_clean_reproduction_uses_declared_inputs_without_repo_import_leak(tmp_path: Path):
    controller = _controller_for_execution(session_id="executor-repro")
    _, result = execute_continuous_active_subgoal(controller, artifact_root=tmp_path, repository_root=Path.cwd())

    reproduction_root = Path(result.clean_reproduction["root"])
    assert (reproduction_root / "candidate" / "continuous_candidate.py").exists()
    assert result.clean_reproduction["passed"] is True
    validation_script = (reproduction_root / "validate_candidate.py").read_text(encoding="utf-8")
    assert "orchestration.runtime" not in validation_script


def test_worker_execution_mode_persists_result_and_restarts_without_duplicate(tmp_path: Path):
    from orchestration.runtime.continuous_worker_supervisor import (
        initialize_supervisor_state,
        request_intentional_worker_stop,
        start_supervised_worker,
        wait_for_worker_status,
    )
    from orchestration.runtime.continuous_runtime_controller import export_continuous_mission_restart_state

    controller = _controller_for_execution(session_id="executor-worker-mode")
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        execute_active_subgoal=True,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        status = wait_for_worker_status(tmp_path)
        result_path = tmp_path / "subgoal_execution_completed.json"
        assert result_path.exists()
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["accepted"] is True
        assert status["lifecycle_owner"] == "continuous_runtime_controller"
    finally:
        request_intentional_worker_stop(tmp_path, reason="test_complete")
        if supervisor.process is not None:
            supervisor.process.wait(timeout=5)


def test_worker_execution_mode_continues_to_next_distinct_subgoal(tmp_path: Path):
    from orchestration.runtime.continuous_worker_supervisor import (
        initialize_supervisor_state,
        request_intentional_worker_stop,
        start_supervised_worker,
    )
    from orchestration.runtime.continuous_runtime_controller import export_continuous_mission_restart_state

    controller = start_continuous_runtime_controller(session_id="executor-worker-multi")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(
        controller,
        (
            {
                "evidence_source": "bridge defect",
                "observed_behavior": "first executable weakness",
                "first_incorrect_transition": "active subgoal one -> no executor",
                "affected_capability": "continuous_subgoal_execution_bridge",
                "baseline_metric": "continuous_subgoal_execution_bridge=0.0",
                "confidence": 0.94,
                "operator_value": 0.96,
                "severity": 0.9,
                "estimated_implementation_breadth": "small",
                "validation_method": "multi_subgoal_worker",
            },
            {
                "evidence_source": "resource defect",
                "observed_behavior": "second executable weakness",
                "first_incorrect_transition": "next active subgoal -> worker returned to heartbeat",
                "affected_capability": "secondary_executor_bridge",
                "baseline_metric": "secondary_executor_bridge=0.0",
                "confidence": 0.8,
                "operator_value": 0.91,
                "severity": 0.72,
                "estimated_implementation_breadth": "small",
                "validation_method": "multi_subgoal_worker",
            },
        ),
    )
    controller = queue_continuous_mission_sandbox_work(select_continuous_mission_subgoal(refresh_continuous_mission_frontier(controller)))
    supervisor = initialize_supervisor_state(
        supervisor_root=tmp_path,
        repository_root=Path.cwd(),
        restart_state=export_continuous_mission_restart_state(controller),
        execute_active_subgoal=True,
        heartbeat_interval_seconds=0.05,
        backoff_seconds=0.01,
        max_relaunches=1,
    )
    supervisor = start_supervised_worker(supervisor)
    try:
        ledger_path = tmp_path / "subgoal_execution_ledger.json"
        import time

        deadline = time.monotonic() + 10
        ledger = {"executions": []}
        while time.monotonic() < deadline:
            if ledger_path.exists():
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                if len(ledger["executions"]) >= 2:
                    break
            time.sleep(0.05)
        assert len(ledger["executions"]) >= 2
        subgoals = [item["subgoal_id"] for item in ledger["executions"]]
        assert len(set(subgoals)) == len(subgoals)
        assert (tmp_path / f"subgoal_execution_{subgoals[0]}.json").exists()
        assert (tmp_path / f"subgoal_execution_{subgoals[1]}.json").exists()
    finally:
        request_intentional_worker_stop(tmp_path, reason="test_complete")
        if supervisor.process is not None:
            supervisor.process.wait(timeout=5)
