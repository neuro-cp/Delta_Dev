from __future__ import annotations

import json
from dataclasses import asdict

from knowledge.semantic_record import SemanticKnowledgeRecord
from orchestration.runtime.candidate_knowledge_retrieval import KnowledgeActivationEngine


def _record(**overrides):
    payload = {
        "concept_id": "concept-a",
        "created_at": "2026-07-02T00:00:00+00:00",
        "updated_at": "2026-07-02T00:00:00+00:00",
        "concept": "Emergency evacuation planning",
        "definition": "Evacuation plans should account for flood routing, shelter capacity, and traffic constraints.",
        "confidence": 0.72,
        "supporting_evidence": ["memory-a"],
        "contradicting_evidence": [],
        "relationship_ids": ["rel-a"],
        "creation_source": "test",
        "last_validation": None,
        "revision_history": [],
        "metadata": {},
    }
    payload.update(overrides)
    return SemanticKnowledgeRecord(**payload)


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(asdict(row), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_candidate_knowledge_retriever_activates_relevant_concepts(tmp_path):
    store = tmp_path / "store"
    reports = tmp_path / "reports"
    _write_jsonl(
        store / "knowledge.jsonl",
        [
            _record(),
            _record(
                concept_id="concept-b",
                concept="Tool logging",
                definition="Incident logs support diagnosis when software services fail.",
                confidence=0.5,
            ),
        ],
    )
    reports.mkdir()
    (reports / "promotion_governance_report.json").write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "concept_id": "concept-a",
                        "recommendation": "Promotion Eligible",
                        "promotion_score": 0.71,
                        "dimensions": {
                            "projected_centrality": 0.4,
                            "evidence_support": 0.8,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    activation = KnowledgeActivationEngine(
        store_root=store,
        reports_dirs=(reports,),
    ).activate("What is the safest flood evacuation strategy?", limit=5)

    assert activation.items
    assert activation.items[0].concept_id == "concept-a"
    assert activation.items[0].recommendation == "Promotion Eligible"
    assert activation.items[0].metadata["supporting_evidence"] == ["memory-a"]


def test_candidate_knowledge_retriever_excludes_superseded_records(tmp_path):
    store = tmp_path / "store"
    _write_jsonl(
        store / "knowledge.jsonl",
        [
            _record(concept_id="old-concept"),
            _record(
                concept_id="new-concept",
                revision_history=["old-concept"],
                definition="Flood evacuation planning should account for traffic and shelter constraints.",
            ),
        ],
    )

    activation = KnowledgeActivationEngine(store_root=store).activate(
        "flood evacuation traffic shelter",
        limit=10,
    )

    assert [item.concept_id for item in activation.items] == ["new-concept"]


def test_candidate_knowledge_activation_builds_working_memory_context(tmp_path):
    store = tmp_path / "store"
    _write_jsonl(store / "knowledge.jsonl", [_record()])

    activation = KnowledgeActivationEngine(store_root=store).activate(
        "flood evacuation shelter traffic",
        limit=1,
    )
    context = activation.as_working_memory_context(cycle_id="cycle-1")

    assert context.cycle_id == "cycle-1"
    assert context.items[0].kind == "candidate_knowledge"
    assert context.items[0].source == "candidate_knowledge_store"
    assert "Emergency evacuation planning" in context.items[0].text


def test_candidate_knowledge_retriever_is_read_only(tmp_path):
    store = tmp_path / "store"
    _write_jsonl(store / "knowledge.jsonl", [_record()])
    before = (store / "knowledge.jsonl").read_text(encoding="utf-8")

    KnowledgeActivationEngine(store_root=store).activate("evacuation", limit=1)

    assert (store / "knowledge.jsonl").read_text(encoding="utf-8") == before
    assert sorted(path.name for path in store.iterdir()) == ["knowledge.jsonl"]


def test_recurrence_penalty_is_bounded_and_preserves_original_score(tmp_path, monkeypatch):
    store = tmp_path / "store"
    prior = tmp_path / "prior.json"
    _write_jsonl(store / "knowledge.jsonl", [_record(concept_id="concept-a")])
    prior.write_text(
        json.dumps({"recurring_noise_prior": {"concept-a": {"penalty": 0.14, "recurrence": 9}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_MODE", "conservative")
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_PRIOR", str(prior))

    item = KnowledgeActivationEngine(store_root=store).activate("flood", limit=1).items[0]

    assert item.metadata["recurrence_risk"] is True
    assert item.metadata["recurrence_penalty"] == 0.045
    assert item.metadata["original_activation_score"] > item.score


def test_recurrence_penalty_strong_specific_match_overrides(tmp_path, monkeypatch):
    store = tmp_path / "store"
    prior = tmp_path / "prior.json"
    _write_jsonl(store / "knowledge.jsonl", [_record(concept_id="concept-a")])
    prior.write_text(
        json.dumps({"recurring_noise_prior": {"concept-a": {"penalty": 0.14, "recurrence": 9}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_MODE", "conservative")
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_PRIOR", str(prior))

    item = KnowledgeActivationEngine(store_root=store).activate("flood shelter traffic", limit=1).items[0]

    assert item.metadata["recurrence_override"] is True
    assert item.metadata["recurrence_penalty"] == 0.0
    assert item.metadata["original_activation_score"] == item.score


def test_recurrence_metadata_mode_does_not_change_score(tmp_path, monkeypatch):
    store = tmp_path / "store"
    prior = tmp_path / "prior.json"
    _write_jsonl(store / "knowledge.jsonl", [_record(concept_id="concept-a")])
    prior.write_text(
        json.dumps({"recurring_noise_prior": {"concept-a": {"penalty": 0.14, "recurrence": 9}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_MODE", "metadata")
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_PRIOR", str(prior))

    item = KnowledgeActivationEngine(store_root=store).activate("flood", limit=1).items[0]

    assert item.metadata["recurrence_risk"] is True
    assert item.metadata["recurrence_penalty"] == 0.0
    assert item.metadata["original_activation_score"] == item.score


def test_recurrence_feature_can_be_disabled_cleanly(tmp_path, monkeypatch):
    store = tmp_path / "store"
    prior = tmp_path / "prior.json"
    _write_jsonl(store / "knowledge.jsonl", [_record(concept_id="concept-a")])
    prior.write_text(
        json.dumps({"recurring_noise_prior": {"concept-a": {"penalty": 0.14, "recurrence": 9}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_MODE", "off")
    monkeypatch.setenv("DELTA_RUNTIME_V13_RECURRENCE_PRIOR", str(prior))

    item = KnowledgeActivationEngine(store_root=store).activate("flood", limit=1).items[0]

    assert item.metadata["recurrence_risk"] is True
    assert item.metadata["recurrence_penalty"] == 0.0
    assert item.metadata["original_activation_score"] == item.score
