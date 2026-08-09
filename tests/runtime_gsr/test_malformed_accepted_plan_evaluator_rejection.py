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
    "When a structured evidence gap materially limits a safer refinement, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."


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
    state = start_or_restore_runtime(root)
    started = _send(state, GOAL, root)
    framed = _send(started.state, FINANCE, root)
    refined = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _accepted_looking_plan(state):
    plan = _record(state, "evidence_fixture_execution_plans")
    return {
        **dict(plan),
        "status": "accepted_pending_execution_gate",
        "may_execute_now": False,
        "execution_requires_future_gate": True,
    }


def _assert_no_positive_state_change(state, graph_before, root):
    assert not _records(state, "evidence_fixture_dry_run_results")
    assert not _records(state, "evidence_result_ingestion_candidates")
    assert not _records(state, "evidence_analysis_revision_candidates")
    assert not _records(state, "evidence_minimal_fixture_results")
    assert not [item for item in _records(state, "analysis_refinements") if item.get("status") == "controlled_fixture_refinement"]
    assert not [
        item
        for item in _records(state, "internal_work_candidates")
        if item.get("controlled_fixture_problem_state_update_id")
    ]
    assert not [
        item
        for item in _records(state, "internal_work_selections")
        if item.get("source_evidence_minimal_fixture_result_id") or item.get("controlled_fixture_problem_state_update_id")
    ]
    assert _graph_snapshot(root) == graph_before


@pytest.mark.parametrize(
    "label,malformed_source_text",
    (
        ("missing_third_sleeve", "My account is 70% aggressive tech funds and 20% cash."),
        ("weights_not_100_percent", "My account is 70% aggressive tech funds, 20% cash, and 20% small-cap value."),
        ("nonnumeric_sleeve", "My account is 70% aggressive tech funds, cash is variable, and 10% small-cap value."),
    ),
)
def test_accepted_looking_plan_rejects_malformed_finance_source_without_fallback(tmp_path, label, malformed_source_text):
    ready = _plan_ready_state(tmp_path / label)
    state = ready.state
    objective = state.active_objective
    assert objective is not None
    graph_before = _graph_snapshot(tmp_path / label)
    analysis = _record(state, "evidence_bound_analyses")
    malformed_analysis = {**dict(analysis), "source_text": malformed_source_text}

    first = compile_evidence_minimal_fixture_results(
        _accepted_looking_plan(state),
        objective_id=objective.objective_id,
        source_analysis=malformed_analysis,
    )
    second = compile_evidence_minimal_fixture_results(
        _accepted_looking_plan(state),
        objective_id=objective.objective_id,
        source_analysis=malformed_analysis,
    )

    assert first == ()
    assert second == ()
    _assert_no_positive_state_change(state, graph_before, tmp_path / label)


def test_accepted_looking_plan_rejects_mismatched_source_analysis_lineage(tmp_path):
    ready = _plan_ready_state(tmp_path)
    state = ready.state
    objective = state.active_objective
    assert objective is not None
    graph_before = _graph_snapshot(tmp_path)
    analysis = _record(state, "evidence_bound_analyses")
    mismatched_analysis = {**dict(analysis), "analysis_id": "unrelated-source-analysis"}
    revision_bound_to_original = {
        "evidence_analysis_revision_candidate_id": "revision-bound-to-original-analysis",
        "source_analysis_id": analysis["analysis_id"],
    }

    assert compile_evidence_minimal_fixture_results(
        _accepted_looking_plan(state),
        objective_id=objective.objective_id,
        source_analysis=mismatched_analysis,
        source_revision_candidate=revision_bound_to_original,
    ) == ()
    _assert_no_positive_state_change(state, graph_before, tmp_path)


def test_malformed_accepted_plan_boundary_preserves_ordinary_chat_and_blocks_external_actions(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    ready = _plan_ready_state(tmp_path)
    state = ready.state
    objective = state.active_objective
    assert objective is not None
    analysis = _record(state, "evidence_bound_analyses")
    malformed_analysis = {**dict(analysis), "source_text": "My account is 60% tech funds and cash is variable."}

    assert compile_evidence_minimal_fixture_results(
        _accepted_looking_plan(state),
        objective_id=objective.objective_id,
        source_analysis=malformed_analysis,
    ) == ()
    ordinary = _send(state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert ordinary.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
