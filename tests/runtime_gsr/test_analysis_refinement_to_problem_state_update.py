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


def test_controlled_refinement_updates_existing_internal_work_problem_posture_once(tmp_path):
    result = _closed_loop_state(tmp_path)
    fixture = _records(result.state, "evidence_minimal_fixture_results")[0]
    controlled = _records(result.state, "analysis_refinements")[-1]
    candidate = next(
        item
        for item in _records(result.state, "internal_work_candidates")
        if item.get("internal_work_candidate_id") == fixture["source_internal_work_candidate_id"]
    )

    assert candidate["status"] == "selected_next_operation_recorded"
    assert candidate["controlled_fixture_refinement_id"] == controlled["refinement_id"]
    assert candidate["source_evidence_minimal_fixture_result_id"] == fixture["evidence_minimal_fixture_result_id"]
    assert candidate["problem_state_status"] == "fixture_refined_live_evidence_still_unresolved"
    assert candidate["controlled_fixture_problem_state_update_id"]
    assert "live evidence unresolved" in candidate["safe_deterministic_next_step"].lower()

    events = tuple(item for item in result.state.objective_progress if item.get("event") == "controlled_fixture_problem_state_updated")
    assert len(events) == 1
    assert events[0]["controlled_fixture_problem_state_update_id"] == candidate["controlled_fixture_problem_state_update_id"]


def test_problem_state_update_is_restart_exact_once_without_external_side_effects(tmp_path):
    result = _closed_loop_state(tmp_path)
    candidates = _records(result.state, "internal_work_candidates")
    selections = _records(result.state, "internal_work_selections")
    updates = tuple(item for item in result.state.objective_progress if item.get("event") == "controlled_fixture_problem_state_updated")

    restored = start_or_restore_runtime(tmp_path)
    assert _records(restored, "internal_work_candidates") == candidates
    assert _records(restored, "internal_work_selections") == selections
    assert tuple(item for item in restored.objective_progress if item.get("event") == "controlled_fixture_problem_state_updated") == updates
    assert not restored.pending_chat_requests
