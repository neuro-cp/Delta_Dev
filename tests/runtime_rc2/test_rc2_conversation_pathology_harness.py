from __future__ import annotations

import json

from orchestration.runtime import rc1_operator_console as rc1
from orchestration.runtime import rc2_developmental_concept_memory as rc2mem
from orchestration.runtime.rc2_conversation_pathology_harness import (
    HARNESS_FLAGS,
    build_conversation_trial_suite,
    run_conversation_pathology_harness,
    write_conversation_pathology_reports,
)


def _isolate_rc1_store(monkeypatch, tmp_path):
    proposition = tmp_path / "noncanonical_propositions.jsonl"
    evidence = tmp_path / "evidence_links.jsonl"
    replay = tmp_path / "replay_queue.jsonl"
    contradictions = tmp_path / "contradictions.jsonl"
    monkeypatch.setattr(rc1, "DATA", tmp_path)
    monkeypatch.setattr(rc1, "PROPOSITION_LOG", proposition)
    monkeypatch.setattr(rc1, "EVIDENCE_LOG", evidence)
    monkeypatch.setattr(rc1, "REPLAY_LOG", replay)
    monkeypatch.setattr(rc1, "CONTRADICTION_LOG", contradictions)
    monkeypatch.setattr(rc1, "LOCAL_STORE_LOGS", (proposition, evidence, replay, contradictions))


def _isolate_rc2_store(monkeypatch, tmp_path):
    conversation = tmp_path / "conversation_memory.jsonl"
    personal = tmp_path / "personal_memory.jsonl"
    knowledge = tmp_path / "knowledge_concepts.jsonl"
    edges = tmp_path / "concept_edges.jsonl"
    replay = tmp_path / "concept_replay_queue.jsonl"
    contradictions = tmp_path / "concept_contradictions.jsonl"
    monkeypatch.setattr(rc2mem, "DATA", tmp_path)
    monkeypatch.setattr(rc2mem, "CONVERSATION_MEMORY_LOG", conversation)
    monkeypatch.setattr(rc2mem, "PERSONAL_MEMORY_LOG", personal)
    monkeypatch.setattr(rc2mem, "KNOWLEDGE_MEMORY_LOG", knowledge)
    monkeypatch.setattr(rc2mem, "CONCEPT_EDGE_LOG", edges)
    monkeypatch.setattr(rc2mem, "CONCEPT_REPLAY_LOG", replay)
    monkeypatch.setattr(rc2mem, "CONCEPT_CONTRADICTION_LOG", contradictions)
    monkeypatch.setattr(rc2mem, "STORE_BY_TYPE", {"conversation": conversation, "personal": personal, "knowledge": knowledge})


def test_pathology_suite_contains_100_cases():
    suite = build_conversation_trial_suite()
    assert len(suite) == 100
    categories = {case.category for case in suite}
    assert "simple_fact" in categories
    assert "casual_unknown" in categories
    assert "provider_trap" in categories
    assert "memory_trap" in categories


def test_pathology_harness_is_safe_and_does_not_persist(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    report = run_conversation_pathology_harness(count=20)
    assert report["question_count"] == 20
    assert report["persistent_cognitive_store_enabled"] is False
    assert report["flags"] == HARNESS_FLAGS
    assert all(result["provider_calls_performed"] is False for result in report["results"])
    assert all(result["training_performed"] is False for result in report["results"])
    assert all(result["canonical_write_performed"] is False for result in report["results"])
    assert rc2mem.build_developmental_memory_state()["knowledge_memory_records"] == 0
    assert report["readiness_gate"]["recommendation"] in {
        "READY_FOR_PERSISTENT_COGNITIVE_STORE",
        "MORE_CONVERSATION_REPAIR_REQUIRED",
        "MEMORY_PERSISTENCE_BLOCKED",
    }


def test_pathology_harness_writes_valid_reports(monkeypatch, tmp_path):
    _isolate_rc1_store(monkeypatch, tmp_path)
    _isolate_rc2_store(monkeypatch, tmp_path)
    reports = tmp_path / "reports"
    monkeypatch.setattr("orchestration.runtime.rc2_conversation_pathology_harness.REPORTS", reports)
    report = write_conversation_pathology_reports(count=12)
    json_path = reports / "RC2_CONVERSATION_PATHOLOGY_HARNESS.json"
    md_path = reports / "RC2_CONVERSATION_PATHOLOGY_HARNESS.md"
    assert json_path.exists()
    assert md_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["trial_id"] == report["trial_id"]
    assert "Persistent Cognitive Store" in md_path.read_text(encoding="utf-8")
