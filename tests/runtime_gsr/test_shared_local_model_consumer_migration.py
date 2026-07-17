from __future__ import annotations

from dataclasses import replace

from orchestration.runtime.continuous_runtime_controller import (
    compile_mission_bound_local_model_learning_request,
    consume_mission_bound_local_model_learning_approval,
    start_continuous_runtime_controller,
)
from orchestration.runtime.delta_1_4_live_wikipedia_runtime import handle_live_chat, start_live_wikipedia_runtime
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


LANE = {"lane": "reasoning_analysis", "available": True, "selected_model": "local-test", "selected_model_id": "local-test-1"}


def test_live_session_delegates_approval_and_only_keeps_reference(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    ledger = LocalModelRequestResultLedger()
    request = ledger.create_or_reuse_request(semantic_identity="live-request", question="Explain a bounded topic.", requester_type="live_conversation", session_reference="session", lane=LANE)
    session = replace(start_live_wikipedia_runtime(runtime_id="ledger-live"), pending_local_model_request={**request, "status": "PENDING_OPERATOR_APPROVAL"})
    calls: list[str] = []
    def execute(request_id: str, _context=None):
        calls.append(request_id)
        ledger.claim_execution(request_id)
        return ledger.complete_request(request_id, {"executed": True, "answer": "live answer", "model_id": "local-test-1"})
    monkeypatch.setattr(ledger, "execute_claimed_request", execute)
    # Use a second explicit stub rather than allowing a real model invocation.
    monkeypatch.setattr("orchestration.runtime.delta_1_4_live_wikipedia_runtime.LocalModelRequestResultLedger", lambda: ledger)
    updated, response = handle_live_chat(session, "ask the local model")
    assert calls == [request["request_id"]]
    assert updated.pending_local_model_request is None
    assert response.payload["operator_approval_request_id"] == request["request_id"]


def test_consumers_observe_one_completed_result_in_either_order(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr("orchestration.runtime.local_model_request_result_ledger.select_model_lane", lambda *_: LANE)
    controller = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="shared-observe"), "Learn the spectral theorem today.")
    request_id = controller.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    completed = ledger.execute_claimed_request(request_id, {"executor": lambda *_: {"executed": True, "answer": "shared answer", "model_id": "local-test-1"}})
    first = consume_mission_bound_local_model_learning_approval(controller)
    second = consume_mission_bound_local_model_learning_approval(first)
    assert first.continuous_learning_state["local_model_result_reference"]["result_id"] == completed["result_id"]
    assert second.continuous_learning_state["local_model_result_reference"]["response_digest"] == first.continuous_learning_state["local_model_result_reference"]["response_digest"]
    assert ledger.observe_request(request_id)["execution_attempt_count"] == 1


def test_live_session_and_learning_controller_observe_the_same_result(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr("orchestration.runtime.local_model_request_result_ledger.select_model_lane", lambda *_: LANE)
    controller = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="shared-live"), "Learn the spectral theorem today.")
    request = controller.continuous_learning_state["local_model_request"]
    ledger = LocalModelRequestResultLedger()
    session = replace(start_live_wikipedia_runtime(runtime_id="shared-live"), pending_local_model_request={**request, "status": "PENDING_OPERATOR_APPROVAL"})
    monkeypatch.setattr("orchestration.runtime.delta_1_4_live_wikipedia_runtime.LocalModelRequestResultLedger", lambda: ledger)
    def execute(request_id: str, _context=None):
        ledger.claim_execution(request_id)
        return ledger.complete_request(request_id, {"executed": True, "answer": "one shared answer", "model_id": "local-test-1"})
    monkeypatch.setattr(ledger, "execute_claimed_request", execute)
    _updated, response = handle_live_chat(session, "ask the local model")
    observed = consume_mission_bound_local_model_learning_approval(controller)
    assert response.payload["operator_approval_request_id"] == request["request_id"]
    assert response.payload["ledger_result_id"] == observed.continuous_learning_state["local_model_result_reference"]["result_id"]
    assert ledger.observe_request(request["request_id"])["execution_attempt_count"] == 1
