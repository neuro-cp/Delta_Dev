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


def _start(tmp_path):
    result = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    assert result.state.active_objective is not None
    return result.state


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _permission_ready_state(tmp_path, scenario, clarification):
    state = _start(tmp_path)
    framed = _send(state, scenario, tmp_path)
    assert framed.state.pending_chat_requests
    answered = _send(framed.state, clarification, tmp_path)
    assert answered.state.pending_chat_requests[0].request_type == "evidence_permission"
    return answered.state


def _finance_ready_state(tmp_path):
    return _permission_ready_state(
        tmp_path,
        FINANCE,
        "Assume losing more than 10% over six months is unacceptable.",
    )


def _grant_and_assert_proposal(state, tmp_path):
    graph_before = load_graph(tmp_path)
    permission_request = state.pending_chat_requests[0]
    result = _send(state, "Yes, but only a local fixture.", tmp_path)
    requests = _records(result.state, "evidence_requests")
    authorizations = _records(result.state, "evidence_authorizations")
    proposals = _records(result.state, "evidence_next_operation_proposals")

    assert result.intent.intent_type == "semantic_evidence_permission_authorization"
    assert len(requests) == 1
    assert len(authorizations) == 1
    assert len(proposals) == 1
    assert result.state.pending_chat_requests[0].request_type == "evidence_next_operation_proposal"
    assert result.state.pending_chat_requests[0].baseline_metrics["evidence_next_operation_proposal_id"] == proposals[0]["evidence_next_operation_proposal_id"]
    assert requests[0]["status"] == "granted_pending_separate_execution"
    assert authorizations[0]["status"] == "granted_pending_separate_execution"
    assert authorizations[0]["may_execute_now"] is False
    assert proposals[0]["source_evidence_request_id"] == requests[0]["evidence_permission_request_id"]
    assert proposals[0]["source_evidence_authorization_id"] == authorizations[0]["evidence_authorization_id"]
    assert proposals[0]["may_execute_now"] is False
    assert proposals[0]["status"] == "surfaced"
    assert "proposal only" in result.reply.lower()
    assert "cannot execute in this phase" in result.reply.lower()
    assert permission_request.request_id == result.state.resolved_chat_requests[-1].request_id

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions
    return result


def test_granted_finance_permission_creates_one_non_executing_proposal(tmp_path):
    result = _grant_and_assert_proposal(_finance_ready_state(tmp_path), tmp_path)
    proposal = _records(result.state, "evidence_next_operation_proposals")[0]

    assert proposal["proposed_operation_type"] == "finance_market_context_proposal_only"
    assert "market-data" in proposal["proposed_scope"]
    assert "no evidence gathering" in result.reply.lower()

    ordinary = _send(result.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert len(_records(ordinary.state, "evidence_next_operation_dispositions")) == 0


def test_granted_cyber_and_operations_permissions_create_scoped_proposals(tmp_path):
    cyber_ready = _permission_ready_state(
        tmp_path / "cyber",
        CYBER,
        "This is my local owned training fixture.",
    )
    cyber = _grant_and_assert_proposal(cyber_ready, tmp_path / "cyber")
    cyber_proposal = _records(cyber.state, "evidence_next_operation_proposals")[0]
    assert cyber_proposal["proposed_operation_type"] == "defensive_owned_fixture_read_only_proposal"
    assert "read-only" in cyber_proposal["proposed_scope"]

    ops_ready = _permission_ready_state(
        tmp_path / "ops",
        OPERATIONS,
        "I do not know the pump ETA yet.",
    )
    ops = _grant_and_assert_proposal(ops_ready, tmp_path / "ops")
    ops_proposal = _records(ops.state, "evidence_next_operation_proposals")[0]
    assert ops_proposal["proposed_operation_type"] == "bounded_operational_status_lookup_proposal"
    assert "status lookup" in ops_proposal["proposed_scope"]


def test_denied_deferred_context_and_unclear_do_not_create_proposals(tmp_path):
    cases = (
        ("No, keep it hypothetical.", "denied", False),
        ("Not now; leave the evidence open.", "deferred", False),
        ("The pump arrives Friday.", "operator_provided_context", False),
        ("Maybe, it depends.", "semantic_evidence_permission_clarification", True),
    )
    for response, expected, stays_pending in cases:
        root = tmp_path / expected
        state = _permission_ready_state(root, OPERATIONS, "I do not know the pump ETA yet.")
        result = _send(state, response, root)

        assert not _records(result.state, "evidence_next_operation_proposals")
        assert not _records(result.state, "evidence_next_operation_dispositions")
        if stays_pending:
            assert result.intent.intent_type == expected
            assert result.state.pending_chat_requests[0].request_type == "evidence_permission"
            assert not _records(result.state, "evidence_authorizations")
        else:
            assert result.intent.intent_type == "semantic_evidence_permission_authorization"
            assert _records(result.state, "evidence_authorizations")[0]["status"] == expected
            assert not result.state.pending_chat_requests


def test_proposal_disposition_binds_exact_request_without_execution_and_restarts(tmp_path):
    granted = _grant_and_assert_proposal(_finance_ready_state(tmp_path), tmp_path)
    proposal_request = granted.state.pending_chat_requests[0]
    proposal = _records(granted.state, "evidence_next_operation_proposals")[0]
    result = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    dispositions = _records(result.state, "evidence_next_operation_dispositions")
    proposals = _records(result.state, "evidence_next_operation_proposals")

    assert result.intent.intent_type == "semantic_evidence_next_operation_disposition"
    assert len(dispositions) == 1
    assert dispositions[0]["status"] == "accepted_pending_separate_execution"
    assert dispositions[0]["evidence_next_operation_proposal_id"] == proposal["evidence_next_operation_proposal_id"]
    assert dispositions[0]["source_evidence_request_id"] == proposal["source_evidence_request_id"]
    assert dispositions[0]["source_evidence_authorization_id"] == proposal["source_evidence_authorization_id"]
    assert dispositions[0]["may_execute_now"] is False
    assert proposals[0]["status"] == "accepted_pending_separate_execution"
    assert result.state.pending_chat_requests[0].request_type == "evidence_execution_authority"
    assert result.state.resolved_chat_requests[-1].request_id == proposal_request.request_id
    assert "no evidence gathering" in result.reply.lower()

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_next_operation_proposals") == proposals
    assert _records(restored, "evidence_next_operation_dispositions") == dispositions
    ordinary = _send(restored, "What is 2 + 2?", tmp_path)
    assert "4" in ordinary.reply
    assert len(_records(ordinary.state, "evidence_next_operation_proposals")) == 1
    assert len(_records(ordinary.state, "evidence_next_operation_dispositions")) == 1
