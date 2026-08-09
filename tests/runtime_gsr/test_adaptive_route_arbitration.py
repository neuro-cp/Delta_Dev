import json
import os
import socket
import subprocess
import urllib.request

import pytest

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import (
    compile_adaptive_route_arbitration,
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
PHYSICS = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
CYBER = "A request parameter is appended into a SQL command before execution."
HEALTH = "I have an itchy rash for two days and I am worried it may be spreading. Should I seek care?"
LEGAL = "A collection agency says I owe a $1,200 balance. I dispute it and do not know which state rules apply."
GENERIC = "The billing system is failing after an update, but no error details or owner are available."


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


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


def _frame(source, scope="adaptive-arbitration"):
    compilation = compile_semantic_problem_frame(source, frame_scope_id=scope)
    assert compilation is not None
    return compilation.as_record()


def _arbitration(objective_id, *frames, corrections=()):
    result = compile_adaptive_route_arbitration(
        objective_id=objective_id,
        semantic_frames=frames,
        correction_candidates=corrections,
    )
    assert result is not None
    return result.as_record()


def _plan_ready_state(root, scenario, clarification):
    started = _send(start_or_restore_runtime(root), GOAL, root)
    framed = _send(started.state, scenario, root)
    refined = _send(framed.state, clarification, root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _completed_finance_loop(root):
    ready = _plan_ready_state(root, FINANCE, "Assume losing more than 10% over six months is unacceptable.")
    return _send(ready.state, "Yes, record this bounded plan.", root)


def test_blocked_operations_boundary_beats_eligible_finance_route():
    finance = _frame(FINANCE)
    operations = _frame(OPERATIONS)
    corrections = [
        item.as_record()
        for item in compile_long_horizon_self_correction_candidates(
            objective_id="ara-blocked-finance",
            semantic_frames=(finance, operations),
        )
    ]
    arbitration = _arbitration("ara-blocked-finance", finance, operations, corrections=corrections)

    route = operations["capability_route_candidate"]
    assert arbitration["decision"] == "blocked"
    assert arbitration["selected_route_id"] == route["capability_route_candidate_id"]
    assert "blocked safety boundary" in arbitration["priority_reason"].lower()
    assert arbitration["may_execute_now"] is False
    assert "external action" in " ".join(arbitration["forbidden_actions"]).lower()


def test_blocked_cyber_boundary_beats_eligible_physics_route_without_inspection():
    physics = _frame(PHYSICS)
    cyber = _frame(CYBER)
    corrections = [
        item.as_record()
        for item in compile_long_horizon_self_correction_candidates(
            objective_id="ara-blocked-cyber",
            semantic_frames=(physics, cyber),
        )
    ]
    arbitration = _arbitration("ara-blocked-cyber", physics, cyber, corrections=corrections)

    assert arbitration["decision"] == "blocked"
    assert arbitration["selected_route_id"] == cyber["capability_route_candidate"]["capability_route_candidate_id"]
    forbidden = " ".join(arbitration["forbidden_actions"]).lower()
    for phrase in ("payload", "repository read", "local file read", "scan"):
        assert phrase in forbidden


@pytest.mark.parametrize(
    ("safe_source", "forbidden_phrase"),
    (
        (HEALTH, "diagnosis certainty"),
        (LEGAL, "legal-advice certainty"),
    ),
)
def test_safe_clarification_beats_eligible_route_without_professional_overclaim(safe_source, forbidden_phrase):
    health = _frame(safe_source)
    finance = _frame(FINANCE)
    corrections = [
        item.as_record()
        for item in compile_long_horizon_self_correction_candidates(
            objective_id="ara-health-finance",
            semantic_frames=(health, finance),
        )
    ]
    arbitration = _arbitration("ara-health-finance", health, finance, corrections=corrections)

    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_route_id"] == health["capability_route_candidate"]["capability_route_candidate_id"]
    assert forbidden_phrase in " ".join(arbitration["forbidden_actions"]).lower()
    assert arbitration["may_execute_now"] is False


def test_eligible_routes_use_source_order_when_no_blocker_or_clarification_exists():
    finance = _frame(FINANCE)
    physics = _frame(PHYSICS)
    arbitration = _arbitration("ara-eligible", finance, physics)

    assert arbitration["decision"] == "eligible"
    assert arbitration["selected_route_id"] == finance["capability_route_candidate"]["capability_route_candidate_id"]
    assert arbitration["requires_existing_authority"] is True
    assert arbitration["may_execute_now"] is False
    assert arbitration["considered_route_ids"] == [
        finance["capability_route_candidate"]["capability_route_candidate_id"],
        physics["capability_route_candidate"]["capability_route_candidate_id"],
    ]


def test_completed_route_is_deprioritized_below_unresolved_blocked_route(tmp_path):
    completed = _completed_finance_loop(tmp_path)
    objective = completed.state.active_objective
    assert objective is not None
    finance_frames = _records(completed.state, "semantic_problem_frames")
    operations = _frame(OPERATIONS, scope=objective.objective_id)
    frames = (*finance_frames, operations)
    corrections = [
        item.as_record()
        for item in compile_long_horizon_self_correction_candidates(
            objective_id=objective.objective_id,
            semantic_frames=frames,
            analyses=_records(completed.state, "evidence_bound_analyses"),
            fixture_results=_records(completed.state, "evidence_minimal_fixture_results"),
        )
    ]
    arbitration = _arbitration(objective.objective_id, *frames, corrections=corrections)

    assert arbitration["decision"] == "blocked"
    assert arbitration["selected_route_id"] == operations["capability_route_candidate"]["capability_route_candidate_id"]
    assert len(_records(completed.state, "evidence_minimal_fixture_results")) == 1


def test_all_completed_routes_select_completed_without_new_work(tmp_path):
    completed = _completed_finance_loop(tmp_path)
    arbitration = completed.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "completed"
    assert arbitration["selected_route_id"] == ""
    assert arbitration["selected_correction_id"]
    assert arbitration["may_execute_now"] is False
    assert len(_records(completed.state, "evidence_minimal_fixture_results")) == 1


def test_ordinary_chat_has_no_frame_or_arbitration_side_effect(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    ordinary = _send(started.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert not _records(ordinary.state, "semantic_problem_frames")
    assert "adaptive_route_arbitration" not in ordinary.state.active_objective.provenance


def test_duplicate_replay_and_restart_preserve_one_persisted_arbitration(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    recorded = _send(started.state, GENERIC, tmp_path)
    expected = _canonical(recorded.state.active_objective.provenance["adaptive_route_arbitration"])
    replayed = _send(recorded.state, GENERIC, tmp_path)
    restored = start_or_restore_runtime(tmp_path)

    assert _canonical(replayed.state.active_objective.provenance["adaptive_route_arbitration"]) == expected
    assert _canonical(restored.active_objective.provenance["adaptive_route_arbitration"]) == expected
    assert len(_records(replayed.state, "semantic_problem_frames")) == 1


def test_arbitration_is_source_and_objective_local():
    first_frame = _frame(FINANCE, scope="ara-alpha")
    second_frame = _frame(FINANCE, scope="ara-beta")
    first = _arbitration("ara-alpha", first_frame)
    second = _arbitration("ara-beta", second_frame)

    assert first["objective_id"] != second["objective_id"]
    assert first["arbitration_id"] != second["arbitration_id"]
    assert first["selected_route_id"] != second["selected_route_id"]
    assert first["considered_route_ids"] == [first_frame["capability_route_candidate"]["capability_route_candidate_id"]]
    assert second["considered_route_ids"] == [second_frame["capability_route_candidate"]["capability_route_candidate_id"]]


def test_arbitration_projection_cannot_reach_graph_or_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    graph_before = _graph_snapshot(tmp_path)

    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, LEGAL, tmp_path)
    arbitration = result.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "clarify"
    assert arbitration["may_execute_now"] is False
    assert _graph_snapshot(tmp_path) == graph_before
