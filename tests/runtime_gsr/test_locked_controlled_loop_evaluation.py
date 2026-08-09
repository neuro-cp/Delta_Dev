import os
import json
import socket
import subprocess
import urllib.request

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
FINANCE_MALFORMED = "My account is 70% aggressive tech funds and 20% cash. I am worried about AI stocks dropping over six months."
CYBER = "A request parameter is appended into a SQL command before execution."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
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


def _graph_snapshot(root):
    graph = load_graph(root)
    return (
        tuple(graph.experiences),
        tuple(graph.claim_versions),
        tuple(graph.packets),
        tuple(graph.reviews),
        tuple(graph.admissions),
    )


def _canonical_records(records):
    return json.loads(json.dumps(records, sort_keys=True))


def _plan_ready_state(root, scenario=FINANCE, clarification="Assume losing more than 10% over six months is unacceptable.", goal=GOAL):
    state = start_or_restore_runtime(root)
    started = _send(state, goal, root)
    framed = _send(started.state, scenario, root)
    refined = _send(framed.state, clarification, root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _closed_loop_state(root, **kwargs):
    ready = _plan_ready_state(root, **kwargs)
    return _send(ready.state, "Yes, record this bounded plan.", root)


def _physics_closed_loop_state(root):
    state = start_or_restore_runtime(root)
    started = _send(state, GOAL, root)
    framed = _send(started.state, PHYSICS, root)
    refined = _send(framed.state, "A numeric result is most useful.", root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return _send(authority.state, "Yes, record this bounded plan.", root)


def _controlled_refinement(state):
    refinements = [item for item in _records(state, "analysis_refinements") if item.get("status") == "controlled_fixture_refinement"]
    assert len(refinements) == 1
    return refinements[0]


def _controlled_selection(state, refinement):
    selections = [
        item
        for item in _records(state, "internal_work_selections")
        if item.get("source_refinement_id") == refinement["refinement_id"]
        and item.get("source_evidence_minimal_fixture_result_id") == refinement["source_evidence_minimal_fixture_result_id"]
        and item.get("status") == "selected_record_only"
    ]
    assert len(selections) == 1
    return selections[0]


def _assert_no_positive_completion(state):
    assert not _records(state, "evidence_minimal_fixture_results")
    assert not [item for item in _records(state, "analysis_refinements") if item.get("status") == "controlled_fixture_refinement"]
    assert not [
        item
        for item in _records(state, "internal_work_selections")
        if item.get("source_evidence_minimal_fixture_result_id") or item.get("controlled_fixture_problem_state_update_id")
    ]
    assert not [item for item in _records(state, "internal_work_candidates") if item.get("controlled_fixture_problem_state_update_id")]


def test_fin_01_positive_finance_completion_is_exactly_source_bound(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    result = _closed_loop_state(tmp_path)

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

    assert fixture["fixture_kind"] == "in_memory_hypothetical_portfolio_drawdown_table"
    assert "-11.3%" in fixture["deterministic_output"]
    assert dry_run["source_plan_id"] == plan["evidence_fixture_execution_plan_id"]
    assert ingestion["source_dry_run_result_id"] == dry_run["evidence_fixture_dry_run_result_id"]
    assert revision["source_ingestion_candidate_id"] == ingestion["evidence_result_ingestion_candidate_id"]
    assert routed["source_evidence_analysis_revision_candidate_id"] == revision["evidence_analysis_revision_candidate_id"]
    assert fixture["source_internal_work_candidate_id"] == routed["internal_work_candidate_id"]
    assert refinement["source_evidence_minimal_fixture_result_id"] == fixture["evidence_minimal_fixture_result_id"]
    assert routed["controlled_fixture_refinement_id"] == refinement["refinement_id"]
    assert selection["source_refinement_id"] == refinement["refinement_id"]
    assert selection["may_execute_now"] is False
    assert _graph_snapshot(tmp_path) == graph_before


def test_fin_02_malformed_finance_rejects_positive_completion_without_fallback(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    started = _send(state, GOAL, tmp_path)
    framed = _send(started.state, FINANCE_MALFORMED, tmp_path)
    result = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", tmp_path)

    assert not _records(result.state, "evidence_fixture_execution_plans")
    assert not _records(result.state, "evidence_fixture_dry_run_results")
    assert not _records(result.state, "evidence_result_ingestion_candidates")
    assert not _records(result.state, "evidence_analysis_revision_candidates")
    _assert_no_positive_completion(result.state)


def test_ops_01_records_only_blocked_external_contact_boundary(tmp_path):
    result = _closed_loop_state(tmp_path, scenario=OPERATIONS, clarification="I do not know the pump ETA yet.")

    dry_run = _record(result.state, "evidence_fixture_dry_run_results")
    revision = _record(result.state, "evidence_analysis_revision_candidates")
    assert dry_run["fixture_kind"] == "synthetic_operational_status_blocked"
    assert revision["proposed_revision_type"] == "note_external_contact_still_blocked"
    assert "did not contact people or systems" in dry_run["deterministic_result"].lower()
    _assert_no_positive_completion(result.state)


def test_cyb_01_records_only_blocked_owned_fixture_boundary(tmp_path):
    result = _closed_loop_state(tmp_path, scenario=CYBER, clarification="This is my local owned training fixture.")

    dry_run = _record(result.state, "evidence_fixture_dry_run_results")
    revision = _record(result.state, "evidence_analysis_revision_candidates")
    assert dry_run["fixture_kind"] == "synthetic_owned_fixture_inspection_blocked"
    assert revision["proposed_revision_type"] == "note_file_read_still_blocked"
    assert "without reading a repository file" in dry_run["deterministic_result"].lower()
    _assert_no_positive_completion(result.state)


def test_phy_01_positive_physics_completion_is_source_bound(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    result = _physics_closed_loop_state(tmp_path)
    fixture = _record(result.state, "evidence_minimal_fixture_results")
    refinement = _controlled_refinement(result.state)
    selection = _controlled_selection(result.state, refinement)

    assert fixture["fixture_kind"] == "in_memory_frictionless_thirty_degree_incline_calculation"
    assert "4.9 m/s^2" in fixture["deterministic_output"]
    assert refinement["changed_unknown_slots"] == ("physics.frictionless_thirty_degree_calculation",)
    assert selection["selected_next_operation"] == "retain_frictionless_incline_calculation_and_wait_for_later_authority"
    assert _graph_snapshot(tmp_path) == graph_before


def test_chat_01_ordinary_question_leaves_surfaced_plan_unchanged(tmp_path):
    ready = _plan_ready_state(tmp_path)
    pending_id = ready.state.pending_chat_requests[0].request_id
    result = _send(ready.state, "What is 2 + 2?", tmp_path)

    assert result.intent.intent_type == "ordinary_conversation"
    assert "4" in result.reply
    assert result.state.pending_chat_requests[0].request_id == pending_id
    assert not _records(result.state, "evidence_fixture_dry_run_results")
    assert not _records(result.state, "evidence_minimal_fixture_results")


def test_chat_02_ordinary_question_after_loop_does_not_duplicate_records(tmp_path):
    completed = _closed_loop_state(tmp_path)
    before = {key: _records(completed.state, key) for key in ("evidence_minimal_fixture_results", "analysis_refinements", "internal_work_selections")}
    result = _send(completed.state, "What is 2 + 2?", tmp_path)

    assert result.intent.intent_type == "ordinary_conversation"
    assert "4" in result.reply
    assert {key: _records(result.state, key) for key in before} == before


def test_rst_01_restart_recovers_surfaced_and_completed_boundaries_exactly_once(tmp_path):
    ready = _plan_ready_state(tmp_path)
    pending_id = ready.state.pending_chat_requests[0].request_id
    restored_ready = start_or_restore_runtime(tmp_path)
    assert restored_ready.pending_chat_requests[0].request_id == pending_id

    completed = _send(restored_ready, "Yes, record this bounded plan.", tmp_path)
    expected = {
        key: _canonical_records(_records(completed.state, key))
        for key in ("evidence_fixture_execution_plans", "evidence_minimal_fixture_results", "analysis_refinements", "internal_work_selections")
    }
    restored_completed = start_or_restore_runtime(tmp_path)
    assert {key: _canonical_records(_records(restored_completed, key)) for key in expected} == expected
    duplicate = _send(restored_completed, "Yes, record this bounded plan.", tmp_path)
    assert duplicate.intent.intent_type == "ordinary_conversation"
    assert {key: _canonical_records(_records(duplicate.state, key)) for key in expected} == expected


def test_auth_01_denied_deferred_and_context_dispositions_stop_downstream_execution(tmp_path):
    for label, response in (
        ("denied", "No, do not record this plan."),
        ("deferred", "Not now; leave it open."),
        ("context", "Use only an in-memory hypothetical table shape for this plan."),
    ):
        ready = _plan_ready_state(tmp_path / label)
        result = _send(ready.state, response, tmp_path / label)
        assert not result.state.pending_chat_requests
        for key in (
            "evidence_fixture_dry_run_results",
            "evidence_result_ingestion_candidates",
            "evidence_analysis_revision_candidates",
        ):
            assert not _records(result.state, key)
        _assert_no_positive_completion(result.state)


def test_mal_01_malformed_or_cross_bound_compiler_inputs_fail_closed(tmp_path):
    completed = _closed_loop_state(tmp_path)
    objective = completed.state.active_objective
    assert objective is not None
    plan = _record(completed.state, "evidence_fixture_execution_plans")
    analysis = _record(completed.state, "evidence_bound_analyses")
    revision = _record(completed.state, "evidence_analysis_revision_candidates")
    routed = next(item for item in _records(completed.state, "internal_work_candidates") if item.get("source_evidence_analysis_revision_candidate_id"))

    for invalid_plan, invalid_revision, invalid_routed in (
        ({**dict(plan), "evidence_fixture_execution_plan_id": ""}, revision, routed),
        ({**dict(plan), "may_execute_now": True}, revision, routed),
        ({**dict(plan), "evidence_source_class": "owned_fixture_read_only_plan"}, revision, routed),
        (plan, {**dict(revision), "source_analysis_id": "unrelated-analysis"}, routed),
        (plan, revision, {**dict(routed), "source_evidence_analysis_revision_candidate_id": "unrelated-revision"}),
    ):
        assert compile_evidence_minimal_fixture_results(
            invalid_plan,
            objective_id=objective.objective_id,
            source_analysis=analysis,
            source_revision_candidate=invalid_revision,
            source_internal_work_candidate=invalid_routed,
        ) == ()


def test_dup_01_replayed_accepted_response_keeps_every_controlled_record_singleton(tmp_path):
    completed = _closed_loop_state(tmp_path)
    keys = (
        "evidence_fixture_dry_run_results",
        "evidence_result_ingestion_candidates",
        "evidence_analysis_revision_candidates",
        "evidence_minimal_fixture_results",
        "analysis_refinements",
        "internal_work_selections",
    )
    expected = {key: _records(completed.state, key) for key in keys}
    replayed = _send(completed.state, "Yes, record this bounded plan.", tmp_path)

    assert replayed.intent.intent_type == "ordinary_conversation"
    assert {key: _records(replayed.state, key) for key in keys} == expected


def test_graph_01_controlled_loop_leaves_graph_records_unchanged(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    _closed_loop_state(tmp_path)
    assert _graph_snapshot(tmp_path) == graph_before


def test_sidefx_01_external_action_guards_are_never_reached(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    result = _closed_loop_state(tmp_path)
    fixture = _record(result.state, "evidence_minimal_fixture_results")
    blocked = " ".join(fixture["blocked_actions"]).lower()
    for forbidden_label in ("repository file read", "local filesystem read", "network", "model", "provider", "tool", "sandbox", "graph truth", "external action"):
        assert forbidden_label in blocked


def test_bind_01_similar_objectives_remain_isolated_by_exact_lineage(tmp_path):
    first = _closed_loop_state(
        tmp_path / "first",
        scenario="Account alpha is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months.",
        goal=GOAL + " Use the alpha scenario only.",
    )
    second = _closed_loop_state(
        tmp_path / "second",
        scenario="Account beta is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months.",
        goal=GOAL + " Use the beta scenario only.",
    )

    first_objective = first.state.active_objective
    second_objective = second.state.active_objective
    assert first_objective is not None and second_objective is not None
    first_fixture = _record(first.state, "evidence_minimal_fixture_results")
    second_fixture = _record(second.state, "evidence_minimal_fixture_results")
    first_refinement = _controlled_refinement(first.state)
    second_refinement = _controlled_refinement(second.state)

    assert first_objective.objective_id != second_objective.objective_id
    assert first_fixture["evidence_minimal_fixture_result_id"] != second_fixture["evidence_minimal_fixture_result_id"]
    assert first_refinement["source_evidence_minimal_fixture_result_id"] == first_fixture["evidence_minimal_fixture_result_id"]
    assert second_refinement["source_evidence_minimal_fixture_result_id"] == second_fixture["evidence_minimal_fixture_result_id"]
