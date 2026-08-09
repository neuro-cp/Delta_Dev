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


def _send(state, text, tmp_path):
    return handle_conversational_message(state, text, runtime_root=tmp_path, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _plan_ready_state(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    started = _send(state, GOAL, tmp_path)
    framed = _send(started.state, FINANCE, tmp_path)
    refined = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", tmp_path)
    granted = _send(refined.state, "Yes, but only a local fixture.", tmp_path)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", tmp_path)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _closed_loop_state(tmp_path):
    ready = _plan_ready_state(tmp_path)
    return _send(ready.state, "Yes, record this bounded plan.", tmp_path)


def test_accepted_plan_records_one_bounded_in_memory_fixture_result(tmp_path):
    ready = _plan_ready_state(tmp_path)
    graph_before = load_graph(tmp_path)
    result = _send(ready.state, "Yes, record this bounded plan.", tmp_path)

    plan = _records(result.state, "evidence_fixture_execution_plans")[0]
    revision = _records(result.state, "evidence_analysis_revision_candidates")[0]
    fixture_results = _records(result.state, "evidence_minimal_fixture_results")
    assert len(fixture_results) == 1
    fixture = fixture_results[0]
    routed = next(
        item
        for item in _records(result.state, "internal_work_candidates")
        if item.get("internal_work_candidate_id") == fixture["source_internal_work_candidate_id"]
    )

    assert fixture["fixture_kind"] == "in_memory_hypothetical_portfolio_drawdown_table"
    assert fixture["source_plan_id"] == plan["evidence_fixture_execution_plan_id"]
    assert fixture["source_evidence_analysis_revision_candidate_id"] == revision["evidence_analysis_revision_candidate_id"]
    assert fixture["source_internal_work_candidate_id"] == routed["internal_work_candidate_id"]
    assert "-11.3%" in fixture["deterministic_output"]
    assert fixture["may_update_analysis"] is False
    assert fixture["may_update_problem_state"] is False
    assert fixture["may_update_graph"] is False
    assert fixture["requires_analysis_refinement_gate"] is True
    assert fixture["status"] == "minimal_fixture_completed"
    assert "controlled in-memory fixture result recorded" in result.reply.lower()

    blocked = " ".join(fixture["blocked_actions"]).lower()
    for forbidden in ("repository file read", "local filesystem read", "network", "model", "provider", "tool", "sandbox", "graph truth", "external action"):
        assert forbidden in blocked

    graph_after = load_graph(tmp_path)
    assert len(graph_after.experiences) == len(graph_before.experiences)
    assert len(graph_after.claim_versions) == len(graph_before.claim_versions)
    assert not graph_after.packets
    assert not graph_after.reviews
    assert not graph_after.admissions


def test_fixture_compiler_rejects_missing_or_broadened_execution_inputs(tmp_path):
    result = _closed_loop_state(tmp_path)
    objective = result.state.active_objective
    assert objective is not None
    plan = _records(result.state, "evidence_fixture_execution_plans")[0]
    analysis = _records(result.state, "evidence_bound_analyses")[0]
    revision = _records(result.state, "evidence_analysis_revision_candidates")[0]
    routed = _records(result.state, "internal_work_candidates")[0]

    assert compile_evidence_minimal_fixture_results(
        {**dict(plan), "evidence_fixture_execution_plan_id": ""},
        objective_id=objective.objective_id,
        source_analysis=analysis,
        source_revision_candidate=revision,
        source_internal_work_candidate=routed,
    ) == ()
    assert compile_evidence_minimal_fixture_results(
        {**dict(plan), "may_execute_now": True},
        objective_id=objective.objective_id,
        source_analysis=analysis,
        source_revision_candidate=revision,
        source_internal_work_candidate=routed,
    ) == ()
    assert compile_evidence_minimal_fixture_results(
        {**dict(plan), "evidence_source_class": "owned_fixture_read_only_plan"},
        objective_id=objective.objective_id,
        source_analysis=analysis,
        source_revision_candidate=revision,
        source_internal_work_candidate=routed,
    ) == ()


def test_declined_deferred_or_context_plan_creates_no_minimal_fixture_result(tmp_path):
    for label, response in (
        ("declined", "No, do not record this plan."),
        ("deferred", "Not now; leave it open."),
        ("context", "Use only an in-memory hypothetical table shape for this plan."),
    ):
        ready = _plan_ready_state(tmp_path / label)
        result = _send(ready.state, response, tmp_path / label)
        assert not _records(result.state, "evidence_minimal_fixture_results")
        assert not _records(result.state, "analysis_refinements")[1:]


def test_minimal_fixture_result_is_restart_exact_once_and_ordinary_chat_stays_ordinary(tmp_path):
    result = _closed_loop_state(tmp_path)
    fixture_results = _records(result.state, "evidence_minimal_fixture_results")
    assert len(fixture_results) == 1

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "evidence_minimal_fixture_results") == fixture_results
    duplicate = _send(restored, "Yes, record this bounded plan.", tmp_path)
    assert len(_records(duplicate.state, "evidence_minimal_fixture_results")) == 1
    assert duplicate.intent.intent_type == "ordinary_conversation"

    ordinary = _send(duplicate.state, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert len(_records(ordinary.state, "evidence_minimal_fixture_results")) == 1
