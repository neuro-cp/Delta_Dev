from __future__ import annotations

from orchestration.runtime.continuous_runtime_controller import (
    compile_mission_bound_local_model_learning_request,
    consume_mission_bound_local_model_learning_approval,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_learning import classify_developmental_instruction
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal


def _lane_available(monkeypatch):
    monkeypatch.setattr(
        "orchestration.runtime.continuous_runtime_controller.select_model_lane",
        lambda _message, _intent: {"lane": "reasoning_analysis", "available": True, "selected_model": "local-test", "selected_model_id": "local-test-1"},
    )


def _response(_message, _lane):
    return {
        "executed": True,
        "model_id": "local-test-1",
        "execution_adapter": "controlled_rc2_fixture",
        "answer": """The spectral theorem has prerequisites in linear algebra.
        The theorem statement concerns self-adjoint operators. Intuition: orthogonal directions simplify the operator.
        Example: a symmetric matrix can be analyzed in an orthonormal basis.
        A common misconception is that every real matrix has an orthonormal eigenbasis.
        Practice question: identify when orthogonal diagonalization applies.""",
        "provider_calls_performed": False,
    }


def _sealed_cases():
    dimension = "spectral_theorem_understanding"
    components = ("prerequisites", "concept_statement", "intuitive_explanation", "worked_example", "misconceptions", "practice_questions")
    return tuple(
        {"case_id": f"sealed-{kind}", "kind": kind, "capability_dimension": dimension, "required_components": components}
        for kind in ("baseline", "control", "held_out", "adversarial", "transfer")
    )


def test_spectral_request_reuses_one_pending_request_and_never_executes_without_approval(monkeypatch):
    _lane_available(monkeypatch)
    controller = compile_mission_bound_local_model_learning_request(
        start_continuous_runtime_controller(session_id="spectral-pending"), "Learn the spectral theorem today."
    )
    assert classify_developmental_instruction("Learn the spectral theorem today.")["topic"] == "spectral_theorem"
    assert controller.continuous_mission_state == "learning_local_model_request_pending"
    request = controller.continuous_learning_state["local_model_request"]
    assert request["status"] == "PENDING_OPERATOR_APPROVAL"
    assert controller.continuous_learning_state["local_model_execution_count"] == 0
    replay = compile_mission_bound_local_model_learning_request(controller, "Learn the spectral theorem today.")
    assert replay.continuous_learning_state["local_model_request"]["request_id"] == request["request_id"]
    assert replay.continuous_learning_state["local_model_execution_count"] == 0


def test_approved_model_evidence_is_exact_once_and_capability_waits_for_sealed_evaluation(monkeypatch):
    _lane_available(monkeypatch)
    controller = compile_mission_bound_local_model_learning_request(
        start_continuous_runtime_controller(session_id="spectral-approved"), "Learn the spectral theorem today."
    )
    updated = consume_mission_bound_local_model_learning_approval(
        controller, model_executor=_response, sealed_evaluation_cases=_sealed_cases()
    )
    state = updated.continuous_learning_state
    assert state["local_model_execution_count"] == 1
    assert state["local_model_request"]["status"] == "COMPLETED"
    assert state["local_model_bridge"]["evidence_sufficiency_state"] == "sufficient_for_provisional_resource"
    assert state["local_model_bridge"]["local_model_response_digest"]
    assert state["evaluations"] == ()  # Model prose did not promote capability.
    assert updated.continuous_active_subgoal["execution_kind"] == "developmental_learning"
    replay = consume_mission_bound_local_model_learning_approval(updated, model_executor=lambda *_: (_ for _ in ()).throw(AssertionError("duplicate call")))
    assert replay.continuous_learning_state["local_model_execution_count"] == 1
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="spectral-approved"), export_continuous_mission_restart_state(updated)
    )
    assert restored.continuous_learning_state["local_model_request"]["result_id"] == state["local_model_request"]["result_id"]
    assert consume_mission_bound_local_model_learning_approval(restored, model_executor=lambda *_: (_ for _ in ()).throw(AssertionError("restart duplicate"))).continuous_learning_state["local_model_execution_count"] == 1


def test_unavailable_empty_and_contradictory_model_results_never_create_a_bundle(monkeypatch):
    _lane_available(monkeypatch)
    seed = compile_mission_bound_local_model_learning_request(
        start_continuous_runtime_controller(session_id="spectral-negative"), "Learn the spectral theorem today."
    )
    empty = consume_mission_bound_local_model_learning_approval(seed, model_executor=lambda *_: {"executed": True, "answer": "", "model_id": "local-test"})
    assert empty.continuous_mission_state == "learning_model_evidence_insufficient"
    assert "retained_bundle" not in empty.continuous_learning_state
    contradictory = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="spectral-contradiction"), "Learn the spectral theorem today.")
    contradictory = consume_mission_bound_local_model_learning_approval(contradictory, model_executor=lambda *_: {"executed": True, "answer": "The spectral theorem [contradiction] contains incompatible claims.", "model_id": "local-test"})
    assert contradictory.continuous_learning_state["model_evidence"]["state"] == "contradictory"
    unavailable = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="spectral-unavailable"), "Learn the spectral theorem today.")
    unavailable = consume_mission_bound_local_model_learning_approval(unavailable, model_executor=lambda *_: {"executed": False, "reason": "no_local_model_available"})
    assert unavailable.continuous_mission_state == "learning_model_evidence_insufficient"
    assert unavailable.continuous_learning_state["local_model_execution_count"] == 1


def test_provisional_resource_reaches_existing_sealed_evaluator_before_narrow_update(monkeypatch, tmp_path):
    _lane_available(monkeypatch)
    controller = compile_mission_bound_local_model_learning_request(
        start_continuous_runtime_controller(session_id="spectral-evaluation"), "Learn the spectral theorem today."
    )
    ready = consume_mission_bound_local_model_learning_approval(
        controller, model_executor=_response, sealed_evaluation_cases=_sealed_cases()
    )
    assert ready.continuous_learning_state["evaluations"] == ()
    updated, result = execute_continuous_active_subgoal(ready, artifact_root=tmp_path, repository_root=tmp_path, python_executable="python")
    assert result.disposition == "behaviorally_demonstrated"
    assert result.validation["held_out"] == {"target": 1.0}
    assert result.validation["adversarial"] == {"target": 1.0}
    assert len(updated.continuous_learning_state["evaluations"]) == 1
    assert updated.continuous_learning_state["local_model_execution_count"] == 1
