from dataclasses import replace

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import compile_evidence_fixture_dry_run_results
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


def _accepted_plan_state(tmp_path, scenario=FINANCE, clarification="Assume losing more than 10% over six months is unacceptable."):
    ready = _plan_ready_state(tmp_path, scenario, clarification)
    return _send(ready.state, "Yes, record this bounded plan.", tmp_path)


def test_accepted_plan_records_one_non_executing_dry_run_result(tmp_path):
    graph_before = load_graph(tmp_path)
    ready = _plan_ready_state(tmp_path)
    plan = _records(ready.state, "evidence_fixture_execution_plans")[0]
    result = _send(ready.state, "Yes, record this bounded plan.", tmp_path)
    plans = _records(result.state, "evidence_fixture_execution_plans")
    dry_runs = _records(result.state, "evidence_fixture_dry_run_results")

    assert result.intent.intent_type == "semantic_evidence_fixture_execution_plan_update"
    assert len(plans) == 1
    assert len(dry_runs) == 1
    dry_run = dry_runs[0]
    assert dry_run["source_plan_id"] == plan["evidence_fixture_execution_plan_id"]
    assert dry_run["source_execution_authority_id"] == plan["source_evidence_execution_authority_id"]
    assert dry_run["source_proposal_id"] == plan["source_evidence_next_operation_proposal_id"]
    assert dry_run["source_evidence_request_id"] == plan["source_evidence_request_id"]
    assert dry_run["source_evidence_authorization_id"] == plan["source_evidence_authorization_id"]
    assert dry_run["status"] == "dry_run_completed"
    assert dry_run["may_update_analysis"] is False
    assert dry_run["may_update_graph"] is False
    assert dry_run["requires_result_ingestion_gate"] is True
    assert not result.state.pending_chat_requests
    assert "dry-run result recorded" in result.reply.lower()
    assert "requires_result_ingestion_gate=true" in result.reply

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_dry_run_result_shapes_cover_market_fixture_and_operations(tmp_path):
    finance = _accepted_plan_state(tmp_path / "finance")
    finance_result = _records(finance.state, "evidence_fixture_dry_run_results")[0]
    assert finance_result["fixture_kind"] == "synthetic_market_context_blocked"
    assert "did not fetch prices" in finance_result["deterministic_result"].lower()
    assert "trading" in finance_result["proof_summary"].lower()

    cyber = _accepted_plan_state(
        tmp_path / "cyber",
        CYBER,
        "This is my local owned training fixture.",
    )
    cyber_result = _records(cyber.state, "evidence_fixture_dry_run_results")[0]
    assert cyber_result["fixture_kind"] == "synthetic_owned_fixture_inspection_blocked"
    assert "without reading a repository file" in cyber_result["deterministic_result"].lower()
    assert "payloads" in cyber_result["proof_summary"].lower()

    ops = _accepted_plan_state(
        tmp_path / "ops",
        OPERATIONS,
        "I do not know the pump ETA yet.",
    )
    ops_result = _records(ops.state, "evidence_fixture_dry_run_results")[0]
    assert ops_result["fixture_kind"] == "synthetic_operational_status_blocked"
    assert "did not contact people or systems" in ops_result["deterministic_result"].lower()
    assert "commitments" in ops_result["proof_summary"].lower()


def test_declined_deferred_context_and_unclear_plan_create_no_dry_run_result(tmp_path):
    cases = (
        ("No, do not record this plan.", "declined", False),
        ("Not now; leave it open.", "deferred", False),
        ("Use only an in-memory hypothetical table shape for this plan.", "context_provided", False),
        ("Maybe, it depends.", "semantic_evidence_fixture_execution_plan_clarification", True),
    )
    for response, expected, pending in cases:
        root = tmp_path / expected
        ready = _plan_ready_state(root)
        result = _send(ready.state, response, root)
        assert not _records(result.state, "evidence_fixture_dry_run_results")
        if pending:
            assert result.intent.intent_type == expected
            assert result.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
        else:
            assert result.intent.intent_type == "semantic_evidence_fixture_execution_plan_update"
            assert _records(result.state, "evidence_fixture_execution_plans")[0]["status"] == expected
            assert not result.state.pending_chat_requests


def test_dry_run_helper_rejects_missing_or_executable_plan_ids(tmp_path):
    accepted = _accepted_plan_state(tmp_path)
    plan = _records(accepted.state, "evidence_fixture_execution_plans")[0]
    objective_id = accepted.state.active_objective.objective_id

    missing_plan_id = {**dict(plan), "evidence_fixture_execution_plan_id": ""}
    executable = {**dict(plan), "may_execute_now": True}
    not_future_gate = {**dict(plan), "execution_requires_future_gate": False}
    pending = {**dict(plan), "status": "surfaced"}

    assert compile_evidence_fixture_dry_run_results(missing_plan_id, objective_id=objective_id) == ()
    assert compile_evidence_fixture_dry_run_results(executable, objective_id=objective_id) == ()
    assert compile_evidence_fixture_dry_run_results(not_future_gate, objective_id=objective_id) == ()
    assert compile_evidence_fixture_dry_run_results(pending, objective_id=objective_id) == ()


def test_dry_run_result_is_exactly_once_across_restart_and_repeat(tmp_path):
    accepted = _accepted_plan_state(tmp_path)
    dry_runs = _records(accepted.state, "evidence_fixture_dry_run_results")
    assert len(dry_runs) == 1

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_fixture_dry_run_results") == dry_runs

    duplicate = _send(restored, "Yes, record this bounded plan.", tmp_path)
    assert len(_records(duplicate.state, "evidence_fixture_dry_run_results")) == 1
    assert duplicate.intent.intent_type == "ordinary_conversation"


def test_pending_unrelated_plan_request_blocks_dry_run_lifecycle(tmp_path):
    ready = _plan_ready_state(tmp_path)
    objective = ready.state.active_objective
    assert objective is not None
    plan = _records(ready.state, "evidence_fixture_execution_plans")[0]
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
    assert _records(result.state, "evidence_fixture_execution_plans")[0]["evidence_fixture_execution_plan_id"] == plan["evidence_fixture_execution_plan_id"]
    assert any(item.get("event") == "evidence_fixture_dry_run_suppressed_existing_request" for item in result.state.objective_progress)


def test_ordinary_chat_stays_ordinary_before_and_after_dry_run(tmp_path):
    ready = _plan_ready_state(tmp_path)
    ordinary_before = _send(ready.state, "What is 2 + 2?", tmp_path)
    assert ordinary_before.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_before.reply
    assert ordinary_before.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    assert not _records(ordinary_before.state, "evidence_fixture_dry_run_results")

    accepted = _send(ordinary_before.state, "Yes, record this bounded plan.", tmp_path)
    ordinary_after = _send(accepted.state, "What is 2 + 2?", tmp_path)
    assert ordinary_after.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary_after.reply
    assert len(_records(ordinary_after.state, "evidence_fixture_dry_run_results")) == 1


def test_dry_run_result_blocks_execution_side_effect_classes(tmp_path):
    accepted = _accepted_plan_state(tmp_path)
    result = _records(accepted.state, "evidence_fixture_dry_run_results")[0]
    blocked = " ".join(result["blocked_actions"]).lower()

    assert "no repository file read" in blocked
    assert "no local filesystem read" in blocked
    assert "no network" in blocked
    assert "no model" in blocked
    assert "provider" in blocked
    assert "tool" in blocked
    assert "sandbox command execution" in blocked
    assert "no source mutation" in blocked
    assert "no graph truth mutation" in blocked
    assert "review" in blocked
    assert "admission" in blocked
    assert result["may_update_analysis"] is False
    assert result["may_update_graph"] is False
    assert result["requires_result_ingestion_gate"] is True
