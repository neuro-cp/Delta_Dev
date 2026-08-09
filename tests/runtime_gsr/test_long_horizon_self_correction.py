import json
import os
import socket
import subprocess
import urllib.request

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import (
    compile_long_horizon_self_correction_candidates,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph
from orchestration.runtime.semantic_problem_modeling import compile_semantic_problem_frame


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement or a calculable fixture need, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
PHYSICS_30 = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."
PHYSICS_45 = "Correction: the same 5 kg block slides down a frictionless 45-degree incline. I want the acceleration."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
CYBER = "A request parameter is appended into a SQL command before execution."
GENERIC_MISSING = "The billing system is failing after an update, but no error details or owner are available."
GENERIC_RESOLVED = "The billing system is failing after an update, but we now know the error is a database timeout and the platform team owns it."


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _corrections(state):
    return _records(state, "long_horizon_self_correction_candidates")


def _candidate(state, correction_type):
    values = [item for item in _corrections(state) if item.get("correction_type") == correction_type]
    assert len(values) == 1
    return values[0]


def _canonical(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _graph_snapshot(root):
    graph = load_graph(root)
    return (
        tuple(graph.experiences),
        tuple(graph.claim_versions),
        tuple(graph.packets),
        tuple(graph.reviews),
        tuple(graph.admissions),
    )


def _plan_ready_state(root):
    started = _send(start_or_restore_runtime(root), GOAL, root)
    framed = _send(started.state, FINANCE, root)
    refined = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def test_resolved_missing_context_is_persisted_as_nonexecuting_objective_local_correction(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    missing = _send(started.state, GENERIC_MISSING, tmp_path)
    resolved = _send(missing.state, GENERIC_RESOLVED, tmp_path)

    correction = _candidate(resolved.state, "resolved_missing_context")
    frames = _records(resolved.state, "semantic_problem_frames")
    assert len(frames) == 2
    assert correction["source_frame_ids"] == [frames[0]["frame_id"], frames[1]["frame_id"]]
    assert correction["may_route_next"] is True
    assert correction["may_execute_now"] is False
    assert "not promoted as truth" in correction["corrected_or_current_state"]
    assert _graph_snapshot(tmp_path) == graph_before


def test_malformed_accepted_finance_input_derives_a_fail_closed_correction_without_fallback(tmp_path):
    ready = _plan_ready_state(tmp_path)
    objective = ready.state.active_objective
    assert objective is not None
    plan = dict(_records(ready.state, "evidence_fixture_execution_plans")[0])
    analysis = dict(_records(ready.state, "evidence_bound_analyses")[0])
    malformed_plan = {
        **plan,
        "status": "accepted_pending_execution_gate",
        "may_execute_now": False,
        "execution_requires_future_gate": True,
    }
    malformed_analysis = {**analysis, "source_text": "My account is 70% aggressive tech funds and cash is variable."}

    corrections = compile_long_horizon_self_correction_candidates(
        objective_id=objective.objective_id,
        semantic_frames=_records(ready.state, "semantic_problem_frames"),
        analyses=(analysis,),
        rejected_fixture_inputs=((malformed_plan, malformed_analysis),),
    )
    rejected = [item.as_record() for item in corrections if item.correction_type == "malformed_to_fail_closed"]
    assert len(rejected) == 1
    correction = rejected[0]
    assert correction["may_execute_now"] is False
    assert "no fixture result" in correction["corrected_or_current_state"]
    assert "fallback data" in " ".join(correction["forbidden_actions"]).lower()
    assert not _records(ready.state, "evidence_minimal_fixture_results")
    assert not [item for item in _records(ready.state, "analysis_refinements") if item.get("status") == "controlled_fixture_refinement"]


def test_blocked_operations_and_defensive_cyber_routes_remain_nonexecuting_corrections(tmp_path):
    for label, source in (("operations", OPERATIONS), ("cyber", CYBER)):
        started = _send(start_or_restore_runtime(tmp_path / label), GOAL, tmp_path / label)
        result = _send(started.state, source, tmp_path / label)
        correction = _candidate(result.state, "blocked_external_boundary")
        forbidden = " ".join(correction["forbidden_actions"]).lower()
        assert correction["may_execute_now"] is False
        assert correction["may_route_next"] is False
        assert "external action" in forbidden
        if label == "operations":
            assert "customer" in forbidden
        else:
            assert "payload" in forbidden and "repository read" in forbidden


def test_conflicting_physics_frames_mark_only_the_prior_assumption_as_superseded():
    first = compile_semantic_problem_frame(PHYSICS_30, frame_scope_id="physics-supersession")
    second = compile_semantic_problem_frame(PHYSICS_45, frame_scope_id="physics-supersession")
    assert first is not None and second is not None
    first_record = first.as_record()
    second_record = second.as_record()

    corrections = compile_long_horizon_self_correction_candidates(
        objective_id="physics-supersession-objective",
        semantic_frames=(first_record, second_record),
    )
    superseded = [item.as_record() for item in corrections if item.correction_type == "contradiction_or_supersession"]
    assert len(superseded) == 1
    correction = superseded[0]
    assert correction["source_frame_ids"] == [first_record["frame_id"], second_record["frame_id"]]
    assert "30 degrees" in correction["prior_state"]
    assert "45 degrees" in correction["corrected_or_current_state"]
    assert correction["may_execute_now"] is False
    assert "do not recompute automatically" in correction["recommended_nonexecuting_posture"]


def test_completed_positive_loop_records_stable_nonrepeating_correction_posture(tmp_path):
    ready = _plan_ready_state(tmp_path)
    completed = _send(ready.state, "Yes, record this bounded plan.", tmp_path)

    correction = _candidate(completed.state, "completed_positive_loop")
    results = _records(completed.state, "evidence_minimal_fixture_results")
    assert len(results) == 1
    assert correction["source_result_ids"] == [results[0]["evidence_minimal_fixture_result_id"]]
    assert correction["may_execute_now"] is False
    assert correction["may_route_next"] is False
    assert "Do not repeat" in correction["recommended_nonexecuting_posture"]


def test_correction_replay_restart_and_objective_isolation_are_exact_once(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path / "first"), GOAL, tmp_path / "first")
    missing = _send(started.state, GENERIC_MISSING, tmp_path / "first")
    resolved = _send(missing.state, GENERIC_RESOLVED, tmp_path / "first")
    expected = _canonical(_corrections(resolved.state))

    replayed = _send(resolved.state, GENERIC_RESOLVED, tmp_path / "first")
    restored = start_or_restore_runtime(tmp_path / "first")
    assert _canonical(_corrections(replayed.state)) == expected
    assert _canonical(_corrections(restored)) == expected

    other_started = _send(start_or_restore_runtime(tmp_path / "second"), GOAL + " Use a separate source only.", tmp_path / "second")
    other = _send(other_started.state, GENERIC_MISSING, tmp_path / "second")
    first_correction = _candidate(resolved.state, "resolved_missing_context")
    other_correction = _candidate(other.state, "unsupported_to_clarify")
    assert first_correction["objective_id"] != other_correction["objective_id"]
    assert set(first_correction["source_frame_ids"]).isdisjoint(set(other_correction["source_frame_ids"]))


def test_ordinary_chat_has_no_long_horizon_correction_side_effect_and_returns_four(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    ordinary = _send(started.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert not _corrections(ordinary.state)


def test_self_correction_projection_cannot_reach_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, OPERATIONS, tmp_path)
    correction = _candidate(result.state, "blocked_external_boundary")
    assert correction["may_execute_now"] is False
