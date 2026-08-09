from dataclasses import replace

import pytest

from orchestration.runtime.conversational_runtime_operation import (
    ChatAddressableRequest,
    handle_conversational_message,
    is_evidence_permission_recall_message,
    select_chat_request_owner,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import (
    classify_evidence_permission_operator_response,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph


EVIDENCE_PERMISSION_GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement, ask me one permission question about a later bounded evidence source. I may approve it for later, decline it, defer it, or give you "
    "the missing context. Do not gather evidence, inspect files, access a network, call a model or provider, use a tool, create a sandbox "
    "plan, take an external action, change source code, or restart. Wait for my scenarios."
)
PARAPHRASED_GOAL = (
    "Your new goal is to assess my scenarios while keeping evidence boundaries explicit. If a refined analysis still lacks a concrete source "
    "needed for verification, ask one clarifying question when uncertainty blocks refinement, then request my authorization for a narrow later evidence source or let me supply the context. Do not collect data, "
    "read files, use tools, contact providers, run models, alter code, or restart."
)
NO_EVIDENCE_PERMISSION_GOAL = (
    "Your new goal is to hold the next source-bound scenarios as provisional analyses. Ask me useful clarifying questions when unknown information blocks refinement and keep "
    "evidence, assumptions, validation checks, limits, and safe next actions. Do not call a model, access a provider, take an external action, "
    "change source code, or restart."
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


def _start(tmp_path, goal=EVIDENCE_PERMISSION_GOAL):
    result = _send(start_or_restore_runtime(tmp_path), goal, tmp_path)
    assert result.state.active_objective is not None
    return result.state


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _finance_permission_state(tmp_path, goal=EVIDENCE_PERMISSION_GOAL):
    state = _start(tmp_path, goal)
    framed = _send(state, FINANCE, tmp_path)
    assert framed.state.pending_chat_requests[0].request_type == "evidence_bound_analysis_question"
    answered = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", tmp_path)
    return framed, answered


def _cyber_permission_state(tmp_path):
    state = _start(tmp_path)
    framed = _send(state, CYBER, tmp_path)
    answered = _send(framed.state, "This is my local owned training fixture.", tmp_path)
    return framed, answered


def _operations_permission_state(tmp_path):
    state = _start(tmp_path)
    framed = _send(state, OPERATIONS, tmp_path)
    answered = _send(framed.state, "I do not know the pump ETA yet.", tmp_path)
    return framed, answered


def test_finance_refinement_surfaces_one_permission_request_without_evidence_execution(tmp_path):
    graph_before = load_graph(tmp_path)
    _framed, answered = _finance_permission_state(tmp_path)

    requests = _records(answered.state, "evidence_requests")
    authorizations = _records(answered.state, "evidence_authorizations")
    pending = answered.state.pending_chat_requests

    assert answered.intent.intent_type == "semantic_evidence_bound_analysis_question_answer"
    assert len(requests) == 1
    assert requests[0]["status"] == "surfaced"
    assert requests[0]["evidence_gap_slot_id"] == "finance.live_market_data_or_correlation_gap"
    assert requests[0]["source_refinement_id"] == _records(answered.state, "analysis_refinements")[0]["refinement_id"]
    assert requests[0]["source_analysis_id"] == _records(answered.state, "evidence_bound_analyses")[0]["analysis_id"]
    assert len(pending) == 1
    assert pending[0].request_type == "evidence_permission"
    assert pending[0].baseline_metrics["evidence_permission_request_id"] == requests[0]["evidence_permission_request_id"]
    assert pending[0].rendered_turn_id
    assert pending[0].render_sequence > 0
    assert "permission request only" in answered.reply.lower()
    assert "no evidence gathering has started" in answered.reply.lower()
    assert not authorizations

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_permission_request_generation_generalizes_for_cyber_and_operations(tmp_path):
    _framed, cyber = _cyber_permission_state(tmp_path / "cyber")
    cyber_request = _records(cyber.state, "evidence_requests")[0]
    assert cyber_request["evidence_gap_slot_id"] == "cyber.local_owned_fixture_verification_gap"
    assert cyber.state.pending_chat_requests[0].request_type == "evidence_permission"
    assert "read-only" in cyber.reply.lower()

    _framed, ops = _operations_permission_state(tmp_path / "ops")
    ops_request = _records(ops.state, "evidence_requests")[0]
    assert ops_request["evidence_gap_slot_id"] == "operations.pump_delivery_eta_status_gap"
    assert ops.state.pending_chat_requests[0].request_type == "evidence_permission"
    assert "bounded status lookup" in ops.reply.lower()


def test_permission_authorization_decisions_bind_once_and_never_execute(tmp_path):
    cases = (
        ("No, keep it hypothetical.", "denied", "not_authorized"),
        ("Yes, but only a local fixture.", "granted_pending_separate_execution", "local_fixture_only"),
        ("Not now; leave the evidence open.", "deferred", "deferred_by_operator"),
    )
    for response, expected_status, expected_scope in cases:
        root = tmp_path / expected_status
        _framed, prepared = _finance_permission_state(root)
        request = prepared.state.pending_chat_requests[0]
        evidence_request = _records(prepared.state, "evidence_requests")[0]

        assert classify_evidence_permission_operator_response(request.baseline_metrics, response) == expected_status
        assert select_chat_request_owner(prepared.state, response) == request

        result = _send(prepared.state, response, root)
        authorizations = _records(result.state, "evidence_authorizations")
        evidence_requests = _records(result.state, "evidence_requests")
        proposals = _records(result.state, "evidence_next_operation_proposals")

        assert result.intent.intent_type == "semantic_evidence_permission_authorization"
        assert len(authorizations) == 1
        assert authorizations[0]["evidence_request_id"] == evidence_request["evidence_permission_request_id"]
        assert authorizations[0]["status"] == expected_status
        assert authorizations[0]["interpreted_scope"] == expected_scope
        assert authorizations[0]["may_execute_now"] is False
        assert authorizations[0]["execution_state"] == "no_evidence_execution_started"
        assert evidence_requests[0]["status"] == expected_status
        if expected_status == "granted_pending_separate_execution":
            assert len(proposals) == 1
            assert proposals[0]["source_evidence_request_id"] == evidence_request["evidence_permission_request_id"]
            assert proposals[0]["source_evidence_authorization_id"] == authorizations[0]["evidence_authorization_id"]
            assert proposals[0]["may_execute_now"] is False
            assert result.state.pending_chat_requests[0].request_type == "evidence_next_operation_proposal"
        else:
            assert not proposals
            assert not result.state.pending_chat_requests
        assert result.state.resolved_chat_requests[-1].request_id == request.request_id
        assert result.state.resolved_chat_requests[-1].consumption_count == 1
        assert "no evidence gathering" in result.reply.lower()
        assert len(_records(result.state, "analysis_refinements")) == 1

        restored = start_or_restore_runtime(root)
        assert _records(restored, "evidence_authorizations") == authorizations
        if expected_status == "granted_pending_separate_execution":
            ordinary = _send(restored, "What is 2 + 2?", root)
            assert "4" in ordinary.reply
            assert len(_records(ordinary.state, "evidence_authorizations")) == 1
        else:
            duplicate = _send(restored, response, root)
            assert len(_records(duplicate.state, "evidence_authorizations")) == 1


def test_operator_context_resolves_operations_gap_without_lookup(tmp_path):
    _framed, prepared = _operations_permission_state(tmp_path)
    request = prepared.state.pending_chat_requests[0]
    result = _send(prepared.state, "The pump arrives Friday.", tmp_path)
    authorizations = _records(result.state, "evidence_authorizations")

    assert result.intent.intent_type == "semantic_evidence_permission_authorization"
    assert authorizations[0]["status"] == "operator_provided_context"
    assert authorizations[0]["operator_provided_context_text"] == "The pump arrives Friday."
    assert authorizations[0]["surface_request_id"] == request.request_id
    assert authorizations[0]["may_execute_now"] is False
    assert "instead of using any external lookup" in result.reply.lower()


def test_unclear_response_leaves_permission_request_pending_without_authorization(tmp_path):
    _framed, prepared = _finance_permission_state(tmp_path)
    request = prepared.state.pending_chat_requests[0]
    result = _send(prepared.state, "Maybe, it depends.", tmp_path)

    assert result.intent.intent_type == "semantic_evidence_permission_clarification"
    assert len(result.state.pending_chat_requests) == 1
    assert result.state.pending_chat_requests[0].request_id == request.request_id
    assert not _records(result.state, "evidence_authorizations")
    assert "cannot bind that as an evidence authorization" in result.reply.lower()


def test_permission_request_is_authority_gated_and_existing_request_suppresses_new_prompt(tmp_path):
    state = _start(tmp_path / "noauth", NO_EVIDENCE_PERMISSION_GOAL)
    framed = _send(state, FINANCE, tmp_path / "noauth")
    answered = _send(framed.state, "Assume losing more than 10% is unacceptable.", tmp_path / "noauth")
    requests = _records(answered.state, "evidence_requests")
    assert requests
    assert all(item["status"] == "deferred_not_authorized" for item in requests)
    assert not answered.state.pending_chat_requests

    state = _start(tmp_path / "suppressed")
    objective = state.active_objective
    assert objective is not None
    existing = ChatAddressableRequest(
        request_id="existing-pending-request",
        request_type="interactive_clarification",
        objective_id=objective.objective_id,
        goal_label="Existing request",
        prompt_text="Which source should I use?",
        rendered_turn_id="existing-turn",
        render_sequence=1,
        accepted_response_types=("clarification",),
    )
    framed = _send(state, FINANCE, tmp_path / "suppressed")
    state_with_existing = replace(framed.state, pending_chat_requests=(existing,) + framed.state.pending_chat_requests)
    answered = _send(state_with_existing, "Assume losing more than 10% is unacceptable.", tmp_path / "suppressed")
    requests = _records(answered.state, "evidence_requests")
    assert requests
    assert all(item["status"] == "suppressed_existing_request" for item in requests)
    assert len(answered.state.pending_chat_requests) == 1
    assert answered.state.pending_chat_requests[0].request_id == existing.request_id


def test_foreground_chat_and_recall_remain_ordinary_and_restart_safe(tmp_path):
    _framed, prepared = _finance_permission_state(tmp_path, PARAPHRASED_GOAL)
    request = prepared.state.pending_chat_requests[0]
    evidence_request = _records(prepared.state, "evidence_requests")[0]

    ordinary = _send(prepared.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert len(ordinary.state.pending_chat_requests) == 1
    assert ordinary.state.pending_chat_requests[0].request_id == request.request_id
    assert not _records(ordinary.state, "evidence_authorizations")

    denied = _send(ordinary.state, "No, keep it hypothetical.", tmp_path)
    assert _records(denied.state, "evidence_authorizations")[0]["status"] == "denied"

    recall_prompt = "What evidence did you need, and what did I authorize?"
    assert is_evidence_permission_recall_message(denied.state, recall_prompt)
    recalled = _send(denied.state, recall_prompt, tmp_path)
    assert recalled.intent.intent_type == "semantic_evidence_permission_recall"
    assert evidence_request["evidence_gap_slot_id"] in recalled.reply
    assert "denied" in recalled.reply.lower()
    assert len(_records(recalled.state, "evidence_authorizations")) == 1

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_requests")[0]["evidence_permission_request_id"] == evidence_request["evidence_permission_request_id"]
    assert len(_records(restored, "evidence_authorizations")) == 1
    restarted_recall = _send(restored, "What was the evidence request and my decision?", tmp_path)
    assert restarted_recall.intent.intent_type == "semantic_evidence_permission_recall"
    assert "read-only recall" in restarted_recall.reply.lower()
