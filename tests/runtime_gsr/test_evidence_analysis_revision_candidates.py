from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import compile_evidence_analysis_revision_candidates
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


def _revision_candidate_state(tmp_path, scenario=FINANCE, clarification="Assume losing more than 10% over six months is unacceptable."):
    ready = _plan_ready_state(tmp_path, scenario, clarification)
    return _send(ready.state, "Yes, record this bounded plan.", tmp_path)


def test_ingestion_candidate_creates_one_inert_analysis_revision_candidate(tmp_path):
    graph_before = load_graph(tmp_path)
    result = _revision_candidate_state(tmp_path)
    ingestion_candidates = _records(result.state, "evidence_result_ingestion_candidates")
    revision_candidates = _records(result.state, "evidence_analysis_revision_candidates")
    refinements = _records(result.state, "analysis_refinements")

    assert len(ingestion_candidates) == 1
    assert len(revision_candidates) == 1
    ingestion = ingestion_candidates[0]
    revision = revision_candidates[0]
    assert revision["source_ingestion_candidate_id"] == ingestion["evidence_result_ingestion_candidate_id"]
    assert revision["source_dry_run_result_id"] == ingestion["source_dry_run_result_id"]
    assert revision["source_plan_id"] == ingestion["source_plan_id"]
    assert revision["source_execution_authority_id"] == ingestion["source_execution_authority_id"]
    assert revision["source_proposal_id"] == ingestion["source_proposal_id"]
    assert revision["source_evidence_request_id"] == ingestion["source_evidence_request_id"]
    assert revision["source_evidence_authorization_id"] == ingestion["source_evidence_authorization_id"]
    assert revision["source_analysis_id"] == ingestion["source_analysis_id"]
    assert revision["may_append_refinement"] is False
    assert revision["may_update_analysis"] is False
    assert revision["may_update_problem_state"] is False
    assert revision["may_change_answer"] is False
    assert revision["may_update_graph"] is False
    assert revision["requires_analysis_revision_gate"] is True
    assert "analysis revision candidate recorded" in result.reply.lower()
    assert "may_append_refinement=false" in result.reply
    assert _records(result.state, "analysis_refinements") == refinements

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_revision_candidate_types_for_lookup_file_contact_and_generic(tmp_path):
    finance = _revision_candidate_state(tmp_path / "finance")
    finance_candidate = _records(finance.state, "evidence_analysis_revision_candidates")[0]
    assert finance_candidate["proposed_revision_type"] == "note_lookup_still_blocked"

    cyber = _revision_candidate_state(
        tmp_path / "cyber",
        CYBER,
        "This is my local owned training fixture.",
    )
    cyber_candidate = _records(cyber.state, "evidence_analysis_revision_candidates")[0]
    assert cyber_candidate["proposed_revision_type"] == "note_file_read_still_blocked"

    ops = _revision_candidate_state(
        tmp_path / "ops",
        OPERATIONS,
        "I do not know the pump ETA yet.",
    )
    ops_candidate = _records(ops.state, "evidence_analysis_revision_candidates")[0]
    assert ops_candidate["proposed_revision_type"] == "note_external_contact_still_blocked"

    generic_source = dict(_records(finance.state, "evidence_result_ingestion_candidates")[0])
    generic_source["candidate_effect_type"] = "unexpected_boundary"
    generic = compile_evidence_analysis_revision_candidates(
        generic_source,
        objective_id=finance.state.active_objective.objective_id,
    )
    assert len(generic) == 1
    assert generic[0].proposed_revision_type == "note_dry_run_boundary_only"


def test_missing_required_ids_or_update_authority_create_no_revision_candidate(tmp_path):
    result = _revision_candidate_state(tmp_path)
    ingestion = _records(result.state, "evidence_result_ingestion_candidates")[0]
    objective_id = result.state.active_objective.objective_id

    missing = {**dict(ingestion), "evidence_result_ingestion_candidate_id": ""}
    analysis_enabled = {**dict(ingestion), "may_update_analysis": True}
    refinement_enabled = {**dict(ingestion), "may_append_refinement": True}
    problem_enabled = {**dict(ingestion), "may_update_problem_state": True}
    answer_enabled = {**dict(ingestion), "may_change_answer": True}
    graph_enabled = {**dict(ingestion), "may_update_graph": True}
    no_gate = {**dict(ingestion), "requires_analysis_revision_gate": False}

    assert compile_evidence_analysis_revision_candidates(missing, objective_id=objective_id) == ()
    assert compile_evidence_analysis_revision_candidates(analysis_enabled, objective_id=objective_id) == ()
    assert compile_evidence_analysis_revision_candidates(refinement_enabled, objective_id=objective_id) == ()
    assert compile_evidence_analysis_revision_candidates(problem_enabled, objective_id=objective_id) == ()
    assert compile_evidence_analysis_revision_candidates(answer_enabled, objective_id=objective_id) == ()
    assert compile_evidence_analysis_revision_candidates(graph_enabled, objective_id=objective_id) == ()
    assert compile_evidence_analysis_revision_candidates(no_gate, objective_id=objective_id) == ()


def test_duplicate_and_restart_preserve_same_revision_candidate(tmp_path):
    result = _revision_candidate_state(tmp_path)
    candidates = _records(result.state, "evidence_analysis_revision_candidates")
    assert len(candidates) == 1

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_analysis_revision_candidates") == candidates
    duplicate = _send(restored, "Yes, record this bounded plan.", tmp_path)
    assert len(_records(duplicate.state, "evidence_analysis_revision_candidates")) == 1
    assert duplicate.intent.intent_type == "ordinary_conversation"


def test_pending_foreground_request_suppresses_revision_candidate(tmp_path):
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
    assert not _records(result.state, "evidence_result_ingestion_candidates")
    assert not _records(result.state, "evidence_analysis_revision_candidates")
    assert any(item.get("event") == "evidence_fixture_dry_run_suppressed_existing_request" for item in result.state.objective_progress)


def test_ordinary_chat_unchanged_before_and_after_revision_candidate(tmp_path):
    ready = _plan_ready_state(tmp_path)
    ordinary_before = _send(ready.state, "What is 2 + 2?", tmp_path)
    assert ordinary_before.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_before.reply
    assert ordinary_before.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    assert not _records(ordinary_before.state, "evidence_analysis_revision_candidates")

    candidate = _send(ordinary_before.state, "Yes, record this bounded plan.", tmp_path)
    ordinary_after = _send(candidate.state, "What is 2 + 2?", tmp_path)
    assert ordinary_after.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_after.reply
    assert len(_records(ordinary_after.state, "evidence_analysis_revision_candidates")) == 1


def test_revision_candidate_side_effect_flags_block_mutation_classes(tmp_path):
    result = _revision_candidate_state(tmp_path)
    candidate = _records(result.state, "evidence_analysis_revision_candidates")[0]
    blocked = " ".join(candidate["blocked_change"]).lower()

    assert candidate["may_append_refinement"] is False
    assert candidate["may_update_analysis"] is False
    assert candidate["may_update_problem_state"] is False
    assert candidate["may_change_answer"] is False
    assert candidate["may_update_graph"] is False
    assert candidate["requires_analysis_revision_gate"] is True
    assert "analysis_update" in blocked
    assert "analysis_refinement_append" in blocked
    assert "problem_state_update" in blocked
    assert "answer_change" in blocked
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
