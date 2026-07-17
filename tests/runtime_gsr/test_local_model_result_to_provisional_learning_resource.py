from __future__ import annotations

from orchestration.runtime.continuous_runtime_controller import (
    compile_mission_bound_local_model_learning_request,
    consume_mission_bound_local_model_learning_approval,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)
from orchestration.runtime.developmental_learning import (
    compile_developmental_mission_contract,
    compile_mission_bound_advisory_learning_evidence,
    compile_mission_information_need,
    compile_provisional_learning_bundle_from_advisory,
)
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


GOOD_RESPONSE = """Spectral theorem statement: this is a bounded theorem statement.
Prerequisites include linear algebra and eigenvalues. Intuition means diagonal directions simplify analysis.
Example: consider a symmetric matrix. A common misconception is that every matrix qualifies, but the theorem does not apply to every matrix.
Practice question: identify a valid application. There is uncertainty about scope limits."""


def _mission_and_records(response: str = GOOD_RESPONSE):
    mission = compile_developmental_mission_contract("Learn the spectral theorem today.")
    assert mission is not None
    need = compile_mission_information_need(mission)
    request = {"request_id": "request-a", "request_digest": "request-digest", "model_identity": "local-model", "adapter_identity": "adapter"}
    result = {"result_id": "result-a", "response_digest": "response-digest", "response_reference": response, "model_identity": "local-model", "adapter_identity": "adapter", "provenance": {"execution_claim_id": "claim-a"}}
    return mission, need, request, result


def test_normalization_preserves_scope_tension_and_builds_narrow_provisional_bundle():
    mission, need, request, result = _mission_and_records()
    evidence = compile_mission_bound_advisory_learning_evidence(mission, need, request, result)
    assert evidence.sufficiency_state == "partially_sufficient"
    assert "unresolved_scope_tension" in evidence.contradictions
    assert evidence.raw_response_reference == "result-a"
    assert evidence.prerequisite_candidates and evidence.suggested_practice
    bundle = compile_provisional_learning_bundle_from_advisory(mission, evidence)
    assert bundle is not None
    assert bundle["resource_status"] == "provisional"
    assert bundle["shared_result_id"] == "result-a"
    assert not bundle["sealed_evaluation_cases"]


def test_empty_irrelevant_and_malformed_responses_do_not_create_resources():
    mission, need, request, result = _mission_and_records("")
    empty = compile_mission_bound_advisory_learning_evidence(mission, need, request, result)
    assert empty.sufficiency_state == "empty"
    assert compile_provisional_learning_bundle_from_advisory(mission, empty) is None
    _mission, _need, _request, irrelevant_result = _mission_and_records("A cooking recipe with no mathematical topic.")
    irrelevant = compile_mission_bound_advisory_learning_evidence(mission, need, request, irrelevant_result)
    assert irrelevant.sufficiency_state == "irrelevant"
    assert compile_provisional_learning_bundle_from_advisory(mission, irrelevant) is None
    _mission, _need, _request, malformed_result = _mission_and_records("@@@@")
    malformed = compile_mission_bound_advisory_learning_evidence(mission, need, request, malformed_result)
    assert malformed.sufficiency_state in {"irrelevant", "insufficient"}
    assert compile_provisional_learning_bundle_from_advisory(mission, malformed) is None


def test_partial_response_creates_follow_up_need_without_fabricating_sections():
    mission, need, request, result = _mission_and_records("The spectral theorem is a topic. Prerequisites include eigenvalues. Practice question: identify a use.")
    evidence = compile_mission_bound_advisory_learning_evidence(mission, need, request, result)
    assert evidence.sufficiency_state == "partially_sufficient"
    assert evidence.missing_sections
    assert evidence.follow_up_information_needs
    bundle = compile_provisional_learning_bundle_from_advisory(mission, evidence)
    assert bundle is not None
    assert "worked_example" not in tuple(bundle["assessment_dimensions"][0]["required_components"])


def test_controller_handoff_reuses_completed_ledger_result_without_capability_update(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr("orchestration.runtime.local_model_request_result_ledger.select_model_lane", lambda *_: {"available": True, "lane": "reasoning", "selected_model_id": "test-model"})
    controller = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="resource-handoff"), "Learn the spectral theorem today.")
    request_id = controller.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    ledger.execute_claimed_request(request_id, {"executor": lambda *_: {"executed": True, "answer": GOOD_RESPONSE, "model_id": "test-model"}})
    before_inventory = controller.continuous_capability_inventory
    updated = consume_mission_bound_local_model_learning_approval(controller)
    state = updated.continuous_learning_state
    assert state["local_model_execution_count"] == 1
    assert state["mission_bound_advisory_evidence"]["shared_request_id"] == request_id
    assert state["provisional_resource_bundle"]["resource_status"] == "provisional"
    assert updated.continuous_active_subgoal
    assert updated.continuous_capability_inventory == before_inventory
    assert not state["evaluations"] and not state["attempts"]


def test_equivalent_observation_and_restart_do_not_duplicate_resource_or_model_call(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr("orchestration.runtime.local_model_request_result_ledger.select_model_lane", lambda *_: {"available": True, "lane": "reasoning", "selected_model_id": "test-model"})
    controller = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="resource-restart"), "Learn the spectral theorem today.")
    request_id = controller.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    ledger.execute_claimed_request(request_id, {"executor": lambda *_: {"executed": True, "answer": GOOD_RESPONSE, "model_id": "test-model"}})
    first = consume_mission_bound_local_model_learning_approval(controller)
    second = consume_mission_bound_local_model_learning_approval(first)
    assert second.continuous_learning_state["provisional_resource_bundle"]["resource_bundle_id"] == first.continuous_learning_state["provisional_resource_bundle"]["resource_bundle_id"]
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="resource-restart"), export_continuous_mission_restart_state(first))
    replay = consume_mission_bound_local_model_learning_approval(restored)
    assert replay.continuous_learning_state["mission_bound_advisory_evidence"]["evidence_id"] == first.continuous_learning_state["mission_bound_advisory_evidence"]["evidence_id"]
    assert ledger.observe_request(request_id)["execution_attempt_count"] == 1


def test_equivalent_mission_reuses_completed_result_without_creating_or_executing_request(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr("orchestration.runtime.local_model_request_result_ledger.select_model_lane", lambda *_: {"available": True, "lane": "reasoning", "selected_model_id": "test-model"})
    first = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="resource-original"), "Learn the spectral theorem today.")
    request_id = first.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    ledger.execute_claimed_request(request_id, {"executor": lambda *_: {"executed": True, "answer": GOOD_RESPONSE, "model_id": "test-model"}})
    replay = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="resource-replay"), "Learn the spectral theorem today.")
    assert replay.continuous_learning_state["local_model_request"]["request_id"] == request_id
    assert replay.continuous_learning_state["provisional_resource_bundle"]
    assert ledger.observe_request(request_id)["execution_attempt_count"] == 1


def test_same_learning_need_reuses_completed_result_across_timestamped_mission_ids(monkeypatch, tmp_path):
    monkeypatch.setenv("DELTA_LOCAL_MODEL_LEDGER_ROOT", str(tmp_path / "ledger"))
    monkeypatch.setattr("orchestration.runtime.local_model_request_result_ledger.select_model_lane", lambda *_: {"available": True, "lane": "reasoning", "selected_model_id": "test-model"})
    first = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="resource-original"), "Learn the spectral theorem today.")
    request_id = first.continuous_learning_state["local_model_request"]["request_id"]
    ledger = LocalModelRequestResultLedger()
    ledger.approve_request(request_id, "operator")
    ledger.execute_claimed_request(request_id, {"executor": lambda *_: {"executed": True, "answer": GOOD_RESPONSE, "model_id": "test-model"}})
    monkeypatch.setattr("orchestration.runtime.developmental_learning.utc_now", lambda: "2040-01-01T00:00:00+00:00")
    replay = compile_mission_bound_local_model_learning_request(start_continuous_runtime_controller(session_id="resource-new-run"), "Learn the spectral theorem today.")
    assert replay.continuous_learning_state["local_model_request"]["request_id"] == request_id
    assert replay.continuous_learning_state["provisional_resource_bundle"]
    assert ledger.observe_request(request_id)["execution_attempt_count"] == 1
