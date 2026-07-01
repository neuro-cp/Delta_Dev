from __future__ import annotations

from knowledge import (
    ContradictionEngine,
    PredictionEngine,
    SemanticConsolidationEngine,
    SemanticKnowledgeStore,
)
from knowledge.contradiction_record import ContradictionRecord
from knowledge.prediction_record import PredictionRecord
from learning.region.learning_record import LearningRecord, SemanticCandidate
from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.self_model import SelfModelRegion


def test_duplicate_consolidation_stress_suppresses_semantic_growth(tmp_path):
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    engine = SemanticConsolidationEngine(
        semantic_store=knowledge,
        prediction_engine=predictions,
    )
    learning = [
        LearningRecord(
            learning_id=f"l{index}",
            created_at="2026-06-30T00:00:00+00:00",
            cycle_id=f"c{index}",
            semantic_candidates=[
                SemanticCandidate(
                    text="Repeated evidence supports bounded consolidation.",
                    evidence_memory_ids=[f"m{index}"],
                    confidence=0.8,
                    rationale="stress",
                )
            ],
        )
        for index in range(100)
    ]

    first = engine.consolidate(learning)
    second = engine.consolidate(learning)

    assert len(first["created"]) == 1
    assert len(second["created"]) == 0
    assert len(knowledge.latest()) == 1
    assert len(predictions.latest()) == 1


def test_repeated_recent_learning_records_are_not_reconsolidated(tmp_path):
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    engine = SemanticConsolidationEngine(semantic_store=knowledge)
    learning = LearningRecord(
        learning_id="learning-1",
        created_at="2026-06-30T00:00:00+00:00",
        cycle_id="cycle-1",
        semantic_candidates=[
            SemanticCandidate(
                text="Repeated attended context appears relevant to the prompt.",
                evidence_memory_ids=["m1"],
                confidence=0.85,
                rationale="runtime repeated recent learning",
            )
        ],
    )

    first = engine.consolidate([learning])
    second = engine.consolidate([learning])

    assert len(first["created"]) == 1
    assert len(second["created"]) == 0
    assert len(knowledge.all()) == 1


def test_contradiction_engine_deduplicates_open_claim_pairs(tmp_path):
    contradictions = ContradictionEngine(tmp_path / "contradictions.jsonl")
    record = ContradictionRecord(
        contradiction_id="c1",
        created_at="2026-06-30T00:00:00+00:00",
        claim_a_id="a",
        claim_b_id="b",
        reason="test",
        severity=0.5,
    )
    duplicate = ContradictionRecord(
        contradiction_id="c2",
        created_at="2026-06-30T00:00:01+00:00",
        claim_a_id="b",
        claim_b_id="a",
        reason="test",
        severity=0.5,
    )

    contradictions.add_all([record])
    added = contradictions.add_all([duplicate])

    assert added == []
    assert len(contradictions.latest()) == 1


def test_relationship_weight_stress_caps_at_one(tmp_path):
    relationships = RelationshipStore(tmp_path / "relationships.jsonl")
    relationship = relationships.add(
        source_id="a",
        target_id="b",
        relationship_type="similarity",
        confidence=0.95,
    )

    for index in range(20):
        relationship = relationships.strengthen(
            relationship,
            evidence=f"repeat-{index}",
            amount=0.05,
        )

    assert relationship.weight == 1.0
    assert relationship.confidence == 1.0
    assert relationship.reinforcement_count == 21
    assert relationships.latest() == [relationship]


def test_prediction_quality_stress_uses_latest_revisions(tmp_path):
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    for index in range(50):
        predictions.add_all(
            [
                PredictionRecord(
                    prediction_id="p1",
                    created_at=f"2026-06-30T00:{index:02d}:00+00:00",
                    source_concept_id="c1",
                    expectation="expectation",
                    confidence=0.5,
                    status="open",
                )
            ]
        )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p1",
                created_at="2026-06-30T01:00:00+00:00",
                source_concept_id="c1",
                expectation="expectation",
                confidence=0.6,
                status="failed",
                metadata={"validation": {"score": 0.7}},
            )
        ]
    )

    metrics = predictions.quality_metrics()

    assert metrics["total"] == 1
    assert metrics["failed"] == 1
    assert metrics["open"] == 0
    assert metrics["coverage"] == 1.0


def test_self_model_observes_high_contradiction_pressure(tmp_path):
    memory = MemoryStore(tmp_path / "memory.jsonl")
    relationships = RelationshipStore(tmp_path / "relationships.jsonl")
    learning = LearningStore(tmp_path / "learning.jsonl")
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    contradictions = ContradictionEngine(tmp_path / "contradictions.jsonl")
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")

    record_a = knowledge.add(
        SemanticKnowledgeStoreRecordFactory.make("a", "Claim A is true.")
    )
    record_b = knowledge.add(
        SemanticKnowledgeStoreRecordFactory.make("b", "Claim A is not true.")
    )
    contradictions.add_all(
        [
            ContradictionRecord(
                contradiction_id="c1",
                created_at="2026-06-30T00:00:00+00:00",
                claim_a_id=record_a.concept_id,
                claim_b_id=record_b.concept_id,
                reason="stress",
                severity=0.8,
            )
        ]
    )

    snapshot = SelfModelRegion(
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
    ).generate()

    assert any(
        item["kind"] == "contradiction_pressure"
        for item in snapshot.self_observations
    )


class SemanticKnowledgeStoreRecordFactory:
    @staticmethod
    def make(concept_id: str, definition: str):
        from knowledge import SemanticKnowledgeRecord

        return SemanticKnowledgeRecord(
            concept_id=concept_id,
            created_at="2026-06-30T00:00:00+00:00",
            updated_at="2026-06-30T00:00:00+00:00",
            concept=concept_id,
            definition=definition,
            confidence=0.8,
        )
