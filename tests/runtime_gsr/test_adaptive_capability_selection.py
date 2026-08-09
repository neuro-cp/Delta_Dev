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
from orchestration.runtime.provisional_semantic_consolidation import load_graph
from orchestration.runtime.semantic_problem_modeling import compile_semantic_problem_frame


GOAL = (
    "Your new goal is to hold source-bound scenario analyses provisionally. "
    "Do not call a model, provider, tool, or take an external action. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
INCLINE = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."
EQUATION = "Explain F = ma as a model, including what it can solve for."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
CYBER = "A request parameter is appended into a SQL command before execution."
HEALTH = "I have an itchy rash for two days and I am worried it may be spreading. Should I seek care?"
LEGAL = "A collection agency says I owe a $1,200 balance. I dispute it and do not know which state rules apply."
GENERIC = "The billing system is failing after an update, but no error details or owner are available."


def _candidate(source, scope="adaptive-capability"):
    compilation = compile_semantic_problem_frame(source, frame_scope_id=scope)
    assert compilation is not None
    record = compilation.as_record()
    return record, record["capability_route_candidate"]


def _canonical(value):
    return json.loads(json.dumps(value, sort_keys=True))


@pytest.mark.parametrize(
    ("source", "route_name", "decision", "required_authority", "forbidden_text"),
    (
        (FINANCE, "finance_controlled_fixture", "eligible", True, "market lookup"),
        (INCLINE, "physics_deterministic_calculation", "eligible", True, "experimental measurement"),
        (EQUATION, "physics_deterministic_calculation", "clarify", True, "unsupported numeric calculation"),
        (OPERATIONS, "operations_blocked_external_dependency", "blocked", True, "customer"),
        (CYBER, "defensive_cyber_blocked_file_or_scan_boundary", "blocked", True, "payload"),
        (HEALTH, "health_info_safe_response", "clarify", False, "diagnosis certainty"),
        (LEGAL, "legal_financial_risk_safe_response", "clarify", False, "legal-advice certainty"),
        (GENERIC, "generic_structured_problem", "clarify", False, "specialist route"),
    ),
)
def test_semantic_frame_projects_one_deterministic_nonexecuting_capability_route(
    source,
    route_name,
    decision,
    required_authority,
    forbidden_text,
):
    record, candidate = _candidate(source)
    repeated_record, repeated = _candidate(source)
    frame = record["semantic_input_frame"]

    assert candidate == repeated
    assert candidate["capability_route_candidate_id"] == repeated_record["capability_route_candidate"]["capability_route_candidate_id"]
    assert candidate["record_kind"] == "semantic_frame_capability_route_candidate"
    assert candidate["source_frame_id"] == frame["frame_id"]
    assert candidate["source_text"] == frame["source_text"] == source
    assert candidate["source_span_refs"] == frame["source_spans"]
    assert candidate["route_name"] == route_name
    assert candidate["decision"] == decision
    assert bool(candidate["required_authority_if_any"]) is required_authority
    assert candidate["may_execute_now"] is False
    assert candidate["status"] == "deterministic_route_candidate_only"
    assert forbidden_text in " ".join(candidate["forbidden_actions"]).lower()
    assert "no automatic authority" in " ".join(candidate["forbidden_actions"]).lower()


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _graph_snapshot(root):
    graph = load_graph(root)
    return (
        tuple(graph.experiences),
        tuple(graph.claim_versions),
        tuple(graph.packets),
        tuple(graph.reviews),
        tuple(graph.admissions),
    )


@pytest.mark.parametrize(
    ("source", "route_name", "decision"),
    (
        (FINANCE, "finance_controlled_fixture", "eligible"),
        (INCLINE, "physics_deterministic_calculation", "eligible"),
        (OPERATIONS, "operations_blocked_external_dependency", "blocked"),
        (CYBER, "defensive_cyber_blocked_file_or_scan_boundary", "blocked"),
        (HEALTH, "health_info_safe_response", "clarify"),
        (LEGAL, "legal_financial_risk_safe_response", "clarify"),
        (GENERIC, "generic_structured_problem", "clarify"),
    ),
)
def test_runtime_persists_route_with_existing_frame_without_authority_or_execution(tmp_path, source, route_name, decision):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, source, tmp_path)

    objective = result.state.active_objective
    assert objective is not None
    frame = objective.provenance["semantic_problem_frames"][0]
    candidate = frame["capability_route_candidate"]
    assert candidate["route_name"] == route_name
    assert candidate["decision"] == decision
    assert candidate["source_frame_id"] == frame["frame_id"]
    assert candidate["may_execute_now"] is False
    assert not objective.provenance.get("evidence_execution_authorities", ())
    assert not objective.provenance.get("evidence_fixture_execution_plans", ())
    assert not objective.provenance.get("evidence_minimal_fixture_results", ())
    assert _graph_snapshot(tmp_path) == graph_before


def test_ordinary_chat_has_no_capability_route_side_effect_and_returns_four(tmp_path):
    assert compile_semantic_problem_frame("What is 2 + 2?", frame_scope_id="ordinary") is None
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    ordinary = _send(started.state, "What is 2 + 2?", tmp_path)

    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert ordinary.state.active_objective is not None
    assert not ordinary.state.active_objective.provenance.get("semantic_problem_frames", ())
    assert not ordinary.state.active_objective.provenance.get("evidence_execution_authorities", ())


def test_route_candidate_replay_and_restart_remain_exact_once(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    recorded = _send(started.state, GENERIC, tmp_path)
    frame = recorded.state.active_objective.provenance["semantic_problem_frames"][0]
    candidate = frame["capability_route_candidate"]

    replayed = _send(recorded.state, GENERIC, tmp_path)
    restored = start_or_restore_runtime(tmp_path)
    replayed_frame = replayed.state.active_objective.provenance["semantic_problem_frames"][0]
    restored_frame = restored.active_objective.provenance["semantic_problem_frames"][0]
    assert len(replayed.state.active_objective.provenance["semantic_problem_frames"]) == 1
    assert len(restored.active_objective.provenance["semantic_problem_frames"]) == 1
    assert _canonical(replayed_frame["capability_route_candidate"]) == _canonical(candidate)
    assert _canonical(restored_frame["capability_route_candidate"]) == _canonical(candidate)
    assert restored_frame["capability_route_candidate"]["capability_route_candidate_id"] == candidate["capability_route_candidate_id"]


def test_similar_objectives_keep_capability_routes_source_and_objective_isolated(tmp_path):
    first = _send(
        _send(start_or_restore_runtime(tmp_path / "first"), GOAL + " Use account alpha only.", tmp_path / "first").state,
        "Account alpha is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months.",
        tmp_path / "first",
    )
    second = _send(
        _send(start_or_restore_runtime(tmp_path / "second"), GOAL + " Use account beta only.", tmp_path / "second").state,
        "Account beta is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months.",
        tmp_path / "second",
    )
    first_objective = first.state.active_objective
    second_objective = second.state.active_objective
    assert first_objective is not None and second_objective is not None
    first_frame = first_objective.provenance["semantic_problem_frames"][0]
    second_frame = second_objective.provenance["semantic_problem_frames"][0]
    first_candidate = first_frame["capability_route_candidate"]
    second_candidate = second_frame["capability_route_candidate"]
    assert first_objective.objective_id != second_objective.objective_id
    assert first_candidate["source_frame_id"] == first_frame["frame_id"]
    assert second_candidate["source_frame_id"] == second_frame["frame_id"]
    assert first_candidate["capability_route_candidate_id"] != second_candidate["capability_route_candidate_id"]


def test_capability_route_projection_cannot_reach_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, CYBER, tmp_path)
    candidate = result.state.active_objective.provenance["semantic_problem_frames"][0]["capability_route_candidate"]
    assert candidate["decision"] == "blocked"
    assert candidate["may_execute_now"] is False
