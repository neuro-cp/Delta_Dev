import json
import os
import socket
import subprocess
import urllib.request

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import compile_adaptive_precondition_selection
from orchestration.runtime.provisional_semantic_consolidation import load_graph


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement or calculable fixture need, ask one permission question about a later bounded evidence source. "
    "Do not gather evidence, inspect files, access a network, call a model or provider, use a tool, take external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
PHYSICS = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
HEALTH = "I have an itchy rash for two days and I am worried it may be spreading. Should I seek care?"
FINANCE_CORRECTION = "Correction: my account is 50% tech funds, 40% cash, and 10% small-cap value. The earlier 70% allocation was wrong, and I remain worried about AI stocks dropping over six months."


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _selection(state):
    objective = state.active_objective
    assert objective is not None
    selection = objective.provenance.get("adaptive_precondition_selection")
    assert isinstance(selection, dict)
    return selection


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
    return framed, refined, granted, accepted, authority


def test_selector_projects_existing_ladder_postures_and_never_executes(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    framed, refined, granted, accepted, authority = _plan_ready_state(tmp_path)

    assert _selection(framed.state)["precondition_state"] == "eligible_needs_permission"
    assert _selection(granted.state)["precondition_state"] == "permission_granted_needs_proposal_or_authority"
    assert _selection(authority.state)["precondition_state"] == "authority_exists_needs_plan_acceptance"
    assert _records(authority.state, "evidence_minimal_fixture_results") == ()

    completed = _send(authority.state, "Yes, record this bounded plan.", tmp_path)
    selection = _selection(completed.state)
    assert selection["precondition_state"] == "completed_stable"
    assert selection["may_execute_now"] is False
    assert "automatic authority" in " ".join(selection["forbidden_actions"]).lower()
    assert len(_records(completed.state, "evidence_minimal_fixture_results")) == 1
    assert _graph_snapshot(tmp_path) == graph_before


def test_accepted_plan_is_visible_as_nonexecuting_until_existing_path_advances(tmp_path):
    _framed, _refined, _granted, _accepted, authority = _plan_ready_state(tmp_path)
    objective = authority.state.active_objective
    assert objective is not None
    plan = dict(_records(authority.state, "evidence_fixture_execution_plans")[0])
    plan["status"] = "accepted_pending_execution_gate"
    selection = compile_adaptive_precondition_selection(
        objective_id=objective.objective_id,
        semantic_frames=_records(authority.state, "semantic_problem_frames"),
        evidence_requests=_records(authority.state, "evidence_requests"),
        evidence_authorizations=_records(authority.state, "evidence_authorizations"),
        evidence_next_operation_proposals=_records(authority.state, "evidence_next_operation_proposals"),
        evidence_execution_authorities=_records(authority.state, "evidence_execution_authorities"),
        evidence_fixture_execution_plans=(plan,),
        analyses=_records(authority.state, "evidence_bound_analyses"),
    )

    assert selection is not None
    record = selection.as_record()
    assert record["precondition_state"] == "accepted_plan_ready_nonexecuting"
    assert record["may_execute_now"] is False
    assert "does not invoke an evaluator" in record["selected_nonexecuting_posture"]


def test_blocked_clarify_and_stale_postures_outrank_eligible_work(tmp_path):
    blocked_start = _send(start_or_restore_runtime(tmp_path / "blocked"), GOAL, tmp_path / "blocked")
    blocked = _send(blocked_start.state, OPERATIONS, tmp_path / "blocked")
    assert _selection(blocked.state)["precondition_state"] == "blocked_safety_boundary"

    clarify_start = _send(start_or_restore_runtime(tmp_path / "clarify"), GOAL, tmp_path / "clarify")
    clarify = _send(clarify_start.state, HEALTH, tmp_path / "clarify")
    assert _selection(clarify.state)["precondition_state"] == "clarify_needed"

    _framed, _refined, _granted, _accepted, authority = _plan_ready_state(tmp_path / "stale")
    completed = _send(authority.state, "Yes, record this bounded plan.", tmp_path / "stale")
    corrected = _send(completed.state, FINANCE_CORRECTION, tmp_path / "stale")
    assert _selection(corrected.state)["precondition_state"] == "completed_stale_needs_new_authorized_cycle"
    assert len(_records(corrected.state, "evidence_minimal_fixture_results")) == 1


def test_selector_is_objective_local_restart_safe_and_ordinary_chat_is_unchanged(tmp_path):
    first = _send(
        _send(start_or_restore_runtime(tmp_path / "first"), GOAL, tmp_path / "first").state,
        PHYSICS,
        tmp_path / "first",
    )
    expected = _canonical(_selection(first.state))
    replayed = _send(first.state, PHYSICS, tmp_path / "first")
    restored = start_or_restore_runtime(tmp_path / "first")
    assert _canonical(_selection(replayed.state)) == expected
    assert _canonical(_selection(restored)) == expected
    assert len(_records(replayed.state, "semantic_problem_frames")) == 1

    ordinary_start = _send(start_or_restore_runtime(tmp_path / "ordinary"), GOAL, tmp_path / "ordinary")
    ordinary = _send(ordinary_start.state, "What is 2 + 2?", tmp_path / "ordinary")
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert "adaptive_precondition_selection" not in ordinary.state.active_objective.provenance


def test_selector_projection_cannot_reach_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, OPERATIONS, tmp_path)

    selection = _selection(result.state)
    assert selection["precondition_state"] == "blocked_safety_boundary"
    assert selection["may_execute_now"] is False
    assert "external action" in " ".join(selection["forbidden_actions"]).lower()
