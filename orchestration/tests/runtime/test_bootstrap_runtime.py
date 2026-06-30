from __future__ import annotations

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from knowledge import (
    ContradictionEngine,
    PredictionEngine,
    SemanticConsolidationEngine,
    SemanticKnowledgeStore,
)
from knowledge.bootstrap import KnowledgeBootstrapper
from learning.region import LearningStore
from learning.region.learning_record import LearningRecord, SemanticCandidate
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.agency import GoalStore
from orchestration.loop.cognitive_loop import CognitiveLoop
from orchestration.runtime import CognitiveRuntime


class DummyRouter:
    def route(self, payload):
        return AIOutputBundle(
            role="assistant",
            mode="mock",
            payload={"raw_model_output": '{"answer": "runtime ok", "confidence": 0.7}'},
            confidence_band=0.7,
        )


def test_bootstrap_is_idempotent(tmp_path):
    memory = MemoryStore(tmp_path / "memory.jsonl")
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    goals = GoalStore(tmp_path / "goals.jsonl")
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    bootstrap = KnowledgeBootstrapper(
        semantic_store=knowledge,
        memory_store=memory,
        goal_store=goals,
        prediction_engine=predictions,
    )

    first = bootstrap.seed()
    second = bootstrap.seed()

    assert len(first["semantic_created"]) > 0
    assert len(second["semantic_created"]) == 0
    assert len(knowledge.latest()) == len(first["semantic_created"])
    assert len(goals.active()) == len(first["goals_created"])


def test_runtime_tick_records_event(tmp_path):
    memory = MemoryStore(tmp_path / "memory.jsonl")
    relationships = RelationshipStore(tmp_path / "relationships.jsonl")
    learning = LearningStore(tmp_path / "learning.jsonl")
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    contradictions = ContradictionEngine(tmp_path / "contradictions.jsonl")
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    goals = GoalStore(tmp_path / "goals.jsonl")
    KnowledgeBootstrapper(
        semantic_store=knowledge,
        memory_store=memory,
        goal_store=goals,
        prediction_engine=predictions,
    ).seed()

    runtime = CognitiveRuntime(
        loop=CognitiveLoop(
            model_router=DummyRouter(),
            enable_recall=False,
            enable_replay_prompt=False,
        ),
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
        goal_store=goals,
        event_path=tmp_path / "events.jsonl",
    )

    results = runtime.run(duration_seconds=30, interval_seconds=30, max_ticks=1)

    assert len(results) == 1
    assert (tmp_path / "events.jsonl").exists()
    assert results[0].agency["metadata"]["execution_authority"] is False


def test_consolidation_suppresses_duplicate_semantic_candidates(tmp_path):
    memory = MemoryStore(tmp_path / "memory.jsonl")
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    learning = LearningRecord(
        learning_id="learning-1",
        created_at="2026-06-30T00:00:00+00:00",
        cycle_id="cycle-1",
        semantic_candidates=[
            SemanticCandidate(
                text="Evidence supports confidence changes.",
                evidence_memory_ids=["m1"],
                confidence=0.8,
                rationale="test",
            )
        ],
    )
    engine = SemanticConsolidationEngine(
        semantic_store=knowledge,
        prediction_engine=predictions,
    )

    first = engine.consolidate([learning])
    second = engine.consolidate([learning])

    assert len(first["created"]) == 1
    assert len(second["created"]) == 0
    assert len(knowledge.latest()) == 1
    assert len(predictions.latest()) == 1


def test_prediction_validation_marks_supported_predictions(tmp_path):
    memory = MemoryStore(tmp_path / "memory.jsonl")
    knowledge = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    KnowledgeBootstrapper(
        semantic_store=knowledge,
        memory_store=memory,
        prediction_engine=predictions,
    ).seed()
    observation = memory.add(
        text="Confidence estimates how strongly Delta should rely on a claim.",
        kind="observation",
        source="test",
        tags=("test",),
    )

    validated = predictions.validate_against_observations([observation])

    assert validated
    assert any(record.status == "supported" for record in predictions.latest())
