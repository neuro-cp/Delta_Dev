from __future__ import annotations

from pathlib import Path

from orchestration.runtime.continuous_runtime_controller import (
    compile_mission_bound_local_model_learning_request,
    consume_mission_bound_local_model_learning_approval,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal
from orchestration.runtime.deterministic_linear_algebra_evaluator import DATA_PATH, _sealed_data, solve_spectral_task
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


ADVISORY_RESPONSE = """Spectral theorem: every square matrix can be diagonalized by a unitary matrix.
Prerequisites include linear algebra and eigenvalues. Intuition means diagonal directions simplify analysis.
Example: consider a symmetric matrix. A common misconception is that every matrix qualifies, but the theorem does not apply to every matrix.
Practice question: identify a valid application. There is uncertainty about scope limits."""


def _spectral_controller(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr(
        "orchestration.runtime.local_model_request_result_ledger.select_model_lane",
        lambda *_: {"available": True, "lane": "reasoning", "selected_model_id": "test-local-model"},
    )
    controller = compile_mission_bound_local_model_learning_request(
        start_continuous_runtime_controller(session_id="verified-semantic-learning"),
        "Learn the spectral theorem today.",
    )
    request_id = controller.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    ledger.execute_claimed_request(
        request_id,
        {"executor": lambda *_: {"executed": True, "answer": ADVISORY_RESPONSE, "model_id": "test-local-model"}},
    )
    return consume_mission_bound_local_model_learning_approval(controller), ledger, request_id


def test_sealed_spectral_authority_is_separate_from_teaching_resource(monkeypatch, tmp_path: Path):
    controller, _ledger, _request_id = _spectral_controller(monkeypatch, tmp_path)
    bundle = controller.continuous_learning_state["retained_bundle"]
    assert DATA_PATH.exists()
    assert _sealed_data()["authority_id"] == bundle["independent_evaluator"]["evaluator_identity"]
    assert bundle["independent_evaluator"]["teaching_source_isolated"] is True
    assert bundle["sealed_evaluation_cases"]
    assert not any("deterministic_answer" in task for resource in bundle["study_resources"] for task in resource.get("visible_practice_cases") or ())
    visible = next(task for resource in bundle["study_resources"] for task in resource.get("visible_practice_cases") or ())
    answer = solve_spectral_task(visible, bundle["study_resources"])
    assert answer["final_answer"] is True
    assert "sealed" not in " ".join(answer["intermediate_steps"]).lower()


def test_first_failure_revises_resource_then_second_attempt_demonstrates_narrow_capability(monkeypatch, tmp_path: Path):
    controller, ledger, request_id = _spectral_controller(monkeypatch, tmp_path)
    before_inventory = controller.continuous_capability_inventory
    first, first_result = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path / "artifacts",
        repository_root=Path.cwd(),
    )
    first_state = first.continuous_learning_state
    first_attempt = first_state["attempts"][0]
    assert first_result.disposition == "behaviorally_failed"
    assert first_attempt["task_records"]
    assert first_attempt["task_records"][0]["candidate_final_answer"] is True
    assert first_attempt["task_records"][0]["intermediate_reasoning_steps"]
    assert first.continuous_capability_inventory == before_inventory
    localization = first_state["failure_localizations"][0]
    assert localization["implicated_concept"] == "orthogonal_diagonalization_conditions"
    assert localization["failed_case_ids"]
    assert first_state["resource_revisions"][0]["prior_bundle_id"] != first_state["resource_revisions"][0]["revised_bundle_id"]
    assert first.continuous_active_subgoal["attempt_type"] == "guided_study_revision"
    assert ledger.observe_request(request_id)["execution_attempt_count"] == 1

    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="verified-semantic-learning"),
        export_continuous_mission_restart_state(first),
    )
    second, second_result = execute_continuous_active_subgoal(
        restored,
        artifact_root=tmp_path / "artifacts",
        repository_root=Path.cwd(),
    )
    second_state = second.continuous_learning_state
    assert second_result.disposition == "behaviorally_demonstrated"
    assert second_result.validation["control"] == {"target": 1.0}
    assert second_result.validation["held_out"] == {"target": 1.0}
    assert second_result.validation["adversarial"] == {"target": 1.0}
    assert second_result.validation["transfer"] == {"target": 1.0}
    assert second_state["attempts"][1]["task_records"][0]["task_id"] != first_attempt["task_records"][0]["task_id"]
    assert second.continuous_capability_inventory
    assert second_state["next_learning_gap"]["status"] == "resource_evidence_needed"
    assert ledger.observe_request(request_id)["execution_attempt_count"] == 1


def test_restart_and_duplicate_execution_do_not_repeat_attempt_or_evaluation(monkeypatch, tmp_path: Path):
    controller, _ledger, _request_id = _spectral_controller(monkeypatch, tmp_path)
    first, _ = execute_continuous_active_subgoal(controller, artifact_root=tmp_path / "artifacts", repository_root=Path.cwd())
    repeated, duplicate = execute_continuous_active_subgoal(controller, artifact_root=tmp_path / "artifacts", repository_root=Path.cwd())
    assert repeated == controller
    assert duplicate.consumed_once is False
    assert duplicate.disposition == "duplicate_consumption_prevented"
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="verified-semantic-learning"),
        export_continuous_mission_restart_state(first),
    )
    replay = consume_mission_bound_local_model_learning_approval(restored)
    assert replay.continuous_learning_state["failure_localizations"] == restored.continuous_learning_state["failure_localizations"]
    assert len(replay.continuous_learning_state["evaluations"]) == 1
