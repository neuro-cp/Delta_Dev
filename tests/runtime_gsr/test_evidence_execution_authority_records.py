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


def _proposal_accepted_state(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    started = _send(state, GOAL, tmp_path)
    framed = _send(started.state, FINANCE, tmp_path)
    refined = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", tmp_path)
    granted = _send(refined.state, "Yes, but only a local fixture.", tmp_path)
    assert granted.state.pending_chat_requests[0].request_type == "evidence_next_operation_proposal"
    accepted = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    assert accepted.state.pending_chat_requests[0].request_type == "evidence_execution_authority"
    return accepted


def test_accepted_proposal_surfaces_one_execution_authority_request_without_execution(tmp_path):
    result = _proposal_accepted_state(tmp_path)
    requests = _records(result.state, "evidence_requests")
    authorizations = _records(result.state, "evidence_authorizations")
    proposals = _records(result.state, "evidence_next_operation_proposals")
    dispositions = _records(result.state, "evidence_next_operation_dispositions")
    pending = result.state.pending_chat_requests

    assert len(requests) == 1
    assert len(authorizations) == 1
    assert len(proposals) == 1
    assert len(dispositions) == 1
    assert not _records(result.state, "evidence_execution_authorities")
    assert len(pending) == 1
    assert pending[0].request_type == "evidence_execution_authority"
    assert pending[0].baseline_metrics["evidence_next_operation_proposal_id"] == proposals[0]["evidence_next_operation_proposal_id"]
    assert pending[0].baseline_metrics["evidence_next_operation_disposition_id"] == dispositions[0]["evidence_next_operation_disposition_id"]
    assert "execution authority request only" in result.reply.lower()
    assert "future execution would require a separate gate" in result.reply.lower()


def test_operator_approval_creates_one_inert_execution_authority_record(tmp_path):
    prepared = _proposal_accepted_state(tmp_path)
    graph_before = load_graph(tmp_path)
    request = prepared.state.pending_chat_requests[0]
    result = _send(prepared.state, "Yes, record approval for a future bounded execution gate.", tmp_path)
    authorities = _records(result.state, "evidence_execution_authorities")
    proposal = _records(result.state, "evidence_next_operation_proposals")[0]
    disposition = _records(result.state, "evidence_next_operation_dispositions")[0]

    assert result.intent.intent_type == "semantic_evidence_execution_authority_record"
    assert len(authorities) == 1
    authority = authorities[0]
    assert authority["operator_decision"] == "approved_for_future_gate"
    assert authority["status"] == "approved_for_future_gate"
    assert authority["source_evidence_request_id"] == proposal["source_evidence_request_id"]
    assert authority["source_evidence_authorization_id"] == proposal["source_evidence_authorization_id"]
    assert authority["source_evidence_next_operation_proposal_id"] == proposal["evidence_next_operation_proposal_id"]
    assert authority["source_evidence_next_operation_disposition_id"] == disposition["evidence_next_operation_disposition_id"]
    assert authority["may_execute_now"] is False
    assert authority["execution_requires_future_gate"] is True
    assert not result.state.pending_chat_requests
    assert result.state.resolved_chat_requests[-1].request_id == request.request_id
    assert "nothing executed now" in result.reply.lower()

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_decline_defer_and_context_record_inert_non_executable_postures(tmp_path):
    cases = (
        ("No, do not record execution authority.", "declined"),
        ("Not now; leave it open.", "deferred"),
        ("The future source should be a hypothetical table, not live market data.", "context_provided"),
    )
    for response, expected in cases:
        root = tmp_path / expected
        prepared = _proposal_accepted_state(root)
        result = _send(prepared.state, response, root)
        authorities = _records(result.state, "evidence_execution_authorities")

        assert result.intent.intent_type == "semantic_evidence_execution_authority_record"
        assert len(authorities) == 1
        assert authorities[0]["operator_decision"] == expected
        assert authorities[0]["may_execute_now"] is False
        assert authorities[0]["execution_requires_future_gate"] is True
        assert not result.state.pending_chat_requests
        assert "no evidence gathering" in result.reply.lower()


def test_unclear_authority_response_leaves_request_pending_without_record(tmp_path):
    prepared = _proposal_accepted_state(tmp_path)
    request = prepared.state.pending_chat_requests[0]
    result = _send(prepared.state, "Maybe, it depends.", tmp_path)

    assert result.intent.intent_type == "semantic_evidence_execution_authority_clarification"
    assert not _records(result.state, "evidence_execution_authorities")
    assert len(result.state.pending_chat_requests) == 1
    assert result.state.pending_chat_requests[0].request_id == request.request_id
    assert "cannot bind that as future execution authority" in result.reply.lower()


def test_restart_preserves_execution_authority_once_and_ordinary_chat_stays_ordinary(tmp_path):
    prepared = _proposal_accepted_state(tmp_path)
    ordinary = _send(prepared.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert ordinary.state.pending_chat_requests[0].request_type == "evidence_execution_authority"

    resolved = _send(ordinary.state, "Yes, record approval for a future bounded execution gate.", tmp_path)
    authorities = _records(resolved.state, "evidence_execution_authorities")
    assert len(authorities) == 1

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_execution_authorities") == authorities
    duplicate = _send(restored, "Yes, record approval for a future bounded execution gate.", tmp_path)
    assert len(_records(duplicate.state, "evidence_execution_authorities")) == 1
    assert duplicate.intent.intent_type == "ordinary_conversation"
