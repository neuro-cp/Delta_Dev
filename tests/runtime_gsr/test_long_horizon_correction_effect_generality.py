import json

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement or a calculable fixture need, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
PHYSICS_30 = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."
PHYSICS_45 = "Correction: the same 5 kg block slides down a frictionless 45-degree incline. I want the acceleration."
PHYSICS_60 = "Correction: the same 5 kg block slides down a frictionless 60-degree incline. I want the acceleration."
FINANCE_70 = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months."
FINANCE_50 = "Correction: my account is 50% tech funds, 40% cash, and 10% small-cap value. The earlier 70% allocation was wrong, and I remain worried about AI stocks dropping over six months."
FINANCE_RETRACTION = "Retraction: ignore that correction; the original account is 70% aggressive tech funds, 20% cash, and 10% small-cap value, and it was correct. I remain worried about AI stocks dropping over six months."
HEALTH = "I have an itchy rash for two days and I am worried it may be spreading. Should I seek care?"
HEALTH_CONTEXT = "I have an itchy rash for two days, I now know I have no fever, and it is still spreading. Should I seek care?"
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
CYBER = "A request parameter is appended into a SQL command before execution."
GENERIC_MISSING = "The billing system is failing after an update, but no error details or owner are available."
GENERIC_RESOLVED = "The billing system is failing after an update, but we now know the error is a database timeout and the platform team owns it."


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _consolidation(state):
    value = state.active_objective.provenance.get("long_horizon_correction_effect_consolidation")
    assert isinstance(value, dict)
    return value


def _canonical(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _graph_snapshot(root):
    graph = load_graph(root)
    return (tuple(graph.experiences), tuple(graph.claim_versions), tuple(graph.packets), tuple(graph.reviews), tuple(graph.admissions))


def _plan_ready_state(root, scenario, clarification):
    started = _send(start_or_restore_runtime(root), GOAL, root)
    framed = _send(started.state, scenario, root)
    refined = _send(framed.state, clarification, root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _completed_loop(root, scenario, clarification):
    ready = _plan_ready_state(root, scenario, clarification)
    return _send(ready.state, "Yes, record this bounded plan.", root)


def _controlled_counts(state):
    return tuple(
        len(_records(state, key))
        for key in ("evidence_minimal_fixture_results", "analysis_refinements", "internal_work_selections")
    )


def test_multiple_physics_corrections_select_latest_effect_without_recomputation(tmp_path):
    completed = _completed_loop(tmp_path, PHYSICS_30, "A numeric result is most useful.")
    after_45 = _send(completed.state, PHYSICS_45, tmp_path)
    after_60 = _send(after_45.state, PHYSICS_60, tmp_path)

    consolidation = _consolidation(after_60.state)
    effects = _records(after_60.state, "long_horizon_correction_effects")
    current = next(effect for effect in effects if effect["effect_id"] == consolidation["active_correction_effect_ids"][0])
    assert consolidation["consolidation_type"] == "latest_supersedes_prior"
    assert len(consolidation["obsolete_correction_effect_ids"]) >= 1
    assert "45-degree" in next(frame for frame in _records(after_60.state, "semantic_problem_frames") if frame["frame_id"] == current["affected_frame_ids"][0])["semantic_input_frame"]["source_text"]
    assert _controlled_counts(after_60.state) == _controlled_counts(completed.state)
    assert after_60.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "clarify"


def test_exact_finance_retraction_restores_only_the_original_completed_posture(tmp_path):
    completed = _completed_loop(tmp_path, FINANCE_70, "Assume losing more than 10% over six months is unacceptable.")
    corrected = _send(completed.state, FINANCE_50, tmp_path)
    retracted = _send(corrected.state, FINANCE_RETRACTION, tmp_path)

    consolidation = _consolidation(retracted.state)
    assert consolidation["consolidation_type"] == "retraction_restores_stable"
    assert consolidation["affected_result_ids"] == [
        _records(completed.state, "evidence_minimal_fixture_results")[0]["evidence_minimal_fixture_result_id"]
    ]
    assert _controlled_counts(retracted.state) == _controlled_counts(completed.state)
    assert retracted.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "completed"
    assert "infer replacement inputs" in consolidation["selected_nonexecuting_posture"].lower()


def test_compound_finance_and_health_effects_remain_domain_separated_and_safety_aware(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    compound = _send(started.state, f"{FINANCE_70} {HEALTH}", tmp_path)
    finance_corrected = _send(compound.state, FINANCE_50, tmp_path)
    health_resolved = _send(finance_corrected.state, HEALTH_CONTEXT, tmp_path)

    consolidation = _consolidation(health_resolved.state)
    arbitration = health_resolved.state.active_objective.provenance["adaptive_route_arbitration"]
    health_routes = [
        record["capability_route_candidate"]
        for record in _records(health_resolved.state, "semantic_problem_frames")
        if record["semantic_input_frame"]["domain_guess"] == "health_information_safety"
    ]
    assert consolidation["consolidation_type"] == "compound_separate_effects"
    assert len(consolidation["active_correction_effect_ids"]) == 2
    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_route_id"] in {route["capability_route_candidate_id"] for route in health_routes}
    assert "diagnosis certainty" in " ".join(health_routes[0]["forbidden_actions"]).lower()


def test_blocked_boundaries_stay_blocked_after_unsafe_or_descriptive_followups(tmp_path):
    for label, source, unsafe in (
        ("operations", OPERATIONS, "Go ahead and contact the supplier and get the pump status."),
        ("cyber", CYBER, "Go ahead and read the repository then scan it."),
    ):
        started = _send(start_or_restore_runtime(tmp_path / label), GOAL, tmp_path / label)
        blocked = _send(started.state, source, tmp_path / label)
        after_followup = _send(blocked.state, unsafe, tmp_path / label)
        consolidation = _consolidation(after_followup.state)
        assert consolidation["consolidation_type"] == "blocked_persists"
        assert after_followup.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "blocked"
        assert not _records(after_followup.state, "evidence_minimal_fixture_results")


def test_partial_clarify_resolution_stays_nonexecuting(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    missing = _send(started.state, GENERIC_MISSING, tmp_path)
    resolved = _send(missing.state, GENERIC_RESOLVED, tmp_path)

    consolidation = _consolidation(resolved.state)
    assert consolidation["consolidation_type"] == "partial_resolution"
    assert consolidation["may_execute_now"] is False
    assert resolved.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "clarify"
    assert not _records(resolved.state, "evidence_minimal_fixture_results")


def test_unrelated_context_does_not_stale_a_completed_finance_lineage(tmp_path):
    completed = _completed_loop(tmp_path, FINANCE_70, "Assume losing more than 10% over six months is unacceptable.")
    after_unrelated = _send(completed.state, GENERIC_MISSING, tmp_path)

    consolidation = _consolidation(after_unrelated.state)
    assert consolidation["consolidation_type"] == "stable_unaffected"
    assert not consolidation["obsolete_correction_effect_ids"]
    assert _controlled_counts(after_unrelated.state) == _controlled_counts(completed.state)
    assert all(effect["effect_type"] != "stale_suppression" for effect in _records(after_unrelated.state, "long_horizon_correction_effects"))


def test_consolidation_is_objective_local_replay_restart_safe_and_ordinary_chat_unchanged(tmp_path):
    first = _completed_loop(tmp_path / "first", PHYSICS_30, "A numeric result is most useful.")
    corrected = _send(first.state, PHYSICS_45, tmp_path / "first")
    replayed = _send(corrected.state, PHYSICS_45, tmp_path / "first")
    restored = start_or_restore_runtime(tmp_path / "first")
    other_started = _send(start_or_restore_runtime(tmp_path / "second"), GOAL + " Keep this second objective separate.", tmp_path / "second")
    other_framed = _send(other_started.state, PHYSICS_30, tmp_path / "second")
    other_refined = _send(other_framed.state, "A numeric result is most useful.", tmp_path / "second")
    other_granted = _send(other_refined.state, "Yes, but only a local fixture.", tmp_path / "second")
    other_accepted = _send(other_granted.state, "Yes, keep that proposal ready.", tmp_path / "second")
    other_authority = _send(other_accepted.state, "Yes, record approval for a future bounded execution gate.", tmp_path / "second")
    other = _send(other_authority.state, "Yes, record this bounded plan.", tmp_path / "second")

    expected = _canonical(_consolidation(corrected.state))
    assert _canonical(_consolidation(replayed.state)) == expected
    assert _canonical(_consolidation(restored)) == expected
    assert _consolidation(corrected.state)["objective_id"] != _consolidation(other.state)["objective_id"]
    ordinary_started = _send(start_or_restore_runtime(tmp_path / "ordinary"), GOAL, tmp_path / "ordinary")
    ordinary = _send(ordinary_started.state, "What is 2 + 2?", tmp_path / "ordinary")
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert "long_horizon_correction_effect_consolidation" not in ordinary.state.active_objective.provenance


def test_consolidation_is_source_bound_and_has_no_graph_side_effects(tmp_path):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, CYBER, tmp_path)
    consolidation = _consolidation(result.state)
    assert consolidation["may_execute_now"] is False
    assert "repository read" in " ".join(consolidation["forbidden_actions"]).lower()
    assert _graph_snapshot(tmp_path) == graph_before
