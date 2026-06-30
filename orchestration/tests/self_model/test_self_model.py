from __future__ import annotations

from datetime import datetime, timezone

from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
from knowledge.semantic_record import SemanticKnowledgeRecord
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.self_model import SelfModelRegion


def test_self_model_generates_metrics_from_existing_regions(tmp_path):
    memory = MemoryStore(tmp_path / "memory.jsonl")
    relationships = RelationshipStore(tmp_path / "relationships.jsonl")
    learning = LearningStore(tmp_path / "learning.jsonl")
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    contradictions = ContradictionEngine(tmp_path / "contradictions.jsonl")
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")

    observation = memory.add(
        text="Delta observed a working memory cycle.",
        tags=("cycle", "working_memory"),
        confidence=0.8,
    )
    output = memory.add(
        text="Delta returned a mock answer.",
        kind="orchestration_output",
        source="delta:mock",
        tags=("cycle", "output"),
        confidence=0.7,
    )
    relationships.add(
        source_id=observation.memory_id,
        target_id=output.memory_id,
        relationship_type="temporal_sequence",
    )
    record = SemanticKnowledgeRecord(
        concept_id="concept-1",
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        concept="Delta working memory",
        definition="Delta can assemble per-cycle active context.",
        confidence=0.75,
        supporting_evidence=[observation.memory_id],
        creation_source="test",
    )
    knowledge.add(record)
    prediction = predictions.generate_for(record)
    assert prediction is not None
    predictions.add_all([prediction])

    snapshot = SelfModelRegion(
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
    ).generate()

    assert snapshot.identity["name"] == "Delta"
    assert snapshot.metrics["experience_count"] == 2
    assert snapshot.metrics["semantic_knowledge_count"] == 1
    assert snapshot.metrics["relationship_count"] == 1
    assert snapshot.metrics["open_prediction_count"] == 1
    assert snapshot.cognitive_health["prediction_quality"] == "unknown"
    assert snapshot.self_observations
