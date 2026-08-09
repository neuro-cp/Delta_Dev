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


def _authority_ready_state(tmp_path, scenario, clarification):
    state = start_or_restore_runtime(tmp_path)
    started = _send(state, GOAL, tmp_path)
    framed = _send(started.state, scenario, tmp_path)
    refined = _send(framed.state, clarification, tmp_path)
    granted = _send(refined.state, "Yes, but only a local fixture.", tmp_path)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    assert accepted.state.pending_chat_requests[0].request_type == "evidence_execution_authority"
    return accepted


def _plan_ready_state(tmp_path, scenario=FINANCE, clarification="Assume losing more than 10% over six months is unacceptable."):
    authority_ready = _authority_ready_state(tmp_path, scenario, clarification)
    result = _send(authority_ready.state, "Yes, record approval for a future bounded execution gate.", tmp_path)
    assert result.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return result


def test_approved_execution_authority_creates_one_non_executing_plan(tmp_path):
    graph_before = load_graph(tmp_path)
    result = _plan_ready_state(tmp_path)
    plans = _records(result.state, "evidence_fixture_execution_plans")
    authorities = _records(result.state, "evidence_execution_authorities")
    proposal = _records(result.state, "evidence_next_operation_proposals")[0]
    disposition = _records(result.state, "evidence_next_operation_dispositions")[0]

    assert len(plans) == 1
    plan = plans[0]
    assert plan["status"] == "surfaced"
    assert plan["source_evidence_request_id"] == proposal["source_evidence_request_id"]
    assert plan["source_evidence_authorization_id"] == proposal["source_evidence_authorization_id"]
    assert plan["source_evidence_next_operation_proposal_id"] == proposal["evidence_next_operation_proposal_id"]
    assert plan["source_evidence_next_operation_disposition_id"] == disposition["evidence_next_operation_disposition_id"]
    assert plan["source_evidence_execution_authority_id"] == authorities[0]["evidence_execution_authority_id"]
    assert plan["may_execute_now"] is False
    assert plan["execution_requires_future_gate"] is True
    assert "plan only" in result.reply.lower()
    assert "cannot execute in this phase" in result.reply.lower()

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_plan_types_cover_market_fixture_and_operations_without_execution(tmp_path):
    finance = _plan_ready_state(tmp_path / "finance")
    finance_plan = _records(finance.state, "evidence_fixture_execution_plans")[0]
    assert finance_plan["evidence_source_class"] == "market_source_context_plan_only"
    assert "no trade" in " ".join(finance_plan["proof_requirements"]).lower()

    cyber = _plan_ready_state(
        tmp_path / "cyber",
        CYBER,
        "This is my local owned training fixture.",
    )
    cyber_plan = _records(cyber.state, "evidence_fixture_execution_plans")[0]
    assert cyber_plan["evidence_source_class"] == "owned_fixture_read_only_plan"
    assert "no payloads" in " ".join(cyber_plan["proof_requirements"]).lower()
    assert "no file read" in cyber.reply.lower() or "do not gather evidence" in cyber.reply.lower()

    ops = _plan_ready_state(
        tmp_path / "ops",
        OPERATIONS,
        "I do not know the pump ETA yet.",
    )
    ops_plan = _records(ops.state, "evidence_fixture_execution_plans")[0]
    assert ops_plan["evidence_source_class"] == "bounded_operational_status_plan"
    assert "no contact" in " ".join(ops_plan["proof_requirements"]).lower()


def test_declined_deferred_context_and_unclear_authority_create_no_plan(tmp_path):
    cases = (
        ("No, do not record execution authority.", "declined", False),
        ("Not now; leave it open.", "deferred", False),
        ("The future source should be a hypothetical table, not live market data.", "context_provided", False),
        ("Maybe, it depends.", "semantic_evidence_execution_authority_clarification", True),
    )
    for response, expected, pending in cases:
        root = tmp_path / expected
        prepared = _authority_ready_state(root, FINANCE, "Assume losing more than 10% over six months is unacceptable.")
        result = _send(prepared.state, response, root)
        assert not _records(result.state, "evidence_fixture_execution_plans")
        if pending:
            assert result.intent.intent_type == expected
            assert result.state.pending_chat_requests[0].request_type == "evidence_execution_authority"
        else:
            assert result.intent.intent_type == "semantic_evidence_execution_authority_record"
            assert _records(result.state, "evidence_execution_authorities")[0]["operator_decision"] == expected
            assert not result.state.pending_chat_requests


def test_plan_operator_disposition_updates_same_plan_without_execution(tmp_path):
    prepared = _plan_ready_state(tmp_path)
    request = prepared.state.pending_chat_requests[0]
    plan = _records(prepared.state, "evidence_fixture_execution_plans")[0]
    result = _send(prepared.state, "Yes, record this bounded plan.", tmp_path)
    plans = _records(result.state, "evidence_fixture_execution_plans")

    assert result.intent.intent_type == "semantic_evidence_fixture_execution_plan_update"
    assert len(plans) == 1
    assert plans[0]["evidence_fixture_execution_plan_id"] == plan["evidence_fixture_execution_plan_id"]
    assert plans[0]["status"] == "accepted_pending_execution_gate"
    assert plans[0]["may_execute_now"] is False
    assert plans[0]["execution_requires_future_gate"] is True
    assert not result.state.pending_chat_requests
    assert result.state.resolved_chat_requests[-1].request_id == request.request_id
    assert "has not run" in result.reply.lower()


def test_plan_unclear_restart_and_ordinary_chat_are_safe(tmp_path):
    prepared = _plan_ready_state(tmp_path)
    request = prepared.state.pending_chat_requests[0]
    unclear = _send(prepared.state, "Maybe, it depends.", tmp_path)
    assert unclear.intent.intent_type == "semantic_evidence_fixture_execution_plan_clarification"
    assert unclear.state.pending_chat_requests[0].request_id == request.request_id
    assert _records(unclear.state, "evidence_fixture_execution_plans")[0]["status"] == "surfaced"

    ordinary = _send(unclear.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert ordinary.state.pending_chat_requests[0].request_id == request.request_id

    accepted = _send(ordinary.state, "Yes, record this bounded plan.", tmp_path)
    plans = _records(accepted.state, "evidence_fixture_execution_plans")
    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_fixture_execution_plans") == plans
    duplicate = _send(restored, "Yes, record this bounded plan.", tmp_path)
    assert len(_records(duplicate.state, "evidence_fixture_execution_plans")) == 1
    assert duplicate.intent.intent_type == "ordinary_conversation"
