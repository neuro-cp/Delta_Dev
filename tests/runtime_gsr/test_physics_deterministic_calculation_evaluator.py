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
from orchestration.runtime.evidence_bound_analysis import compile_evidence_minimal_fixture_results
from orchestration.runtime.provisional_semantic_consolidation import load_graph


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement or a calculable fixture need, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
PHYSICS = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _record(state, key):
    records = _records(state, key)
    assert len(records) == 1
    return records[0]


def _canonical(records):
    return json.loads(json.dumps(records, sort_keys=True))


def _graph_snapshot(root):
    graph = load_graph(root)
    return (
        tuple(graph.experiences),
        tuple(graph.claim_versions),
        tuple(graph.packets),
        tuple(graph.reviews),
        tuple(graph.admissions),
    )


def _physics_plan_ready_state(root):
    state = start_or_restore_runtime(root)
    started = _send(state, GOAL, root)
    framed = _send(started.state, PHYSICS, root)
    refined = _send(framed.state, "A numeric result is most useful.", root)
    assert refined.state.pending_chat_requests[0].request_type == "evidence_permission"
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    assert granted.state.pending_chat_requests[0].request_type == "evidence_next_operation_proposal"
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    assert accepted.state.pending_chat_requests[0].request_type == "evidence_execution_authority"
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _physics_closed_loop_state(root):
    ready = _physics_plan_ready_state(root)
    return _send(ready.state, "Yes, record this bounded plan.", root)


def _accepted_looking_plan(state):
    plan = _record(state, "evidence_fixture_execution_plans")
    return {
        **dict(plan),
        "status": "accepted_pending_execution_gate",
        "may_execute_now": False,
        "execution_requires_future_gate": True,
    }


def _controlled_refinement(state):
    records = [item for item in _records(state, "analysis_refinements") if item.get("status") == "controlled_fixture_refinement"]
    assert len(records) == 1
    return records[0]


def _controlled_selection(state, refinement):
    records = [
        item
        for item in _records(state, "internal_work_selections")
        if item.get("source_refinement_id") == refinement["refinement_id"]
        and item.get("source_evidence_minimal_fixture_result_id") == refinement["source_evidence_minimal_fixture_result_id"]
        and item.get("status") == "selected_record_only"
    ]
    assert len(records) == 1
    return records[0]


def _assert_no_positive_completion(state, root, graph_before):
    assert not _records(state, "evidence_minimal_fixture_results")
    assert not [item for item in _records(state, "analysis_refinements") if item.get("status") == "controlled_fixture_refinement"]
    assert not [item for item in _records(state, "internal_work_candidates") if item.get("controlled_fixture_problem_state_update_id")]
    assert not [
        item
        for item in _records(state, "internal_work_selections")
        if item.get("source_evidence_minimal_fixture_result_id") or item.get("controlled_fixture_problem_state_update_id")
    ]
    assert _graph_snapshot(root) == graph_before


def test_positive_physics_completion_uses_existing_controlled_loop(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    result = _physics_closed_loop_state(tmp_path)

    plan = _record(result.state, "evidence_fixture_execution_plans")
    dry_run = _record(result.state, "evidence_fixture_dry_run_results")
    ingestion = _record(result.state, "evidence_result_ingestion_candidates")
    revision = _record(result.state, "evidence_analysis_revision_candidates")
    fixture = _record(result.state, "evidence_minimal_fixture_results")
    refinement = _controlled_refinement(result.state)
    selection = _controlled_selection(result.state, refinement)
    routed = next(
        item
        for item in _records(result.state, "internal_work_candidates")
        if item.get("internal_work_candidate_id") == fixture["source_internal_work_candidate_id"]
    )

    assert plan["proposed_operation_type"] == "physics_frictionless_incline_calculation_proposal_only"
    assert dry_run["fixture_kind"] == "synthetic_physics_incline_calculation_ready"
    assert fixture["fixture_kind"] == "in_memory_frictionless_thirty_degree_incline_calculation"
    assert "4.9 m/s^2" in fixture["deterministic_output"]
    assert fixture["source_plan_id"] == plan["evidence_fixture_execution_plan_id"]
    assert ingestion["source_dry_run_result_id"] == dry_run["evidence_fixture_dry_run_result_id"]
    assert revision["source_ingestion_candidate_id"] == ingestion["evidence_result_ingestion_candidate_id"]
    assert routed["source_evidence_analysis_revision_candidate_id"] == revision["evidence_analysis_revision_candidate_id"]
    assert refinement["source_evidence_minimal_fixture_result_id"] == fixture["evidence_minimal_fixture_result_id"]
    assert refinement["changed_unknown_slots"] == ("physics.frictionless_thirty_degree_calculation",)
    assert routed["problem_state_status"] == "fixture_refined_frictionless_incline_calculation_recorded"
    assert selection["selected_next_operation"] == "retain_frictionless_incline_calculation_and_wait_for_later_authority"
    assert selection["may_execute_now"] is False
    assert _graph_snapshot(tmp_path) == graph_before


@pytest.mark.parametrize(
    "label,source_text",
    (
        ("missing_angle", "A 5 kg block slides down a frictionless incline."),
        ("nonnumeric_angle", "A 5 kg block slides down a frictionless steep incline."),
        ("friction_present", "A 5 kg block slides down a frictionless 30-degree incline with friction from a rough surface."),
    ),
)
def test_negative_physics_inputs_fail_closed_after_accepted_looking_plan(tmp_path, label, source_text):
    ready = _physics_plan_ready_state(tmp_path / label)
    state = ready.state
    objective = state.active_objective
    assert objective is not None
    graph_before = _graph_snapshot(tmp_path / label)
    analysis = _record(state, "evidence_bound_analyses")
    malformed_analysis = {**dict(analysis), "source_text": source_text}

    assert compile_evidence_minimal_fixture_results(
        _accepted_looking_plan(state),
        objective_id=objective.objective_id,
        source_analysis=malformed_analysis,
    ) == ()
    _assert_no_positive_completion(state, tmp_path / label, graph_before)


def test_mismatched_physics_lineage_fails_closed_after_accepted_looking_plan(tmp_path):
    ready = _physics_plan_ready_state(tmp_path)
    state = ready.state
    objective = state.active_objective
    assert objective is not None
    graph_before = _graph_snapshot(tmp_path)
    analysis = _record(state, "evidence_bound_analyses")
    mismatched_analysis = {**dict(analysis), "analysis_id": "unrelated-physics-analysis"}
    revision_bound_to_original = {
        "evidence_analysis_revision_candidate_id": "revision-bound-to-original-physics-analysis",
        "source_analysis_id": analysis["analysis_id"],
    }

    assert compile_evidence_minimal_fixture_results(
        _accepted_looking_plan(state),
        objective_id=objective.objective_id,
        source_analysis=mismatched_analysis,
        source_revision_candidate=revision_bound_to_original,
    ) == ()
    _assert_no_positive_completion(state, tmp_path, graph_before)


def test_physics_duplicate_restart_and_ordinary_chat_are_exactly_once(tmp_path):
    completed = _physics_closed_loop_state(tmp_path)
    keys = (
        "evidence_fixture_execution_plans",
        "evidence_minimal_fixture_results",
        "analysis_refinements",
        "internal_work_selections",
    )
    expected = {key: _canonical(_records(completed.state, key)) for key in keys}

    restored = start_or_restore_runtime(tmp_path)
    assert {key: _canonical(_records(restored, key)) for key in keys} == expected
    duplicate = _send(restored, "Yes, record this bounded plan.", tmp_path)
    assert duplicate.intent.intent_type == "ordinary_conversation"
    assert {key: _canonical(_records(duplicate.state, key)) for key in keys} == expected
    ordinary = _send(duplicate.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert {key: _canonical(_records(ordinary.state, key)) for key in keys} == expected


def test_physics_boundary_uses_no_external_side_effect(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    result = _physics_closed_loop_state(tmp_path)
    fixture = _record(result.state, "evidence_minimal_fixture_results")
    blocked = " ".join(fixture["blocked_actions"]).lower()
    for label in ("repository file read", "local filesystem read", "network", "model", "provider", "tool", "sandbox", "graph truth", "external action"):
        assert label in blocked
