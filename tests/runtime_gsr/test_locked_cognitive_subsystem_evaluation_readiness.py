import json
import os
import socket
import subprocess
import urllib.request

import pytest

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.evidence_bound_analysis import (
    compile_adaptive_precondition_selection,
    compile_long_horizon_self_correction_candidates,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph
from orchestration.runtime.semantic_problem_modeling import compile_semantic_problem_frame


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement or a calculable fixture need, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
FINANCE_50 = "Correction: my account is 50% tech funds, 40% cash, and 10% small-cap value. The earlier 70% allocation was wrong, and I remain worried about AI stocks dropping over six months."
PHYSICS_30 = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."
PHYSICS_45 = "Correction: the same 5 kg block slides down a frictionless 45-degree incline. I want the acceleration."
FINANCE_RETRACTION = "Retraction: ignore that correction; the original account is 70% aggressive tech funds, 20% cash, and 10% small-cap value, and it was correct. I remain worried about AI stocks dropping over six months."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
CYBER = "A request parameter is appended into a SQL command before execution."
HEALTH = "I have an itchy rash for two days and I am worried it may be spreading. Should I seek care?"
LEGAL = "A collection agency says I owe a $1,200 balance. I dispute it and do not know which state rules apply."
GENERIC = "The billing system is failing after an update, but no error details or owner are available."
GENERIC_RESOLVED = "The billing system is failing after an update, but we now know the error is a database timeout and the platform team owns it."


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _one_record(state, key):
    records = _records(state, key)
    assert len(records) == 1
    return records[0]


def _canonical(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _graph_snapshot(root):
    graph = load_graph(root)
    return (
        tuple(graph.experiences),
        tuple(graph.claim_versions),
        tuple(graph.packets),
        tuple(graph.reviews),
        tuple(graph.admissions),
    )


def _route(state):
    return _one_record(state, "semantic_problem_frames")["capability_route_candidate"]


def _precondition(state):
    objective = state.active_objective
    assert objective is not None
    selection = objective.provenance.get("adaptive_precondition_selection")
    assert isinstance(selection, dict)
    return selection


def _correction(state, correction_type):
    matches = [
        record
        for record in _records(state, "long_horizon_self_correction_candidates")
        if record.get("correction_type") == correction_type
    ]
    assert len(matches) == 1
    return matches[0]


def _correction_effect(state, effect_type):
    matches = [
        record
        for record in _records(state, "long_horizon_correction_effects")
        if record.get("effect_type") == effect_type
    ]
    assert len(matches) == 1
    return matches[0]


def _controlled_lineage(state):
    return {
        "evidence_minimal_fixture_results": _records(state, "evidence_minimal_fixture_results"),
        "analysis_refinements": tuple(
            record
            for record in _records(state, "analysis_refinements")
            if record.get("status") == "controlled_fixture_refinement"
        ),
        "internal_work_selections": tuple(
            record
            for record in _records(state, "internal_work_selections")
            if record.get("source_evidence_minimal_fixture_result_id")
        ),
    }


def _plan_ready_state(root, scenario, clarification, goal=GOAL):
    started = _send(start_or_restore_runtime(root), goal, root)
    framed = _send(started.state, scenario, root)
    refined = _send(framed.state, clarification, root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _closed_loop_state(root, scenario, clarification, goal=GOAL):
    ready = _plan_ready_state(root, scenario, clarification, goal=goal)
    return _send(ready.state, "Yes, record this bounded plan.", root)


def _controlled_refinement(state):
    matches = [
        record
        for record in _records(state, "analysis_refinements")
        if record.get("status") == "controlled_fixture_refinement"
    ]
    assert len(matches) == 1
    return matches[0]


def _controlled_selection(state, refinement):
    matches = [
        record
        for record in _records(state, "internal_work_selections")
        if record.get("source_refinement_id") == refinement["refinement_id"]
        and record.get("status") == "selected_record_only"
    ]
    assert len(matches) == 1
    return matches[0]


def _assert_no_controlled_completion(state):
    assert not _records(state, "evidence_minimal_fixture_results")
    assert not [
        record
        for record in _records(state, "analysis_refinements")
        if record.get("status") == "controlled_fixture_refinement"
    ]
    assert not [
        record
        for record in _records(state, "internal_work_selections")
        if record.get("source_evidence_minimal_fixture_result_id")
    ]


def test_finance_full_path_composes_frame_route_correction_and_controlled_loop(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    completed = _closed_loop_state(
        tmp_path,
        FINANCE,
        "Assume losing more than 10% over six months is unacceptable.",
    )

    route = _route(completed.state)
    result = _one_record(completed.state, "evidence_minimal_fixture_results")
    refinement = _controlled_refinement(completed.state)
    selection = _controlled_selection(completed.state, refinement)
    correction = _correction(completed.state, "completed_positive_loop")

    assert route["route_name"] == "finance_controlled_fixture"
    assert route["decision"] == "eligible"
    assert "-11.3%" in result["deterministic_output"]
    assert correction["source_result_ids"] == [result["evidence_minimal_fixture_result_id"]]
    assert correction["may_execute_now"] is False
    assert selection["may_execute_now"] is False
    assert _precondition(completed.state)["precondition_state"] == "completed_stable"
    assert _graph_snapshot(tmp_path) == graph_before


def test_physics_full_path_composes_frame_route_correction_and_controlled_loop(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    completed = _closed_loop_state(tmp_path, PHYSICS_30, "A numeric result is most useful.")

    route = _route(completed.state)
    result = _one_record(completed.state, "evidence_minimal_fixture_results")
    refinement = _controlled_refinement(completed.state)
    correction = _correction(completed.state, "completed_positive_loop")

    assert route["route_name"] == "physics_deterministic_calculation"
    assert route["decision"] == "eligible"
    assert "4.9 m/s^2" in result["deterministic_output"]
    assert refinement["source_evidence_minimal_fixture_result_id"] == result["evidence_minimal_fixture_result_id"]
    assert correction["source_result_ids"] == [result["evidence_minimal_fixture_result_id"]]
    assert _precondition(completed.state)["precondition_state"] == "completed_stable"
    assert _graph_snapshot(tmp_path) == graph_before


def test_locked_precondition_ladder_requires_each_existing_authority_boundary(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    framed = _send(started.state, FINANCE, tmp_path)
    refined = _send(framed.state, "Assume losing more than 10% over six months is unacceptable.", tmp_path)
    granted = _send(refined.state, "Yes, but only a local fixture.", tmp_path)
    proposal_accepted = _send(granted.state, "Yes, keep that proposal ready.", tmp_path)
    authority = _send(proposal_accepted.state, "Yes, record approval for a future bounded execution gate.", tmp_path)

    assert _precondition(framed.state)["precondition_state"] == "eligible_needs_permission"
    assert _precondition(granted.state)["precondition_state"] == "permission_granted_needs_proposal_or_authority"
    assert _precondition(authority.state)["precondition_state"] == "authority_exists_needs_plan_acceptance"
    assert not _records(authority.state, "evidence_minimal_fixture_results")
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"

    objective = authority.state.active_objective
    assert objective is not None
    accepted_plan = {
        **dict(_one_record(authority.state, "evidence_fixture_execution_plans")),
        "status": "accepted_pending_execution_gate",
    }
    projection = compile_adaptive_precondition_selection(
        objective_id=objective.objective_id,
        semantic_frames=_records(authority.state, "semantic_problem_frames"),
        evidence_requests=_records(authority.state, "evidence_requests"),
        evidence_authorizations=_records(authority.state, "evidence_authorizations"),
        evidence_next_operation_proposals=_records(authority.state, "evidence_next_operation_proposals"),
        evidence_execution_authorities=_records(authority.state, "evidence_execution_authorities"),
        evidence_fixture_execution_plans=(accepted_plan,),
        analyses=_records(authority.state, "evidence_bound_analyses"),
    )
    assert projection is not None
    assert projection.precondition_state == "accepted_plan_ready_nonexecuting"
    assert projection.may_execute_now is False
    assert not _records(authority.state, "evidence_minimal_fixture_results")
    assert _graph_snapshot(tmp_path) == graph_before


@pytest.mark.parametrize(
    ("source", "route_name", "forbidden_terms"),
    (
        (OPERATIONS, "operations_blocked_external_dependency", ("customer", "external action")),
        (CYBER, "defensive_cyber_blocked_file_or_scan_boundary", ("payload", "repository read", "local file read")),
    ),
)
def test_unsafe_domains_remain_blocked_without_controlled_execution(tmp_path, source, route_name, forbidden_terms):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, source, tmp_path)

    route = _route(result.state)
    correction = _correction(result.state, "blocked_external_boundary")
    forbidden = " ".join((*correction["forbidden_actions"], *route["forbidden_actions"])).lower()
    assert route["route_name"] == route_name
    assert route["decision"] == "blocked"
    assert correction["may_execute_now"] is False
    assert correction["may_route_next"] is False
    assert _precondition(result.state)["precondition_state"] == "blocked_safety_boundary"
    assert all(term in forbidden for term in forbidden_terms)
    _assert_no_controlled_completion(result.state)
    assert _graph_snapshot(tmp_path) == graph_before


@pytest.mark.parametrize(
    ("source", "route_name", "required_limit"),
    (
        (HEALTH, "health_info_safe_response", "does not diagnose"),
        (LEGAL, "legal_financial_risk_safe_response", "not legal advice"),
        (GENERIC, "generic_structured_problem", "specialist"),
    ),
)
def test_safe_and_generic_domains_preserve_clarify_only_posture(tmp_path, source, route_name, required_limit):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, source, tmp_path)

    frame = _one_record(result.state, "semantic_problem_frames")["semantic_input_frame"]
    route = _route(result.state)
    correction = _correction(result.state, "unsupported_to_clarify")
    assert route["route_name"] == route_name
    assert route["decision"] == "clarify"
    assert correction["may_execute_now"] is False
    assert _precondition(result.state)["precondition_state"] == "clarify_needed"
    assert "clarification" in correction["corrected_or_current_state"]
    assert required_limit in " ".join(frame["limitations"]).lower()
    _assert_no_controlled_completion(result.state)
    assert not result.state.pending_chat_requests
    assert _graph_snapshot(tmp_path) == graph_before


def test_supersession_preserves_both_physics_frames_without_recomputation(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    first = _send(started.state, PHYSICS_30, tmp_path)
    corrected = _send(first.state, PHYSICS_45, tmp_path)

    correction = _correction(corrected.state, "contradiction_or_supersession")
    frames = _records(corrected.state, "semantic_problem_frames")
    assert len(frames) == 2
    assert correction["source_frame_ids"] == [frames[0]["frame_id"], frames[1]["frame_id"]]
    assert "30 degrees" in correction["prior_state"]
    assert "45 degrees" in correction["corrected_or_current_state"]
    _assert_no_controlled_completion(corrected.state)
    assert _graph_snapshot(tmp_path) == graph_before


def test_locked_physics_stale_suppression_replaces_completed_posture_without_recomputation(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    completed = _closed_loop_state(tmp_path, PHYSICS_30, "A numeric result is most useful.")
    prior_lineage = _controlled_lineage(completed.state)
    corrected = _send(completed.state, PHYSICS_45, tmp_path)

    effect = _correction_effect(corrected.state, "stale_suppression")
    arbitration = corrected.state.active_objective.provenance["adaptive_route_arbitration"]
    assert effect["affected_result_ids"]
    assert effect["affected_refinement_ids"]
    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_correction_effect_id"] == effect["effect_id"]
    assert arbitration["may_execute_now"] is False
    assert _precondition(corrected.state)["precondition_state"] == "completed_stale_needs_new_authorized_cycle"
    assert _controlled_lineage(corrected.state) == prior_lineage
    assert _graph_snapshot(tmp_path) == graph_before


def test_locked_finance_stale_suppression_replaces_completed_posture_without_fallback(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    completed = _closed_loop_state(tmp_path, FINANCE, "Assume losing more than 10% over six months is unacceptable.")
    prior_lineage = _controlled_lineage(completed.state)
    corrected = _send(completed.state, FINANCE_50, tmp_path)

    effect = _correction_effect(corrected.state, "stale_suppression")
    arbitration = corrected.state.active_objective.provenance["adaptive_route_arbitration"]
    assert "infer replacement weights" in effect["selected_nonexecuting_posture"].lower()
    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_correction_effect_id"] == effect["effect_id"]
    assert _precondition(corrected.state)["precondition_state"] == "completed_stale_needs_new_authorized_cycle"
    assert _controlled_lineage(corrected.state) == prior_lineage
    assert _graph_snapshot(tmp_path) == graph_before


def test_locked_resolved_context_and_blocked_effects_remain_nonexecuting(tmp_path):
    graph_before = _graph_snapshot(tmp_path / "resolved")
    started = _send(start_or_restore_runtime(tmp_path / "resolved"), GOAL, tmp_path / "resolved")
    missing = _send(started.state, GENERIC, tmp_path / "resolved")
    resolved = _send(missing.state, GENERIC_RESOLVED, tmp_path / "resolved")
    resolved_effect = _correction_effect(resolved.state, "resolved_context")
    assert resolved.state.active_objective.provenance["adaptive_route_arbitration"]["selected_correction_effect_id"] == resolved_effect["effect_id"]
    assert resolved_effect["may_execute_now"] is False
    assert _precondition(resolved.state)["precondition_state"] == "clarify_needed"
    _assert_no_controlled_completion(resolved.state)
    assert _graph_snapshot(tmp_path / "resolved") == graph_before

    blocked_started = _send(start_or_restore_runtime(tmp_path / "blocked"), GOAL, tmp_path / "blocked")
    blocked = _send(blocked_started.state, CYBER, tmp_path / "blocked")
    after_context = _send(blocked.state, "No additional fixture or repository context is available today.", tmp_path / "blocked")
    blocked_effect = _correction_effect(after_context.state, "blocked_persists")
    assert after_context.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "blocked"
    assert blocked_effect["may_execute_now"] is False
    _assert_no_controlled_completion(after_context.state)


def test_locked_stable_completion_and_mixed_safety_ordering_do_not_duplicate_work(tmp_path):
    completed = _closed_loop_state(tmp_path, FINANCE, "Assume losing more than 10% over six months is unacceptable.")
    stable_effect = _correction_effect(completed.state, "stable_completed")
    assert completed.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "completed"
    assert stable_effect["may_execute_now"] is False
    prior_lineage = _controlled_lineage(completed.state)

    mixed = _send(completed.state, OPERATIONS, tmp_path)
    arbitration = mixed.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "blocked"
    assert arbitration["may_execute_now"] is False
    assert _precondition(mixed.state)["precondition_state"] == "blocked_safety_boundary"
    assert _correction_effect(mixed.state, "blocked_persists")["may_execute_now"] is False
    assert _controlled_lineage(mixed.state) == prior_lineage


def test_malformed_authority_path_fails_closed_without_fallback_or_selection(tmp_path):
    ready = _plan_ready_state(
        tmp_path,
        FINANCE,
        "Assume losing more than 10% over six months is unacceptable.",
    )
    objective = ready.state.active_objective
    assert objective is not None
    plan = dict(_one_record(ready.state, "evidence_fixture_execution_plans"))
    analysis = dict(_one_record(ready.state, "evidence_bound_analyses"))
    malformed_plan = {**plan, "status": "accepted_pending_execution_gate", "may_execute_now": False}
    malformed_analysis = {**analysis, "source_text": "My account is 70% aggressive tech funds and cash is variable."}

    corrections = compile_long_horizon_self_correction_candidates(
        objective_id=objective.objective_id,
        semantic_frames=_records(ready.state, "semantic_problem_frames"),
        analyses=(analysis,),
        rejected_fixture_inputs=((malformed_plan, malformed_analysis),),
    )
    failed = [record.as_record() for record in corrections if record.correction_type == "malformed_to_fail_closed"]
    assert len(failed) == 1
    assert "no fixture result" in failed[0]["corrected_or_current_state"]
    assert "fallback data" in " ".join(failed[0]["forbidden_actions"]).lower()
    _assert_no_controlled_completion(ready.state)


def test_ordinary_chat_remains_unframed_and_does_not_create_cognitive_records(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    ordinary = _send(started.state, "What is 2 + 2?", tmp_path)

    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    for key in (
        "semantic_problem_frames",
        "long_horizon_self_correction_candidates",
        "long_horizon_correction_effects",
        "evidence_minimal_fixture_results",
        "analysis_refinements",
    ):
        assert not _records(ordinary.state, key)
    assert "adaptive_route_arbitration" not in ordinary.state.active_objective.provenance
    assert "adaptive_precondition_selection" not in ordinary.state.active_objective.provenance


def test_source_objective_isolation_and_restart_replay_are_exact_once(tmp_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = _closed_loop_state(
        first_root,
        "Account alpha is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months.",
        "Assume losing more than 10% over six months is unacceptable.",
    )
    second = _closed_loop_state(
        second_root,
        PHYSICS_30,
        "A numeric result is most useful.",
        goal=GOAL + " Use the physics scenario only.",
    )
    first_objective = first.state.active_objective
    second_objective = second.state.active_objective
    assert first_objective is not None and second_objective is not None
    assert first_objective.objective_id != second_objective.objective_id
    assert _one_record(first.state, "evidence_minimal_fixture_results")["fixture_kind"] != _one_record(second.state, "evidence_minimal_fixture_results")["fixture_kind"]

    keys = (
        "semantic_problem_frames",
        "long_horizon_self_correction_candidates",
        "long_horizon_correction_effects",
        "evidence_minimal_fixture_results",
        "analysis_refinements",
        "internal_work_selections",
    )
    expected = {key: _canonical(_records(first.state, key)) for key in keys}
    replayed = _send(first.state, "Yes, record this bounded plan.", first_root)
    restored = start_or_restore_runtime(first_root)
    assert {key: _canonical(_records(replayed.state, key)) for key in keys} == expected
    assert {key: _canonical(_records(restored, key)) for key in keys} == expected
    assert _canonical(replayed.state.active_objective.provenance["adaptive_route_arbitration"]) == _canonical(restored.active_objective.provenance["adaptive_route_arbitration"])
    assert _canonical(replayed.state.active_objective.provenance["adaptive_precondition_selection"]) == _canonical(restored.active_objective.provenance["adaptive_precondition_selection"])


def test_locked_compound_and_mixed_preconditions_use_safety_first_ordering(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    compound = _send(started.state, f"{FINANCE} {HEALTH}", tmp_path)

    frames = _records(compound.state, "semantic_problem_frames")
    assert len(frames) == 2
    assert {frame["semantic_input_frame"]["domain_guess"] for frame in frames} == {
        "finance_portfolio_risk",
        "health_information_safety",
    }
    assert _precondition(compound.state)["precondition_state"] == "clarify_needed"
    _assert_no_controlled_completion(compound.state)

    completed = _closed_loop_state(
        tmp_path / "mixed",
        FINANCE,
        "Assume losing more than 10% over six months is unacceptable.",
    )
    stale = _send(completed.state, FINANCE_50, tmp_path / "mixed")
    assert _precondition(stale.state)["precondition_state"] == "completed_stale_needs_new_authorized_cycle"
    mixed = _send(stale.state, f"{OPERATIONS} {HEALTH} {PHYSICS_30}", tmp_path / "mixed")
    assert _precondition(mixed.state)["precondition_state"] == "blocked_safety_boundary"
    assert len(_records(mixed.state, "evidence_minimal_fixture_results")) == 1
    assert _graph_snapshot(tmp_path) == graph_before


def test_locked_precondition_consumes_latest_retraction_and_partial_correction_postures(tmp_path):
    completed = _closed_loop_state(
        tmp_path / "finance",
        FINANCE,
        "Assume losing more than 10% over six months is unacceptable.",
    )
    superseded = _send(completed.state, FINANCE_50, tmp_path / "finance")
    assert _precondition(superseded.state)["precondition_state"] == "completed_stale_needs_new_authorized_cycle"
    retracted = _send(superseded.state, FINANCE_RETRACTION, tmp_path / "finance")
    assert _precondition(retracted.state)["precondition_state"] == "completed_stable"

    generic_started = _send(start_or_restore_runtime(tmp_path / "generic"), GOAL, tmp_path / "generic")
    missing = _send(generic_started.state, GENERIC, tmp_path / "generic")
    resolved = _send(missing.state, GENERIC_RESOLVED, tmp_path / "generic")
    assert _precondition(resolved.state)["precondition_state"] == "clarify_needed"


def test_locked_battery_reaches_no_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    completed = _closed_loop_state(
        tmp_path,
        FINANCE,
        "Assume losing more than 10% over six months is unacceptable.",
    )
    assert _one_record(completed.state, "evidence_minimal_fixture_results")["fixture_kind"] == "in_memory_hypothetical_portfolio_drawdown_table"
