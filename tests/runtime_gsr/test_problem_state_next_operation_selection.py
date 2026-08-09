from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)


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


def _closed_loop_state(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    started = _send(state, GOAL, tmp_path)
    framed = _send(started.state, FINANCE, tmp_path)
    refined = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", tmp_path)
    granted = _send(refined.state, "Yes, but only a local fixture.", tmp_path)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", tmp_path)
    return _send(authority.state, "Yes, record this bounded plan.", tmp_path)


def test_problem_state_selects_one_existing_internal_work_next_operation_record_only(tmp_path):
    result = _closed_loop_state(tmp_path)
    fixture = _records(result.state, "evidence_minimal_fixture_results")[0]
    selections = [
        item
        for item in _records(result.state, "internal_work_selections")
        if item.get("source_evidence_minimal_fixture_result_id") == fixture["evidence_minimal_fixture_result_id"]
    ]

    assert len(selections) == 1
    selection = selections[0]
    assert selection["status"] == "selected_record_only"
    assert selection["selection_scope"] == "record_only"
    assert selection["may_execute_now"] is False
    assert selection["selected_next_operation"] == "retain_fixture_context_and_wait_for_later_evidence_authority"
    assert selection["source_evidence_analysis_revision_candidate_id"] == fixture["source_evidence_analysis_revision_candidate_id"]
    assert not result.state.pending_chat_requests
    assert "next operation selected" in result.reply.lower()

    events = tuple(item for item in result.state.objective_progress if item.get("event") == "controlled_fixture_next_operation_selected")
    assert len(events) == 1
    assert events[0]["internal_work_selection_id"] == selection["internal_work_selection_id"]


def test_next_operation_selection_is_restart_exact_once_and_ordinary_chat_unchanged(tmp_path):
    result = _closed_loop_state(tmp_path)
    selections = _records(result.state, "internal_work_selections")
    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "internal_work_selections") == selections

    ordinary = _send(restored, "What is 2 + 2?", tmp_path)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert _records(ordinary.state, "internal_work_selections") == selections
