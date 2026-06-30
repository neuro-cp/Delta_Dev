from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from knowledge.prediction_engine import PredictionEngine
from knowledge.semantic_record import SemanticKnowledgeRecord
from knowledge.semantic_store import SemanticKnowledgeStore
from memory.persistent import MemoryStore
from orchestration.agency import GoalStore


@dataclass(frozen=True)
class BootstrapConcept:
    concept: str
    definition: str
    confidence: float
    domain: str


FOUNDATIONAL_CONCEPTS: tuple[BootstrapConcept, ...] = (
    BootstrapConcept(
        concept="identity",
        definition="An identity is a stable reference to an entity across time, even while that entity changes.",
        confidence=0.82,
        domain="self_world",
    ),
    BootstrapConcept(
        concept="time",
        definition="Time orders events into before, during, and after; temporal order supports memory, prediction, and planning.",
        confidence=0.86,
        domain="world_model",
    ),
    BootstrapConcept(
        concept="object",
        definition="An object is a bounded thing that can have properties, persist across observations, and participate in relationships.",
        confidence=0.78,
        domain="world_model",
    ),
    BootstrapConcept(
        concept="cause and effect",
        definition="A cause is a condition or event that contributes to another event; effects can be uncertain and context dependent.",
        confidence=0.8,
        domain="world_model",
    ),
    BootstrapConcept(
        concept="evidence",
        definition="Evidence is information that supports or weakens a claim; stronger evidence should increase confidence with preserved provenance.",
        confidence=0.85,
        domain="knowledge",
    ),
    BootstrapConcept(
        concept="confidence",
        definition="Confidence estimates how strongly Delta should rely on a claim, prediction, plan, or memory under current evidence.",
        confidence=0.83,
        domain="knowledge",
    ),
    BootstrapConcept(
        concept="contradiction",
        definition="A contradiction is a conflict between claims that should be preserved, investigated, and resolved through better knowledge.",
        confidence=0.82,
        domain="knowledge",
    ),
    BootstrapConcept(
        concept="goal",
        definition="A goal is a desired future state with priority, urgency, expected value, effort, progress, and confidence.",
        confidence=0.84,
        domain="agency",
    ),
    BootstrapConcept(
        concept="action",
        definition="An action is an intentional change attempt; proposed actions require evaluation and bounded execution authority.",
        confidence=0.8,
        domain="agency",
    ),
    BootstrapConcept(
        concept="planning",
        definition="Planning compares possible strategies before action by estimating benefit, risk, uncertainty, and goal satisfaction.",
        confidence=0.82,
        domain="agency",
    ),
    BootstrapConcept(
        concept="prediction",
        definition="A prediction is an expected future observation generated from knowledge and later compared against outcomes.",
        confidence=0.82,
        domain="simulation",
    ),
    BootstrapConcept(
        concept="simulation",
        definition="Simulation evaluates hypothetical futures without executing them and should preserve evidence, confidence, and risk.",
        confidence=0.82,
        domain="simulation",
    ),
    BootstrapConcept(
        concept="learning",
        definition="Learning is the transformation of experience into better organization, confidence, relationships, goals, and knowledge.",
        confidence=0.84,
        domain="learning",
    ),
    BootstrapConcept(
        concept="language",
        definition="Language represents meaning through symbols and context; interpretation should remain grounded in evidence and task state.",
        confidence=0.76,
        domain="reasoning",
    ),
    BootstrapConcept(
        concept="number",
        definition="Numbers represent quantity, order, measurement, and comparison; numeric reasoning should preserve units and uncertainty.",
        confidence=0.8,
        domain="reasoning",
    ),
    BootstrapConcept(
        concept="curiosity",
        definition="Curiosity is pressure to investigate low confidence, unresolved contradictions, missing relationships, and failed predictions.",
        confidence=0.78,
        domain="motivation",
    ),
)


BOOTSTRAP_GOALS: tuple[str, ...] = (
    "Increase semantic knowledge coverage from foundational concepts.",
    "Investigate contradictions before relying on conflicting knowledge.",
    "Improve prediction accuracy by comparing expectations against later observations.",
    "Reduce uncertainty by turning repeated observations into semantic knowledge.",
)


class KnowledgeBootstrapper:
    """
    Seeds Delta with small foundational knowledge, not bulk facts.
    """

    def __init__(
        self,
        *,
        semantic_store: SemanticKnowledgeStore,
        memory_store: MemoryStore,
        goal_store: GoalStore | None = None,
        prediction_engine: PredictionEngine | None = None,
    ) -> None:
        self._semantic_store = semantic_store
        self._memory_store = memory_store
        self._goal_store = goal_store
        self._prediction_engine = prediction_engine

    def seed(self, concepts: Iterable[BootstrapConcept] = FOUNDATIONAL_CONCEPTS) -> dict:
        existing = {
            str(record.metadata.get("bootstrap_concept", "")).lower()
            for record in self._semantic_store.latest()
        }
        created = []
        predictions = []
        now = datetime.now(timezone.utc).isoformat()

        for concept in concepts:
            if concept.concept.lower() in existing:
                continue
            memory = self._memory_store.add(
                text=f"Bootstrap concept: {concept.concept}. {concept.definition}",
                kind="bootstrap_observation",
                source="delta:bootstrap",
                layer="experience",
                confidence=concept.confidence,
                tags=("bootstrap", concept.domain),
                metadata={"bootstrap_concept": concept.concept},
            )
            record = SemanticKnowledgeRecord(
                concept_id=str(uuid.uuid4()),
                created_at=now,
                updated_at=now,
                concept=concept.concept,
                definition=concept.definition,
                confidence=concept.confidence,
                supporting_evidence=[memory.memory_id],
                creation_source="bootstrap:foundational",
                metadata={
                    "bootstrap_concept": concept.concept,
                    "domain": concept.domain,
                },
            )
            self._semantic_store.add(record)
            created.append(record)

            if self._prediction_engine is not None:
                prediction = self._prediction_engine.generate_for(record)
                if prediction is not None:
                    self._prediction_engine.add_all([prediction])
                    predictions.append(prediction)

        goals = []
        if self._goal_store is not None:
            existing_goals = {goal.description for goal in self._goal_store.latest()}
            for description in BOOTSTRAP_GOALS:
                if description in existing_goals:
                    continue
                goals.append(
                    self._goal_store.create(
                        description=description,
                        origin="bootstrap",
                        priority=0.62,
                        urgency=0.35,
                        expected_value=0.75,
                        estimated_effort=0.45,
                        confidence=0.7,
                        metadata={"bootstrap": True},
                    )
                )

        return {
            "semantic_created": created,
            "predictions_created": predictions,
            "goals_created": goals,
        }
