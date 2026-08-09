import json
import os
import socket
import subprocess
import urllib.request

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement or a calculable fixture need, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE_70 = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
FINANCE_50 = "Correction: my account is 50% tech funds, 40% cash, and 10% small-cap value. The earlier 70% allocation was wrong, and I remain worried about AI stocks dropping over six months."
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


def _one_record(state, key):
    records = _records(state, key)
    assert len(records) == 1
    return records[0]


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


def _plan_ready_state(root, scenario, clarification, goal=GOAL):
    started = _send(start_or_restore_runtime(root), goal, root)
    framed = _send(started.state, scenario, root)
    refined = _send(framed.state, clarification, root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _completed_loop(root, scenario, clarification, goal=GOAL):
    ready = _plan_ready_state(root, scenario, clarification, goal=goal)
    return _send(ready.state, "Yes, record this bounded plan.", root)


def _effect(state, effect_type):
    matches = [record for record in _records(state, "long_horizon_correction_effects") if record.get("effect_type") == effect_type]
    assert len(matches) == 1
    return matches[0]


def _assert_no_duplicate_completion(before, after):
    for key in ("evidence_minimal_fixture_results", "analysis_refinements", "internal_work_selections"):
        assert _records(after, key) == _records(before, key)


def test_physics_supersession_suppresses_prior_completed_lineage_without_recomputation(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    completed = _completed_loop(tmp_path, PHYSICS_30, "A numeric result is most useful.")
    prior_frame = _one_record(completed.state, "semantic_problem_frames")
    prior_result = _one_record(completed.state, "evidence_minimal_fixture_results")
    prior_refinement = next(
        record for record in _records(completed.state, "analysis_refinements") if record.get("status") == "controlled_fixture_refinement"
    )
    corrected = _send(completed.state, PHYSICS_45, tmp_path)

    effect = _effect(corrected.state, "stale_suppression")
    arbitration = corrected.state.active_objective.provenance["adaptive_route_arbitration"]
    assert prior_frame["frame_id"] in effect["affected_frame_ids"]
    assert prior_result["evidence_minimal_fixture_result_id"] in effect["affected_result_ids"]
    assert prior_refinement["refinement_id"] in effect["affected_refinement_ids"]
    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_correction_effect_id"] == effect["effect_id"]
    assert arbitration["may_execute_now"] is False
    _assert_no_duplicate_completion(completed.state, corrected.state)
    assert _graph_snapshot(tmp_path) == graph_before


def test_finance_supersession_suppresses_prior_completed_lineage_without_inferred_weights(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    completed = _completed_loop(tmp_path, FINANCE_70, "Assume losing more than 10% over six months is unacceptable.")
    prior_result = _one_record(completed.state, "evidence_minimal_fixture_results")
    corrected = _send(completed.state, FINANCE_50, tmp_path)

    effect = _effect(corrected.state, "stale_suppression")
    arbitration = corrected.state.active_objective.provenance["adaptive_route_arbitration"]
    assert prior_result["evidence_minimal_fixture_result_id"] in effect["affected_result_ids"]
    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_correction_effect_id"] == effect["effect_id"]
    assert "infer replacement weights" in effect["selected_nonexecuting_posture"].lower()
    _assert_no_duplicate_completion(completed.state, corrected.state)
    assert _graph_snapshot(tmp_path) == graph_before


def test_resolved_context_selects_a_nonexecuting_correction_aware_posture(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    missing = _send(started.state, GENERIC_MISSING, tmp_path)
    resolved = _send(missing.state, GENERIC_RESOLVED, tmp_path)

    effect = _effect(resolved.state, "resolved_context")
    arbitration = resolved.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_correction_effect_id"] == effect["effect_id"]
    assert effect["may_execute_now"] is False
    assert not _records(resolved.state, "evidence_minimal_fixture_results")
    assert not resolved.state.pending_chat_requests
    assert _graph_snapshot(tmp_path) == graph_before


def test_blocked_boundary_effect_persists_after_unrelated_context(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    blocked = _send(started.state, OPERATIONS, tmp_path)
    after_context = _send(blocked.state, "Thanks, I will provide no additional invoice or pump status today.", tmp_path)

    effect = _effect(after_context.state, "blocked_persists")
    arbitration = after_context.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "blocked"
    assert effect["may_execute_now"] is False
    assert "blocked safety boundary" in effect["selected_nonexecuting_posture"].lower()
    assert not _records(after_context.state, "evidence_minimal_fixture_results")
    assert _graph_snapshot(tmp_path) == graph_before


def test_stable_completion_remains_stable_without_later_correction(tmp_path):
    completed = _completed_loop(tmp_path, FINANCE_70, "Assume losing more than 10% over six months is unacceptable.")
    effect = _effect(completed.state, "stable_completed")
    arbitration = completed.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "completed"
    assert effect["may_execute_now"] is False
    assert len(_records(completed.state, "evidence_minimal_fixture_results")) == 1


def test_correction_effect_replay_and_restart_are_exact_once(tmp_path):
    completed = _completed_loop(tmp_path, PHYSICS_30, "A numeric result is most useful.")
    corrected = _send(completed.state, PHYSICS_45, tmp_path)
    expected_effects = _canonical(_records(corrected.state, "long_horizon_correction_effects"))
    expected_arbitration = _canonical(corrected.state.active_objective.provenance["adaptive_route_arbitration"])
    replayed = _send(corrected.state, PHYSICS_45, tmp_path)
    restored = start_or_restore_runtime(tmp_path)

    assert _canonical(_records(replayed.state, "long_horizon_correction_effects")) == expected_effects
    assert _canonical(restored.active_objective.provenance["long_horizon_correction_effects"]) == expected_effects
    assert _canonical(replayed.state.active_objective.provenance["adaptive_route_arbitration"]) == expected_arbitration
    assert _canonical(restored.active_objective.provenance["adaptive_route_arbitration"]) == expected_arbitration


def test_correction_effects_are_objective_local(tmp_path):
    first = _completed_loop(tmp_path / "first", PHYSICS_30, "A numeric result is most useful.")
    first_corrected = _send(first.state, PHYSICS_45, tmp_path / "first")
    second = _completed_loop(
        tmp_path / "second",
        FINANCE_70,
        "Assume losing more than 10% over six months is unacceptable.",
        goal=GOAL + " Use the finance scenario only.",
    )
    first_effect = _effect(first_corrected.state, "stale_suppression")
    second_effect = _effect(second.state, "stable_completed")

    assert first_effect["objective_id"] != second_effect["objective_id"]
    assert first_effect["effect_id"] != second_effect["effect_id"]
    assert set(first_effect["affected_result_ids"]).isdisjoint(set(second_effect["affected_result_ids"]))


def test_ordinary_chat_has_no_correction_effect(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    ordinary = _send(started.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert not _records(ordinary.state, "long_horizon_correction_effects")
    assert "adaptive_route_arbitration" not in ordinary.state.active_objective.provenance


def test_correction_effect_projection_cannot_reach_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    blocked = _send(started.state, CYBER, tmp_path)
    effect = _effect(blocked.state, "blocked_persists")
    assert effect["may_execute_now"] is False
