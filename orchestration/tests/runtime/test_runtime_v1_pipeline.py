from __future__ import annotations

import json
from dataclasses import asdict

from knowledge.semantic_record import SemanticKnowledgeRecord
from orchestration.runtime import RuntimeV1Pipeline


def _record(concept_id: str, concept: str, definition: str, confidence: float = 0.8):
    return SemanticKnowledgeRecord(
        concept_id=concept_id,
        created_at="2026-07-02T00:00:00+00:00",
        updated_at="2026-07-02T00:00:00+00:00",
        concept=concept,
        definition=definition,
        confidence=confidence,
        supporting_evidence=["memory-a"],
        contradicting_evidence=[],
        relationship_ids=["rel-a"],
        creation_source="test",
        last_validation=None,
        revision_history=[],
        metadata={},
    )


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(asdict(row), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_runtime_v1_pipeline_answers_with_activated_candidate_knowledge(tmp_path):
    store = tmp_path / "store"
    reports = tmp_path / "reports"
    _write_jsonl(
        store / "knowledge.jsonl",
        [
            _record(
                "snow-a",
                "Snowstorm preparation",
                "Cities should pre-position plows, prioritize emergency routes, and track shelter capacity before severe snowstorms.",
            ),
            _record(
                "risk-a",
                "Risk tradeoff",
                "Resource allocation plans should identify tradeoffs between immediate relief and capacity exhaustion.",
            ),
        ],
    )
    reports.mkdir()
    (reports / "promotion_governance_report.json").write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "concept_id": "snow-a",
                        "recommendation": "Validated",
                        "promotion_score": 0.61,
                        "dimensions": {"projected_centrality": 0.3, "evidence_support": 1.0},
                    },
                    {
                        "concept_id": "risk-a",
                        "recommendation": "Candidate",
                        "promotion_score": 0.55,
                        "dimensions": {"projected_centrality": 0.25, "evidence_support": 0.8},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    before = (store / "knowledge.jsonl").read_text(encoding="utf-8")

    result = RuntimeV1Pipeline(store_root=store, reports_dirs=(reports,), activation_limit=5).answer(
        "How should a city prepare for a severe snowstorm?",
        cycle_id="cycle-1",
    )

    assert result.activation.items
    assert result.working_memory.items
    assert result.reasoning.findings
    assert result.plan.recommended_option == "Evidence-grounded recommendation"
    assert "Activated support" in result.response.answer
    assert result.response.evidence_used
    assert (store / "knowledge.jsonl").read_text(encoding="utf-8") == before


def test_runtime_v1_pipeline_handles_sparse_activation(tmp_path):
    store = tmp_path / "store"
    _write_jsonl(
        store / "knowledge.jsonl",
        [
            _record(
                "snow-a",
                "Snowstorm preparation",
                "Cities should pre-position plows before severe snowstorms.",
            )
        ],
    )

    result = RuntimeV1Pipeline(store_root=store, activation_limit=5).answer(
        "Explain violin tuning.",
        cycle_id="cycle-2",
    )

    assert result.activation.items == []
    assert result.reasoning.confidence == 0.0
    assert result.plan.recommended_option == "Low-evidence response"
    assert "not have enough activated candidate knowledge" in result.response.answer
