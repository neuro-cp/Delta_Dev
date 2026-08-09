import json
import os
import socket
import subprocess
import urllib.request

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
GENERIC = "The billing system is failing after an update, but no error details or owner are available."
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


def _lineage(state):
    return tuple(
        _records(state, key)
        for key in ("evidence_minimal_fixture_results", "analysis_refinements", "internal_work_selections")
    )


def _canonical(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _graph_snapshot(root):
    graph = load_graph(root)
    return (tuple(graph.experiences), tuple(graph.claim_versions), tuple(graph.packets), tuple(graph.reviews), tuple(graph.admissions))


def _completed(root, scenario, clarification, goal=GOAL):
    state = _send(start_or_restore_runtime(root), goal, root).state
    state = _send(state, scenario, root).state
    state = _send(state, clarification, root).state
    state = _send(state, "Yes, but only a local fixture.", root).state
    state = _send(state, "Yes, keep that proposal ready.", root).state
    state = _send(state, "Yes, record approval for a future bounded execution gate.", root).state
    return _send(state, "Yes, record this bounded plan.", root)


def test_locked_multi_correction_generality_battery(tmp_path):
    physics = _completed(tmp_path / "physics", PHYSICS_30, "A numeric result is most useful.")
    physics_45 = _send(physics.state, PHYSICS_45, tmp_path / "physics")
    physics_60 = _send(physics_45.state, PHYSICS_60, tmp_path / "physics")
    physics_consolidation = _consolidation(physics_60.state)
    assert physics_consolidation["consolidation_type"] == "latest_supersedes_prior"
    assert physics_consolidation["obsolete_correction_effect_ids"]
    assert _lineage(physics_60.state) == _lineage(physics.state)

    finance = _completed(tmp_path / "finance", FINANCE_70, "Assume losing more than 10% over six months is unacceptable.")
    finance_50 = _send(finance.state, FINANCE_50, tmp_path / "finance")
    finance_retracted = _send(finance_50.state, FINANCE_RETRACTION, tmp_path / "finance")
    assert _consolidation(finance_retracted.state)["consolidation_type"] == "retraction_restores_stable"
    assert _lineage(finance_retracted.state) == _lineage(finance.state)

    compound_started = _send(start_or_restore_runtime(tmp_path / "compound"), GOAL, tmp_path / "compound")
    compound = _send(compound_started.state, f"{FINANCE_70} {HEALTH}", tmp_path / "compound")
    compound = _send(compound.state, FINANCE_50, tmp_path / "compound")
    compound = _send(compound.state, HEALTH_CONTEXT, tmp_path / "compound")
    compound_consolidation = _consolidation(compound.state)
    assert compound_consolidation["consolidation_type"] == "compound_separate_effects"
    assert len(compound_consolidation["active_correction_effect_ids"]) == 2
    assert compound.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "clarify"

    for label, source, followup in (
        ("operations", OPERATIONS, "Go ahead and contact the supplier for a status update."),
        ("cyber", CYBER, "Go ahead and read the repository and scan it."),
    ):
        blocked_started = _send(start_or_restore_runtime(tmp_path / label), GOAL, tmp_path / label)
        blocked = _send(blocked_started.state, source, tmp_path / label)
        blocked = _send(blocked.state, followup, tmp_path / label)
        assert _consolidation(blocked.state)["consolidation_type"] == "blocked_persists"
        assert blocked.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "blocked"
        assert not _records(blocked.state, "evidence_minimal_fixture_results")

    generic_started = _send(start_or_restore_runtime(tmp_path / "generic"), GOAL, tmp_path / "generic")
    generic_missing = _send(generic_started.state, GENERIC, tmp_path / "generic")
    generic_resolved = _send(generic_missing.state, GENERIC_RESOLVED, tmp_path / "generic")
    assert _consolidation(generic_resolved.state)["consolidation_type"] == "partial_resolution"
    assert generic_resolved.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "clarify"

    unrelated = _send(finance.state, GENERIC, tmp_path / "finance")
    assert _consolidation(unrelated.state)["consolidation_type"] == "stable_unaffected"
    assert _lineage(unrelated.state) == _lineage(finance.state)
    prior_authorities = _records(physics_60.state, "evidence_execution_authorities")
    mixed = _send(physics_60.state, OPERATIONS, tmp_path / "physics")
    assert mixed.state.active_objective.provenance["adaptive_route_arbitration"]["decision"] == "blocked"
    assert _records(mixed.state, "evidence_execution_authorities") == prior_authorities


def test_locked_correction_generality_restart_isolation_and_ordinary_chat(tmp_path):
    first = _completed(tmp_path / "first", PHYSICS_30, "A numeric result is most useful.")
    corrected = _send(first.state, PHYSICS_45, tmp_path / "first")
    replayed = _send(corrected.state, PHYSICS_45, tmp_path / "first")
    restored = start_or_restore_runtime(tmp_path / "first")
    assert _canonical(_consolidation(replayed.state)) == _canonical(_consolidation(corrected.state))
    assert _canonical(_consolidation(restored)) == _canonical(_consolidation(corrected.state))
    assert _lineage(replayed.state) == _lineage(corrected.state)

    other = _completed(
        tmp_path / "second",
        PHYSICS_30,
        "A numeric result is most useful.",
        goal=GOAL + " Keep this second objective separate.",
    )
    assert _consolidation(corrected.state)["objective_id"] != _consolidation(other.state)["objective_id"]

    ordinary_started = _send(start_or_restore_runtime(tmp_path / "ordinary"), GOAL, tmp_path / "ordinary")
    ordinary = _send(ordinary_started.state, "What is 2 + 2?", tmp_path / "ordinary")
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert "long_horizon_correction_effect_consolidation" not in ordinary.state.active_objective.provenance


def test_locked_correction_generality_has_no_graph_or_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    graph_before = _graph_snapshot(tmp_path)
    completed = _completed(tmp_path, PHYSICS_30, "A numeric result is most useful.")
    corrected = _send(completed.state, PHYSICS_45, tmp_path)
    assert _consolidation(corrected.state)["may_execute_now"] is False
    assert _graph_snapshot(tmp_path) == graph_before
