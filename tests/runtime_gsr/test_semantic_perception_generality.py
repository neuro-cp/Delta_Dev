import os
import socket
import subprocess
import urllib.request

import pytest

from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)
from orchestration.runtime.provisional_semantic_consolidation import load_graph
from orchestration.runtime.semantic_problem_modeling import compile_semantic_problem_frame


GOAL = (
    "Your new goal is to hold source-bound scenario analyses provisionally. "
    "Do not call a model, provider, tool, or take an external action. Wait for my scenarios."
)


@pytest.mark.parametrize(
    ("source", "domain", "expected_terms"),
    (
        (
            "My retirement account is 65% technology funds, 25% cash, and 10% small-cap value; I am worried about a growth-stock drawdown over six months.",
            "finance_portfolio_risk",
            ("six months", "technology", "drawdown"),
        ),
        (
            "A 3 kg object moves down a 30-degree ramp without friction. Please calculate its acceleration.",
            "physics_mechanics",
            ("30-degree", "friction", "acceleration"),
        ),
        (
            "Invoice #87 has been unpaid for 30 days, and Team West cannot begin the Cedar install until the lift arrives.",
            "operations_logistics_receivables",
            ("Invoice #87", "Team West", "lift"),
        ),
        (
            "A request parameter is string-concatenated into a SQL statement before it runs.",
            "defensive_cybersecurity",
            ("request parameter", "SQL", "concatenated"),
        ),
        (
            "I have an itchy rash for two days and I am worried it may be spreading. Should I seek care?",
            "health_information_safety",
            ("itchy rash", "two days", "spreading"),
        ),
        (
            "A collection agency says I owe a $1,200 balance. I dispute it and only have its notice; I do not know which state rules apply.",
            "legal_financial_risk_information",
            ("collection agency", "balance", "dispute"),
        ),
        (
            "The billing system is failing after an update, but no error details or owner are available.",
            "generic_source_bound_problem",
            ("failing", "no error details"),
        ),
    ),
)
def test_structured_sources_compile_to_deterministic_source_bound_frames(source, domain, expected_terms):
    first = compile_semantic_problem_frame(source, frame_scope_id="semantic-generality")
    second = compile_semantic_problem_frame(source, frame_scope_id="semantic-generality")

    assert first is not None
    assert second is not None
    record = first.as_record()
    frame = record["semantic_input_frame"]
    model = record["problem_model"]
    assert frame["frame_id"] == second.semantic_input_frame.frame_id
    assert frame["source_text"] == source
    assert frame["domain_guess"] == domain
    assert frame["source_spans"]
    assert frame["known_facts"] if "known_facts" in frame else model["given_information"]
    assert frame["unknown_target"]
    assert frame["constraints"]
    assert frame["limitations"]
    assert model["candidate_methods"]
    assert all(term.lower() in source.lower() for term in expected_terms)
    assert all(
        source[int(span["start"]):int(span["end"])] == span["text"]
        for span in frame["source_spans"]
    )


def _graph_snapshot(root):
    graph = load_graph(root)
    return (
        tuple(graph.experiences),
        tuple(graph.claim_versions),
        tuple(graph.packets),
        tuple(graph.reviews),
        tuple(graph.admissions),
    )


def _send(state, text, root):
    return handle_conversational_message(state, text, runtime_root=root, run_background_cycle=False)


@pytest.mark.parametrize(
    ("source", "domain"),
    (
        ("I have an itchy rash for two days and I am concerned it is spreading. Should I seek care?", "health_information_safety"),
        ("A debt collector says I owe a disputed balance. I am not sure which state law applies.", "legal_financial_risk_information"),
        ("The billing system is inconsistent after an update, but no error details or owner are known.", "generic_source_bound_problem"),
    ),
)
def test_new_safe_and_generic_frames_persist_without_analysis_execution_or_graph_mutation(tmp_path, source, domain):
    graph_before = _graph_snapshot(tmp_path)
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(started.state, source, tmp_path)

    objective = result.state.active_objective
    assert objective is not None
    frames = tuple(objective.provenance.get("semantic_problem_frames", ()))
    assert len(frames) == 1
    assert frames[0]["semantic_input_frame"]["domain_guess"] == domain
    assert not objective.provenance.get("evidence_bound_analyses", ())
    assert not result.state.pending_chat_requests
    assert not result.state.resolved_chat_requests
    assert _graph_snapshot(tmp_path) == graph_before


def test_health_and_legal_frames_are_explicitly_non_diagnostic_and_non_advisory():
    health = compile_semantic_problem_frame(
        "I have an itchy rash for two days and I am worried it is spreading. Should I seek care?",
        frame_scope_id="health-safety",
    )
    legal = compile_semantic_problem_frame(
        "A collection agency says I owe a $1,200 balance. I dispute it and do not know which state rules apply.",
        frame_scope_id="legal-safety",
    )

    assert health is not None and legal is not None
    health_record = health.as_record()
    legal_record = legal.as_record()
    health_text = " ".join(
        (*health_record["semantic_input_frame"]["limitations"], health_record["problem_model"]["expected_output"])
    ).lower()
    legal_text = " ".join(
        (*legal_record["semantic_input_frame"]["limitations"], legal_record["problem_model"]["expected_output"])
    ).lower()
    assert "does not diagnose" in health_text
    assert "prescribe" in health_text
    assert "escalation" in health_record["semantic_input_frame"]["unknown_target"].lower()
    assert "not legal advice" in legal_text
    assert "jurisdiction" in legal_record["semantic_input_frame"]["unknown_target"].lower()
    assert "liability" in legal_text


def test_ambiguous_structured_source_stays_generic_and_does_not_invent_specialist_facts():
    source = "The warehouse count is inconsistent, but no one knows which records changed or who owns the correction."
    compilation = compile_semantic_problem_frame(source, frame_scope_id="generic-ambiguity")

    assert compilation is not None
    record = compilation.as_record()
    frame = record["semantic_input_frame"]
    assert frame["domain_guess"] == "generic_source_bound_problem"
    assert "specialist" in " ".join(frame["limitations"]).lower()
    assert "warehouse" not in " ".join(str(item) for item in record["problem_model"]["given_information"]).lower()
    assert "domain" in frame["unknown_target"].lower()


def test_ordinary_chat_remains_unframed_and_returns_four(tmp_path):
    assert compile_semantic_problem_frame("What is 2 + 2?", frame_scope_id="ordinary") is None
    assert compile_semantic_problem_frame("Nice weather today.", frame_scope_id="ordinary") is None

    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    ordinary = _send(started.state, "What is 2 + 2?", tmp_path)
    objective = ordinary.state.active_objective
    assert ordinary.intent.intent_type == "ordinary_conversation"
    assert "4" in ordinary.reply
    assert objective is not None
    assert not objective.provenance.get("semantic_problem_frames", ())
    assert not ordinary.state.pending_chat_requests


def test_generic_frame_replay_and_restart_are_exact_once(tmp_path):
    source = "The billing system is failing after an update, but no error details or owner are available."
    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    recorded = _send(started.state, source, tmp_path)
    frame = recorded.state.active_objective.provenance["semantic_problem_frames"][0]

    replayed = _send(recorded.state, source, tmp_path)
    restored = start_or_restore_runtime(tmp_path)
    replayed_frames = replayed.state.active_objective.provenance["semantic_problem_frames"]
    restored_frames = restored.active_objective.provenance["semantic_problem_frames"]
    assert len(replayed_frames) == 1
    assert len(restored_frames) == 1
    assert replayed_frames[0]["frame_id"] == frame["frame_id"]
    assert restored_frames[0]["frame_id"] == frame["frame_id"]


def test_semantic_frame_compilation_cannot_reach_external_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external side effect")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    started = _send(start_or_restore_runtime(tmp_path), GOAL, tmp_path)
    result = _send(
        started.state,
        "A request parameter is string-concatenated into a SQL statement before it runs.",
        tmp_path,
    )
    assert result.intent.intent_type == "semantic_problem_modeling"
    assert "no exploit payload is required" in result.reply.lower()
    assert "drop table" not in result.reply.lower()
    assert "; --" not in result.reply.lower()
