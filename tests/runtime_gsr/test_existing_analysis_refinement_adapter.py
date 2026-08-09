from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
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


def _adapter_state(tmp_path, scenario=FINANCE, clarification="Assume losing more than 10% over six months is unacceptable."):
    ready = _plan_ready_state(tmp_path, scenario, clarification)
    return _send(ready.state, "Yes, record this bounded plan.", tmp_path)


def _routed_internal_candidate(state):
    revision = _records(state, "evidence_analysis_revision_candidates")[0]
    revision_id = revision["evidence_analysis_revision_candidate_id"]
    routed = [
        item
        for item in _records(state, "internal_work_candidates")
        if item.get("source_evidence_analysis_revision_candidate_id") == revision_id
    ]
    assert len(routed) == 1
    return revision, routed[0]


def test_revision_candidate_routes_to_existing_internal_work_without_new_approval(tmp_path):
    graph_before = load_graph(tmp_path)
    result = _adapter_state(tmp_path)
    revision, routed = _routed_internal_candidate(result.state)

    assert revision["status"] == "routed_to_existing_internal_work"
    assert revision["routed_internal_work_candidate_id"] == routed["internal_work_candidate_id"]
    assert routed["record_kind"] == "internal_work_candidate"
    assert routed["candidate_intent"] == "route_analysis_revision_candidate_to_existing_internal_work"
    assert routed["route_status"] == "routed_to_existing_internal_work"
    assert not result.state.pending_chat_requests
    assert not _records(result.state, "evidence_analysis_revision_approvals")
    assert "routed to internal work candidate" in result.reply.lower()
    assert "no new approval request" in result.reply.lower()

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_revision_candidate_routes_blocked_lookup_file_and_contact_cases(tmp_path):
    finance = _adapter_state(tmp_path / "finance")
    finance_revision, finance_route = _routed_internal_candidate(finance.state)
    assert finance_revision["proposed_revision_type"] == "note_lookup_still_blocked"
    assert "lookup" in finance_route["unresolved_label"]

    cyber = _adapter_state(
        tmp_path / "cyber",
        CYBER,
        "This is my local owned training fixture.",
    )
    cyber_revision, cyber_route = _routed_internal_candidate(cyber.state)
    assert cyber_revision["proposed_revision_type"] == "note_file_read_still_blocked"
    assert "file read" in cyber_route["unresolved_label"]

    ops = _adapter_state(
        tmp_path / "ops",
        OPERATIONS,
        "I do not know the pump ETA yet.",
    )
    ops_revision, ops_route = _routed_internal_candidate(ops.state)
    assert ops_revision["proposed_revision_type"] == "note_external_contact_still_blocked"
    assert "external contact" in ops_route["unresolved_label"]


def test_adapter_does_not_append_refinement_update_analysis_or_change_answer(tmp_path):
    result = _adapter_state(tmp_path)
    revision, routed = _routed_internal_candidate(result.state)
    blocked = " ".join(routed["prohibited_actions"]).lower()

    assert len(_records(result.state, "analysis_refinements")) == 1
    assert revision["may_append_refinement"] is False
    assert revision["may_update_analysis"] is False
    assert revision["may_update_problem_state"] is False
    assert revision["may_change_answer"] is False
    assert revision["may_update_graph"] is False
    assert "do not append analysisrefinement" in blocked
    assert "do not mutate analysis" in blocked
    assert "answer state" in blocked
    assert "graph truth" in blocked
    assert "replanning" in blocked


def test_duplicate_and_restart_preserve_same_routed_internal_work_candidate(tmp_path):
    result = _adapter_state(tmp_path)
    revision, routed = _routed_internal_candidate(result.state)
    routed_id = routed["internal_work_candidate_id"]

    restored = start_or_restore_runtime(tmp_path)
    restored_revision, restored_routed = _routed_internal_candidate(restored)
    assert restored_revision == revision
    assert restored_routed["internal_work_candidate_id"] == routed_id

    duplicate = _send(restored, "Yes, record this bounded plan.", tmp_path)
    duplicate_routes = [
        item
        for item in _records(duplicate.state, "internal_work_candidates")
        if item.get("source_evidence_analysis_revision_candidate_id") == revision["evidence_analysis_revision_candidate_id"]
    ]
    assert len(duplicate_routes) == 1
    assert duplicate.intent.intent_type == "ordinary_conversation"


def test_foreground_request_conflict_suppresses_adapter_route(tmp_path):
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
    assert not _records(result.state, "evidence_analysis_revision_candidates")
    assert not [
        item
        for item in _records(result.state, "internal_work_candidates")
        if item.get("source_evidence_analysis_revision_candidate_id")
    ]


def test_ordinary_chat_unchanged_before_and_after_adapter_route(tmp_path):
    ready = _plan_ready_state(tmp_path)
    ordinary_before = _send(ready.state, "What is 2 + 2?", tmp_path)
    assert ordinary_before.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_before.reply
    assert ordinary_before.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"

    routed = _send(ordinary_before.state, "Yes, record this bounded plan.", tmp_path)
    ordinary_after = _send(routed.state, "What is 2 + 2?", tmp_path)
    assert ordinary_after.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_after.reply
    _routed_internal_candidate(ordinary_after.state)


def test_adapter_side_effect_classes_remain_blocked(tmp_path):
    result = _adapter_state(tmp_path)
    _, routed = _routed_internal_candidate(result.state)
    blocked = " ".join(routed["prohibited_actions"]).lower()

    assert "analysis_refinement_append" in blocked
    assert "analysis_update" in blocked
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
