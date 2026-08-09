import json

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph
from orchestration.runtime.semantic_problem_modeling import compile_semantic_problem_frames


GOAL = (
    "Your new goal is to analyze source-bound scenarios provisionally. Ask me one useful clarification when uncertainty blocks refinement. "
    "When a structured evidence gap materially limits a safer refinement or a calculable fixture need, ask me one permission question about a later bounded evidence source. "
    "I may approve it for later, decline it, defer it, or give you the missing context. Do not gather evidence, inspect files, access a network, "
    "call a model or provider, use a tool, create a sandbox plan, take an external action, change source code, or restart. Wait for my scenarios."
)
FINANCE = "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value, and I am worried about AI stocks dropping over six months."
PHYSICS_30 = "A 5 kg block slides down a frictionless 30-degree incline. I want the acceleration."
PHYSICS_45 = "Correction: the same 5 kg block slides down a frictionless 45-degree incline. I want the acceleration."
OPERATIONS = "Invoice #331 is overdue 45 days. Crew A cannot start the Jackson job until the pump is delivered."
CYBER = "A request parameter is appended into a SQL command before execution."
HEALTH = "I have an itchy rash for two days and I am worried it may be spreading. Should I seek care?"
LEGAL = "A collection agency says I owe a $1,200 balance. I dispute it and do not know which state rules apply."
GENERIC = "The billing system is failing after an update, but no error details or owner are available."


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


def _records(state, key):
    objective = state.active_objective
    assert objective is not None
    return tuple(objective.provenance.get(key, ()))


def _canonical(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _graph_snapshot(root):
    graph = load_graph(root)
    return (tuple(graph.experiences), tuple(graph.claim_versions), tuple(graph.packets), tuple(graph.reviews), tuple(graph.admissions))


def _domains(state):
    return tuple(record["semantic_input_frame"]["domain_guess"] for record in _records(state, "semantic_problem_frames"))


def _routes(state):
    return tuple(record["capability_route_candidate"] for record in _records(state, "semantic_problem_frames"))


def _plan_ready_state(root, scenario, clarification):
    started = _send(start_or_restore_runtime(root), GOAL, root)
    framed = _send(started.state, scenario, root)
    refined = _send(framed.state, clarification, root)
    granted = _send(refined.state, "Yes, but only a local fixture.", root)
    accepted = _send(granted.state, "Yes, keep that proposal ready.", root)
    authority = _send(accepted.state, "Yes, record approval for a future bounded execution gate.", root)
    assert authority.state.pending_chat_requests[0].request_type == "evidence_fixture_execution_plan"
    return authority


def _completed_physics_loop(root):
    ready = _plan_ready_state(root, PHYSICS_30, "A numeric result is most useful.")
    return _send(ready.state, "Yes, record this bounded plan.", root)


def test_finance_and_health_are_separate_source_bound_frames_with_health_clarify_priority(tmp_path):
    source = f"{FINANCE} {HEALTH}"
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, source, tmp_path)

    assert _domains(result.state) == ("finance_portfolio_risk", "health_information_safety")
    routes = _routes(result.state)
    assert tuple(route["decision"] for route in routes) == ("eligible", "clarify")
    arbitration = result.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "clarify"
    assert arbitration["selected_route_id"] == routes[1]["capability_route_candidate_id"]
    assert not result.state.pending_chat_requests
    assert "diagnosis certainty" in " ".join(routes[1]["forbidden_actions"]).lower()
    assert _graph_snapshot(tmp_path) == graph_before


def test_physics_and_operations_select_the_blocked_boundary_without_execution(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, f"{PHYSICS_30} {OPERATIONS}", tmp_path)

    assert _domains(result.state) == ("physics_mechanics", "operations_logistics_receivables")
    routes = _routes(result.state)
    arbitration = result.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "blocked"
    assert arbitration["selected_route_id"] == routes[1]["capability_route_candidate_id"]
    forbidden = " ".join(routes[1]["forbidden_actions"]).lower()
    assert all(term in forbidden for term in ("customer", "payment", "scheduling", "status"))
    assert not _records(result.state, "evidence_minimal_fixture_results")


def test_cyber_and_legal_frames_keep_both_safety_boundaries(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, f"{CYBER} {LEGAL}", tmp_path)

    assert _domains(result.state) == ("defensive_cybersecurity", "legal_financial_risk_information")
    routes = _routes(result.state)
    arbitration = result.state.active_objective.provenance["adaptive_route_arbitration"]
    assert arbitration["decision"] == "blocked"
    assert arbitration["selected_route_id"] == routes[0]["capability_route_candidate_id"]
    forbidden = " ".join(routes[0]["forbidden_actions"] + routes[1]["forbidden_actions"]).lower()
    assert all(term in forbidden for term in ("payload", "repository read", "scan", "legal-advice certainty"))


def test_two_eligible_routes_follow_source_order_without_authority_or_execution(tmp_path):
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, f"{FINANCE} {PHYSICS_30}", tmp_path)

    routes = _routes(result.state)
    arbitration = result.state.active_objective.provenance["adaptive_route_arbitration"]
    assert tuple(route["decision"] for route in routes) == ("eligible", "eligible")
    assert arbitration["decision"] == "eligible"
    assert arbitration["selected_route_id"] == routes[0]["capability_route_candidate_id"]
    assert arbitration["may_execute_now"] is False
    assert not result.state.pending_chat_requests
    assert not _records(result.state, "evidence_fixture_execution_authorities")
    assert not _records(result.state, "evidence_minimal_fixture_results")


def test_completed_correction_and_blocked_compound_preserve_stale_effect_without_duplicate_work(tmp_path):
    completed = _completed_physics_loop(tmp_path)
    before_results = _records(completed.state, "evidence_minimal_fixture_results")
    corrected = _send(completed.state, f"{PHYSICS_45} {OPERATIONS}", tmp_path)

    effects = _records(corrected.state, "long_horizon_correction_effects")
    arbitration = corrected.state.active_objective.provenance["adaptive_route_arbitration"]
    assert any(effect["effect_type"] == "stale_suppression" for effect in effects)
    assert arbitration["decision"] == "blocked"
    assert _records(corrected.state, "evidence_minimal_fixture_results") == before_results
    assert not corrected.state.pending_chat_requests


def test_generic_clause_excludes_ordinary_arithmetic_from_semantic_capture_and_chat_remains_normal(tmp_path):
    source = f"{GENERIC} What is 2 + 2?"
    frames = compile_semantic_problem_frames(source, frame_scope_id="compound-generic")
    assert len(frames) == 1
    assert frames[0].semantic_input_frame.domain_guess == "generic_source_bound_problem"
    assert "2 + 2" not in frames[0].semantic_input_frame.source_text

    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    framed = _send(started.state, source, tmp_path)
    ordinary = _send(framed.state, "What is 2 + 2?", tmp_path)
    assert _domains(framed.state) == ("generic_source_bound_problem",)
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply


def test_compound_replay_restart_and_objective_isolation_are_exact_once(tmp_path):
    source = f"{FINANCE} {HEALTH}"
    first = _send(_send(start_or_restore_runtime(tmp_path / "first"), GOAL, tmp_path / "first").state, source, tmp_path / "first")
    replayed = _send(first.state, source, tmp_path / "first")
    restored = start_or_restore_runtime(tmp_path / "first")
    second_goal = f"{GOAL} Keep this second objective separate."
    second = _send(_send(start_or_restore_runtime(tmp_path / "second"), second_goal, tmp_path / "second").state, source, tmp_path / "second")

    first_frames = _records(first.state, "semantic_problem_frames")
    assert len(first_frames) == 2
    assert _canonical(_records(replayed.state, "semantic_problem_frames")) == _canonical(first_frames)
    assert _canonical(_records(restored, "semantic_problem_frames")) == _canonical(first_frames)
    assert _canonical(replayed.state.active_objective.provenance["adaptive_route_arbitration"]) == _canonical(
        first.state.active_objective.provenance["adaptive_route_arbitration"]
    )
    assert _canonical(restored.active_objective.provenance["adaptive_route_arbitration"]) == _canonical(
        first.state.active_objective.provenance["adaptive_route_arbitration"]
    )
    assert [item["frame_id"] for item in first_frames] != [item["frame_id"] for item in _records(second.state, "semantic_problem_frames")]
    for record in first_frames:
        source_text = record["semantic_input_frame"]["source_text"]
        assert all(source_text[int(span["start"]):int(span["end"])] == span["text"] for span in record["semantic_input_frame"]["source_spans"])
