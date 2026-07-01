from __future__ import annotations

import hashlib
from functools import lru_cache
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord
from memory.relationships.relationship_record import RelationshipRecord
from memory.working_memory import WorkingMemoryContext


@dataclass(frozen=True)
class HypotheticalOutcome:
    option: str
    expected_outcome: str
    confidence: float
    risk: float
    supporting_prediction_ids: list[str] = field(default_factory=list)
    supporting_knowledge_ids: list[str] = field(default_factory=list)
    relationship_ids: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(frozen=True)
class SimulationReport:
    simulation_id: str
    generated_at: str
    cycle_id: str | None
    outcomes: list[HypotheticalOutcome]
    selected_basis: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SimulationRegion:
    """
    Evaluates hypothetical futures without executing or mutating state.

    Simulation is a cognitive-cycle participant. Planning may consume its
    reports later, but simulation itself never chooses or performs actions.
    """

    def simulate(
        self,
        *,
        options: Iterable[str],
        working_memory: WorkingMemoryContext | None = None,
        semantic_knowledge: Sequence[SemanticKnowledgeRecord] = (),
        relationships: Sequence[RelationshipRecord] = (),
        predictions: Sequence[PredictionRecord] = (),
        goals: Sequence[str] = (),
    ) -> SimulationReport:
        normalized_options = [
            str(option).strip()
            for option in options
            if str(option).strip()
        ]
        if not normalized_options:
            normalized_options = ["continue current cognitive cycle"]

        outcomes = [
            self._simulate_option(
                option=option,
                semantic_knowledge=semantic_knowledge,
                relationships=relationships,
                predictions=predictions,
                goals=goals,
            )
            for option in normalized_options
        ]

        return SimulationReport(
            simulation_id=self._stable_simulation_id(normalized_options),
            generated_at=datetime.now(timezone.utc).isoformat(),
            cycle_id=working_memory.cycle_id if working_memory else None,
            outcomes=outcomes,
            selected_basis="highest confidence adjusted for risk",
            metadata={
                "working_memory_item_count": (
                    len(working_memory.items) if working_memory else 0
                ),
                "option_count": len(outcomes),
                "goal_count": len(goals),
                "non_executing": True,
            },
        )

    def _simulate_option(
        self,
        *,
        option: str,
        semantic_knowledge: Sequence[SemanticKnowledgeRecord],
        relationships: Sequence[RelationshipRecord],
        predictions: Sequence[PredictionRecord],
        goals: Sequence[str],
    ) -> HypotheticalOutcome:
        option_tokens = self._tokens(option)
        matching_predictions = [
            prediction
            for prediction in predictions
            if option_tokens & self._tokens(prediction.expectation)
        ]
        matching_knowledge = [
            record
            for record in semantic_knowledge
            if option_tokens & self._tokens(record.concept + " " + record.definition)
        ]
        matching_relationships = [
            record
            for record in relationships
            if option_tokens
            & self._tokens(
                " ".join(
                    [
                        record.relationship_type,
                        record.evidence,
                        str(record.metadata),
                    ]
                )
            )
        ]

        prediction_confidence = self._average(
            prediction.confidence for prediction in matching_predictions
        )
        knowledge_confidence = self._average(
            record.confidence for record in matching_knowledge
        )
        relationship_confidence = self._average(
            record.confidence for record in matching_relationships
        )
        goal_alignment = self._goal_alignment(option_tokens, goals)

        evidence_count = (
            len(matching_predictions)
            + len(matching_knowledge)
            + len(matching_relationships)
        )
        confidence = min(
            1.0,
            0.2
            + prediction_confidence * 0.35
            + knowledge_confidence * 0.3
            + relationship_confidence * 0.15
            + goal_alignment * 0.1
            + min(0.1, evidence_count * 0.02),
        )
        risk = max(
            0.0,
            min(
                1.0,
                0.8
                - confidence * 0.45
                + (0.2 if not matching_predictions else 0.0)
                + (0.1 if not matching_knowledge else 0.0),
            ),
        )

        return HypotheticalOutcome(
            option=option,
            expected_outcome=self._expected_outcome(
                option=option,
                predictions=matching_predictions,
                knowledge=matching_knowledge,
            ),
            confidence=round(confidence, 4),
            risk=round(risk, 4),
            supporting_prediction_ids=[
                prediction.prediction_id for prediction in matching_predictions
            ],
            supporting_knowledge_ids=[
                record.concept_id for record in matching_knowledge
            ],
            relationship_ids=[
                record.relationship_id for record in matching_relationships
            ],
            rationale=(
                "Estimated from matching predictions, semantic knowledge, "
                "relationships, and goal alignment."
            ),
        )

    @staticmethod
    def _expected_outcome(
        *,
        option: str,
        predictions: Sequence[PredictionRecord],
        knowledge: Sequence[SemanticKnowledgeRecord],
    ) -> str:
        if predictions:
            return predictions[0].expectation
        if knowledge:
            return f"If '{option}' is chosen, expect: {knowledge[0].definition}"
        return f"If '{option}' is chosen, outcome is uncertain."

    @staticmethod
    def _goal_alignment(option_tokens: set[str], goals: Sequence[str]) -> float:
        if not goals:
            return 0.0
        scores = []
        for goal in goals:
            goal_tokens = SimulationRegion._tokens(goal)
            if not goal_tokens:
                continue
            scores.append(len(option_tokens & goal_tokens) / len(goal_tokens))
        return max(scores) if scores else 0.0

    @staticmethod
    def _average(values: Iterable[float]) -> float:
        items = [float(value) for value in values]
        if not items:
            return 0.0
        return sum(items) / len(items)

    @staticmethod
    @lru_cache(maxsize=8192)
    def _tokens(value: str) -> set[str]:
        return {
            token
            for token in "".join(
                char.lower() if char.isalnum() or char == "_" else " "
                for char in str(value)
            ).split()
            if token
        }

    @staticmethod
    def _stable_simulation_id(options: Sequence[str]) -> str:
        digest = hashlib.sha256("\n".join(options).encode("utf-8")).hexdigest()
        return "simulation:" + digest[:16]
