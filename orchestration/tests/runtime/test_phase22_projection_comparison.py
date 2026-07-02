from __future__ import annotations

from datetime import datetime, timezone

from knowledge import SemanticKnowledgeRecord, SemanticKnowledgeStore
from knowledge.prediction_engine import PredictionEngine
from knowledge.prediction_record import PredictionRecord
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from tools.phase22_projection_comparison import compare_projection


def test_phase22_comparison_reports_projection_delta(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    first = memory.add(kind="observation", text="first", source="test")
    second = memory.add(kind="observation", text="second", source="test")
    relationships.add(
        source_id=first.memory_id,
        target_id=second.memory_id,
        relationship_type="temporal_sequence",
        confidence=0.8,
    )
    now = datetime.now(timezone.utc).isoformat()
    record = knowledge.add(
        SemanticKnowledgeRecord(
            concept_id="concept",
            created_at=now,
            updated_at=now,
            concept="Projection comparison concept",
            definition="Projection comparison concept is supported by linked evidence.",
            confidence=0.86,
            supporting_evidence=[first.memory_id],
            creation_source="test",
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="prediction",
                created_at=now,
                source_concept_id=record.concept_id,
                expectation="If relevant, expect support.",
                confidence=0.7,
                status="supported",
            )
        ]
    )

    summary = compare_projection(store_root=store_root, reports_dir=reports_dir)

    assert summary["concepts_evaluated"] == 1
    assert summary["average_projected_centrality"] > summary["average_raw_centrality"]
    assert summary["evidence_projection_boosted_count"] == 1
    assert (reports_dir / "phase22_projection_comparison.md").exists()
