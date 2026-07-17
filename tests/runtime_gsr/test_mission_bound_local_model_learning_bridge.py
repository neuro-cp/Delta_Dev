from __future__ import annotations

from orchestration.runtime.continuous_runtime_controller import (
    compile_mission_bound_local_model_learning_request,
    consume_mission_bound_local_model_learning_approval,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_learning import classify_developmental_instruction
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


def _lane_available(monkeypatch):
    monkeypatch.setattr(
        "orchestration.runtime.local_model_request_result_ledger.select_model_lane",
        lambda _message, _intent: {"lane": "reasoning_analysis", "available": True, "selected_model": "local-test", "selected_model_id": "local-test-1"},
    )


def _response(_message, _lane):
    return {"executed": True, "model_id": "local-test-1", "execution_adapter": "controlled_rc2_fixture", "answer": "bounded advisory answer"}


def test_mission_request_is_a_ledger_reference_and_reuses_without_execution(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    _lane_available(monkeypatch)
    controller = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="spectral-pending"), "Learn the spectral theorem today.")
    assert classify_developmental_instruction("Learn the spectral theorem today.")["topic"] == "spectral_theorem"
    request = controller.continuous_learning_state["local_model_request"]
    assert request["lifecycle_state"] == "pending_operator_approval"
    replay = compile_mission_bound_local_model_learning_request(controller, "Learn the spectral theorem today.")
    assert replay.continuous_learning_state["local_model_request"]["request_id"] == request["request_id"]
    assert LocalModelRequestResultLedger().observe_request(request["request_id"])["execution_attempt_count"] == 0


def test_distinct_missions_do_not_reuse_each_others_request(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    _lane_available(monkeypatch)
    first = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="mission-one"), "Learn the spectral theorem today.")
    second = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="mission-two"), "Learn the spectral theorem today.")
    assert first.continuous_learning_state["local_model_request"]["request_id"] != second.continuous_learning_state["local_model_request"]["request_id"]


def test_controller_only_observes_terminal_result_without_curriculum_or_capability(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    _lane_available(monkeypatch)
    controller = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="spectral-complete"), "Learn the spectral theorem today.")
    request_id = controller.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator_approved_one_use")
    completed = ledger.execute_claimed_request(request_id, {"executor": _response})
    observed = consume_mission_bound_local_model_learning_approval(controller, model_executor=lambda *_: (_ for _ in ()).throw(AssertionError("controller must not execute")))
    state = observed.continuous_learning_state
    assert state["local_model_request"]["request_id"] == request_id
    assert state["local_model_result_reference"]["result_id"] == completed["result_id"]
    assert state["local_model_execution_count"] == 1
    assert "evaluations" not in state and "retained_bundle" not in state
    assert not observed.continuous_active_subgoal


def test_controller_restart_observes_same_ledger_result_once(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    _lane_available(monkeypatch)
    controller = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="spectral-restart"), "Learn the spectral theorem today.")
    request_id = controller.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    ledger.execute_claimed_request(request_id, {"executor": _response})
    observed = consume_mission_bound_local_model_learning_approval(controller)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="spectral-restart"), export_continuous_mission_restart_state(observed))
    replay = consume_mission_bound_local_model_learning_approval(restored)
    assert replay.continuous_learning_state["local_model_result_reference"]["result_id"] == observed.continuous_learning_state["local_model_result_reference"]["result_id"]
    assert LocalModelRequestResultLedger().observe_request(request_id)["execution_attempt_count"] == 1
