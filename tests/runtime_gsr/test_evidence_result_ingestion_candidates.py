from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import compile_evidence_result_ingestion_candidates
from orchestration.runtime.provisional_semantic_consolidation import load_graph


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
CYBER = "A request parameter is appended into a SQL command before execution."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."


def _send(state, text, tmp_path):
    return handle_conversational_message(
        state,
        text,
        runtime_root=tmp_path,
        run_background_cycle=False,
    )


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _plan_ready_state(tmp_path, scenario=FINANCE, clarification="Assume losing more than 10% over six months is unacceptable."):
    state = start_or_restore_runtime(tmp_path)
    started = _send(state, GOAL, tmp_path)
    framed = _send(started.state, scenario, tmp_path)
    refined = _send(framed.state, clarification, tmp_path)
    granted = _send(refined.state, "Yes, but only a local fixture.", tmp_path)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", tmp_path)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _candidate_state(tmp_path, scenario=FINANCE, clarification="Assume losing more than 10% over six months is unacceptable."):
    ready = _plan_ready_state(tmp_path, scenario, clarification)
    return _send(ready.state, "Yes, record this bounded plan.", tmp_path)


def test_dry_run_result_creates_one_inert_ingestion_candidate(tmp_path):
    graph_before = load_graph(tmp_path)
    result = _candidate_state(tmp_path)
    dry_runs = _records(result.state, "evidence_fixture_dry_run_results")
    candidates = _records(result.state, "evidence_result_ingestion_candidates")
    refinements = _records(result.state, "analysis_refinements")

    assert len(dry_runs) == 1
    assert len(candidates) == 1
    candidate = candidates[0]
    dry_run = dry_runs[0]
    request = _records(result.state, "evidence_requests")[0]
    assert candidate["source_dry_run_result_id"] == dry_run["evidence_fixture_dry_run_result_id"]
    assert candidate["source_plan_id"] == dry_run["source_plan_id"]
    assert candidate["source_execution_authority_id"] == dry_run["source_execution_authority_id"]
    assert candidate["source_proposal_id"] == dry_run["source_proposal_id"]
    assert candidate["source_evidence_request_id"] == dry_run["source_evidence_request_id"]
    assert candidate["source_evidence_authorization_id"] == dry_run["source_evidence_authorization_id"]
    assert candidate["source_analysis_id"] == request["source_analysis_id"]
    assert candidate["may_update_analysis"] is False
    assert candidate["may_update_problem_state"] is False
    assert candidate["may_update_graph"] is False
    assert candidate["requires_analysis_revision_gate"] is True
    assert "ingestion candidate recorded" in result.reply.lower()
    assert "requires_analysis_revision_gate=true" in result.reply
    assert _records(result.state, "analysis_refinements") == refinements

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_ingestion_candidate_effect_types_for_market_fixture_and_operations(tmp_path):
    finance = _candidate_state(tmp_path / "finance")
    finance_candidate = _records(finance.state, "evidence_result_ingestion_candidates")[0]
    assert finance_candidate["candidate_effect_type"] == "evidence_gap_remains_lookup_blocked"

    cyber = _candidate_state(
        tmp_path / "cyber",
        CYBER,
        "This is my local owned training fixture.",
    )
    cyber_candidate = _records(cyber.state, "evidence_result_ingestion_candidates")[0]
    assert cyber_candidate["candidate_effect_type"] == "evidence_gap_remains_file_read_blocked"

    ops = _candidate_state(
        tmp_path / "ops",
        OPERATIONS,
        "I do not know the pump ETA yet.",
    )
    ops_candidate = _records(ops.state, "evidence_result_ingestion_candidates")[0]
    assert ops_candidate["candidate_effect_type"] == "evidence_gap_remains_external_contact_blocked"


def test_missing_ids_executable_or_update_enabled_dry_runs_create_no_candidate(tmp_path):
    result = _candidate_state(tmp_path)
    dry_run = _records(result.state, "evidence_fixture_dry_run_results")[0]
    request = _records(result.state, "evidence_requests")[0]
    objective_id = result.state.active_objective.objective_id

    missing = {**dict(dry_run), "evidence_fixture_dry_run_result_id": ""}
    analysis_enabled = {**dict(dry_run), "may_update_analysis": True}
    graph_enabled = {**dict(dry_run), "may_update_graph": True}
    no_gate = {**dict(dry_run), "requires_result_ingestion_gate": False}

    assert compile_evidence_result_ingestion_candidates(missing, objective_id=objective_id, source_evidence_request=request) == ()
    assert compile_evidence_result_ingestion_candidates(analysis_enabled, objective_id=objective_id, source_evidence_request=request) == ()
    assert compile_evidence_result_ingestion_candidates(graph_enabled, objective_id=objective_id, source_evidence_request=request) == ()
    assert compile_evidence_result_ingestion_candidates(no_gate, objective_id=objective_id, source_evidence_request=request) == ()


def test_duplicate_and_restart_preserve_same_ingestion_candidate(tmp_path):
    result = _candidate_state(tmp_path)
    candidates = _records(result.state, "evidence_result_ingestion_candidates")
    assert len(candidates) == 1

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_result_ingestion_candidates") == candidates
    duplicate = _send(restored, "Yes, record this bounded plan.", tmp_path)
    assert len(_records(duplicate.state, "evidence_result_ingestion_candidates")) == 1
    assert duplicate.intent.intent_type == "ordinary_conversation"


def test_pending_foreground_request_suppresses_ingestion_candidate(tmp_path):
    ready = _plan_ready_state(tmp_path)
    pending_request = ready.state.pending_chat_requests[0]
    conflicting_request = replace(
        pending_request,
        request_id="unrelated-pending-request",
        request_type="evidence_permission",
        render_sequence=-1,
        created_sequence=-1,
    )
    state = replace(
        ready.state,
        pending_chat_requests=(pending_request, conflicting_request),
    )

    result = _send(state, "Yes, record this bounded plan.", tmp_path)
    assert not _records(result.state, "evidence_fixture_dry_run_results")
    assert not _records(result.state, "evidence_result_ingestion_candidates")
    assert any(item.get("event") == "evidence_fixture_dry_run_suppressed_existing_request" for item in result.state.objective_progress)


def test_ordinary_chat_unchanged_before_and_after_candidate(tmp_path):
    ready = _plan_ready_state(tmp_path)
    ordinary_before = _send(ready.state, "What is 2 + 2?", tmp_path)
    assert ordinary_before.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_before.reply
    assert ordinary_before.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    assert not _records(ordinary_before.state, "evidence_result_ingestion_candidates")

    candidate = _send(ordinary_before.state, "Yes, record this bounded plan.", tmp_path)
    ordinary_after = _send(candidate.state, "What is 2 + 2?", tmp_path)
    assert ordinary_after.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_after.reply
    assert len(_records(ordinary_after.state, "evidence_result_ingestion_candidates")) == 1


def test_ingestion_candidate_side_effect_flags_block_mutation_classes(tmp_path):
    result = _candidate_state(tmp_path)
    candidate = _records(result.state, "evidence_result_ingestion_candidates")[0]
    blocked = " ".join(candidate["blocked_update_scope"]).lower()

    assert candidate["may_update_analysis"] is False
    assert candidate["may_update_problem_state"] is False
    assert candidate["may_update_graph"] is False
    assert candidate["requires_analysis_revision_gate"] is True
    assert "analysis_update" in blocked
    assert "analysis_refinement" in blocked
    assert "problem_state_update" in blocked
    assert "graph_update" in blocked
    assert "review_admission" in blocked
    assert "replanning" in blocked
    assert "file_read" in blocked
    assert "repo_read" in blocked
    assert "network" in blocked
    assert "tool" in blocked
    assert "model" in blocked
    assert "provider" in blocked
    assert "sandbox" in blocked
