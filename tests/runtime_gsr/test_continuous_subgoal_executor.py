from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_runtime,
    attach_continuous_mission,
    consume_continuous_operator_interaction_response,
    queue_continuous_mission_sandbox_work,
    refresh_continuous_mission_frontier,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import (
    _inspect_sources,
    _repository_bound_design_prompt,
    _validate_repository_bound_design,
    execute_continuous_active_subgoal,
)


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


def test_abstract_subgoal_records_one_repository_bound_design_and_never_creates_static_candidate(tmp_path: Path):
    controller = _controller_for_execution()
    updated, result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        local_model_adapter=lambda payload: {
            "model_id": "local-test-model",
            "result": "local_model_executed",
            "executed": True,
            "answer": "This is advice without a repository-bound JSON target.",
            "provider_calls_performed": False,
        },
    )
    duplicate_controller, duplicate = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
    )

    assert result.accepted is False
    assert result.consumed_once is True
    assert result.source_inspection["file_count"] > 0
    assert result.disposition == "candidate_design_requires_concrete_behavior_contract"
    assert result.candidate["state"] == "not_created"
    assert result.validation["not_run"] == "no concrete candidate source exists"
    assert result.reassessment["capability_id"] == "continuous_subgoal_execution_bridge"
    assert "weakness-" not in result.reassessment["capability_id"]
    assert "source_inspection_completed" in result.meaningful_transition_timestamps
    assert updated.continuous_mission_state == "awaiting_operator_insight"
    pending = [item for item in updated.continuous_developmental_insight_requests if item["status"] == "pending"]
    assert len(pending) == 1
    request = pending[0]
    assert request["request_source"] == "repository_bound_candidate_design"
    assert request["authority_granted"] is False
    assert updated.continuous_observation_state["candidate_design_evidence_exhausted"] is True
    artifact = tmp_path / "subgoal_executions" / result.subgoal_id / "repository_bound_candidate_design.json"
    assert artifact.exists()
    assert "candidate_metric" not in artifact.read_text(encoding="utf-8")
    assert duplicate.consumed_once is False
    assert duplicate.disposition == "duplicate_consumption_prevented"
    assert duplicate_controller == controller

    boundary = consume_continuous_operator_interaction_response(
        updated,
        request_id=request["request_id"],
        response_kind="insight",
        operator_text="Treat this ungrounded abstract branch as an accepted boundary.",
        selected_option="treat as accepted boundary",
    )
    blocked = select_continuous_mission_subgoal(boundary)
    assert blocked.continuous_mission_state == "observing_for_new_weaknesses"
    assert blocked.continuous_active_subgoal == {}
    assert blocked.continuous_observation_state["observation_reason"] == "repository_bound_candidate_design_evidence_scope_exhausted"


def test_prefilled_design_mapping_cannot_restore_the_removed_static_candidate_path(tmp_path: Path):
    controller = _controller_for_execution()
    controller = replace(
        controller,
        continuous_active_subgoal={
            **controller.continuous_active_subgoal,
            "candidate_design": {"affected_path": "orchestration/runtime/continuous_subgoal_executor.py"},
        },
    )

    _, result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        local_model_adapter=lambda payload: {
            "model_id": "local-test-model",
            "result": "local_model_executed",
            "executed": True,
            "answer": "not a valid grounded design",
            "provider_calls_performed": False,
        },
    )

    assert result.accepted is False
    assert result.disposition == "candidate_design_requires_concrete_behavior_contract"
    assert not (tmp_path / "candidate" / "continuous_candidate.py").exists()


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


def test_repository_bound_design_requires_an_inspected_implementation_and_test_path():
    controller = _controller_for_execution()
    subgoal = controller.continuous_active_subgoal
    inspection = _inspect_sources(Path.cwd(), subgoal)
    paths = [item["path"] for item in inspection["files"]]
    implementation_path = next(path for path in paths if path.endswith("continuous_subgoal_executor.py"))
    evidence_path = next(path for path in paths if path.endswith("test_continuous_subgoal_executor.py"))

    prompt = _repository_bound_design_prompt(subgoal, inspection, Path.cwd())
    design = _validate_repository_bound_design(
        {
            "executed": True,
            "answer": json.dumps(
                {
                    "affected_path": implementation_path,
                    "evidence_path": evidence_path,
                    "failure_mechanism": "abstract subgoals lack a behavior contract",
                    "candidate_behavior": "require inspected test evidence before a candidate can exist",
                    "independent_evidence_needed": "the named focused test",
                    "validation_target": "the focused test rejects a fabricated candidate",
                }
            ),
        },
        inspection,
    )

    assert f"PATH: {implementation_path}" in prompt
    assert f"PATH: {evidence_path}" in prompt
    assert design["grounded"] is True
    assert design["evidence_path_is_independent"] is True


def test_worker_execution_mode_persists_one_grounded_block_without_local_model_execution(tmp_path: Path):
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
        result_path = tmp_path / "subgoal_execution_completed.json"
        import time

        deadline = time.monotonic() + 5
        status = {}
        while time.monotonic() < deadline:
            status = wait_for_worker_status(tmp_path)
            if result_path.exists():
                break
            time.sleep(0.05)
        assert result_path.exists()
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["accepted"] is False
        assert result["disposition"] == "candidate_design_requires_concrete_behavior_contract"
        assert status["lifecycle_owner"] == "continuous_runtime_controller"
    finally:
        request_intentional_worker_stop(tmp_path, reason="test_complete")
        if supervisor.process is not None:
            supervisor.process.wait(timeout=5)
