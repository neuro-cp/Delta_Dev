from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

from integration.model_runtime.model_registry import list_available_models
from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord
from learning.region import LearningStore
from learning.region.learning_record import LearningRecord
from memory.persistent import MemoryRecord, MemoryStore
from memory.relationships import RelationshipStore


@dataclass(frozen=True)
class CognitiveMetrics:
    generated_at: str
    experience_count: int
    semantic_knowledge_count: int
    relationship_count: int
    contradiction_count: int
    prediction_count: int
    open_prediction_count: int
    learning_record_count: int
    recent_learning_count: int
    reflection_count: int
    recent_reflection_count: int
    average_memory_confidence: float
    average_knowledge_confidence: float
    average_prediction_confidence: float
    relationship_density: float
    consolidation_rate: float
    prediction_accuracy: float | None
    working_memory_utilization: float | None
    attention_distribution: dict[str, int]
    temporal: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SelfModelSnapshot:
    generated_at: str
    identity: dict[str, Any]
    capabilities: list[str]
    limitations: list[str]
    knowledge_coverage: dict[str, Any]
    confidence_distribution: dict[str, Any]
    predictions: dict[str, Any]
    contradictions: dict[str, Any]
    learning: dict[str, Any]
    temporal_continuity: dict[str, Any]
    subsystem_health: dict[str, Any]
    cognitive_health: dict[str, Any]
    self_observations: list[dict[str, Any]]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CognitiveHealthEvaluator:
    """
    Generates health indicators from existing state.

    Health is descriptive only. It does not mutate stores or authorize action.
    """

    def evaluate(self, metrics: CognitiveMetrics) -> dict[str, Any]:
        contradiction_pressure = self._ratio(
            metrics.contradiction_count,
            max(1, metrics.semantic_knowledge_count),
        )
        fragmentation = 1.0 - min(1.0, metrics.relationship_density)
        prediction_quality = (
            metrics.prediction_accuracy
            if metrics.prediction_accuracy is not None
            else "unknown"
        )
        learning_efficiency = min(1.0, metrics.consolidation_rate)
        reflection_coverage = self._ratio(
            metrics.reflection_count,
            max(1, metrics.experience_count),
        )

        warnings: list[str] = []
        if contradiction_pressure > 0.25:
            warnings.append("contradiction pressure is high")
        if metrics.semantic_knowledge_count == 0 and metrics.learning_record_count > 0:
            warnings.append("learning records are not yet consolidating into knowledge")
        if metrics.open_prediction_count > 0 and metrics.prediction_accuracy is None:
            warnings.append("open predictions exist but are not yet evaluated")
        if metrics.relationship_density < 0.25 and metrics.experience_count > 4:
            warnings.append("experience memory is sparsely related")

        return {
            "fragmentation": round(fragmentation, 4),
            "contradiction_pressure": round(contradiction_pressure, 4),
            "knowledge_stability": round(1.0 - min(1.0, contradiction_pressure), 4),
            "goal_overload": "unknown",
            "memory_growth": metrics.temporal.get("today", {}).get("experience_count", 0),
            "prediction_quality": prediction_quality,
            "learning_efficiency": round(learning_efficiency, 4),
            "reflection_coverage": round(reflection_coverage, 4),
            "warnings": warnings,
        }

    @staticmethod
    def _ratio(numerator: int | float, denominator: int | float) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator) / float(denominator)


class SelfModelRegion:
    """
    Builds Delta's self-model from canonical stores.

    The report is generated automatically from existing regions rather than
    maintained as a second source of truth.
    """

    def __init__(
        self,
        *,
        memory_store: MemoryStore,
        relationship_store: RelationshipStore,
        learning_store: LearningStore,
        semantic_store: SemanticKnowledgeStore,
        contradiction_engine: ContradictionEngine,
        prediction_engine: PredictionEngine,
        health_evaluator: CognitiveHealthEvaluator | None = None,
    ) -> None:
        self._memory_store = memory_store
        self._relationship_store = relationship_store
        self._learning_store = learning_store
        self._semantic_store = semantic_store
        self._contradiction_engine = contradiction_engine
        self._prediction_engine = prediction_engine
        self._health_evaluator = health_evaluator or CognitiveHealthEvaluator()

    def generate(self) -> SelfModelSnapshot:
        now = datetime.now(timezone.utc)
        memories = self._memory_store.all()
        relationships = self._relationship_store.all()
        learning = self._learning_store.all()
        knowledge = self._semantic_store.latest()
        contradictions = self._contradiction_engine.all()
        predictions = self._prediction_engine.latest()

        metrics = self._metrics(
            now=now,
            memories=memories,
            relationships=relationships,
            learning=learning,
            knowledge=knowledge,
            predictions=predictions,
            contradiction_count=len(contradictions),
        )
        cognitive_health = self._health_evaluator.evaluate(metrics)
        subsystem_health = self._subsystem_health(
            memories=memories,
            relationships=relationships,
            learning=learning,
            knowledge=knowledge,
            predictions=predictions,
            contradiction_count=len(contradictions),
        )

        self_observations = self._self_observations(
            metrics=metrics,
            cognitive_health=cognitive_health,
        )
        available_models = list_available_models()

        return SelfModelSnapshot(
            generated_at=now.isoformat(),
            identity={
                "name": "Delta",
                "type": "persistent cognitive substrate",
                "continuity_source": "append-only state and generated reports",
            },
            capabilities=[
                "run one explicit cognitive cycle",
                "store immutable experience records",
                "rank recalled memories through attention",
                "assemble per-cycle working memory",
                "emit structured reflection and learning records",
                "consolidate semantic knowledge from learning records",
                "generate predictions from confident semantic knowledge",
                "validate predictions through append-only evidence records",
                "track explicit goals, proposed plans, and agency proposals",
                "run bounded cognitive runtime ticks",
                "generate self-model metrics from existing regions",
            ],
            limitations=[
                "goal progress feedback is not yet implemented",
                "planning is proposal-only and non-executing",
                "prediction evaluation is shallow token-overlap validation",
                "confidence evolution is proposal-based only",
                "attention has no durable decay model yet",
                "self-model is generated on demand, not continuously scheduled",
            ],
            knowledge_coverage={
                "semantic_records": len(knowledge),
                "concepts": [record.concept for record in knowledge[-10:]],
                "coverage_note": "coverage is inferred from explicit semantic records only",
            },
            confidence_distribution=self._confidence_distribution(
                memories=memories,
                knowledge=knowledge,
                predictions=predictions,
            ),
            predictions={
                "total": len(predictions),
                "open": metrics.open_prediction_count,
                "accuracy": metrics.prediction_accuracy,
                "recent": [prediction.prediction_id for prediction in predictions[-10:]],
            },
            contradictions={
                "total": len(contradictions),
                "pressure": cognitive_health["contradiction_pressure"],
            },
            learning={
                "records": len(learning),
                "recent_records": metrics.recent_learning_count,
                "recent_questions": [
                    question
                    for record in learning[-5:]
                    for question in record.questions[:3]
                ],
            },
            temporal_continuity=metrics.temporal,
            subsystem_health=subsystem_health,
            cognitive_health=cognitive_health,
            self_observations=self_observations,
            metrics=metrics.to_dict(),
        )

    def _metrics(
        self,
        *,
        now: datetime,
        memories: Sequence[MemoryRecord],
        relationships: Sequence[Any],
        learning: Sequence[LearningRecord],
        knowledge: Sequence[SemanticKnowledgeRecord],
        predictions: Sequence[PredictionRecord],
        contradiction_count: int,
    ) -> CognitiveMetrics:
        open_predictions = [
            prediction
            for prediction in predictions
            if prediction.status == "open"
        ]
        evaluated_predictions = [
            prediction
            for prediction in predictions
            if prediction.status in {"supported", "succeeded", "failed"}
        ]
        succeeded_predictions = [
            prediction
            for prediction in evaluated_predictions
            if prediction.status in {"supported", "succeeded"}
        ]
        temporal = self._temporal_summary(now, memories, learning)

        return CognitiveMetrics(
            generated_at=now.isoformat(),
            experience_count=len(memories),
            semantic_knowledge_count=len(knowledge),
            relationship_count=len(relationships),
            contradiction_count=contradiction_count,
            prediction_count=len(predictions),
            open_prediction_count=len(open_predictions),
            learning_record_count=len(learning),
            recent_learning_count=temporal["today"]["learning_count"],
            reflection_count=len(learning),
            recent_reflection_count=temporal["today"]["learning_count"],
            average_memory_confidence=self._average(
                record.confidence for record in memories
            ),
            average_knowledge_confidence=self._average(
                record.confidence for record in knowledge
            ),
            average_prediction_confidence=self._average(
                record.confidence for record in predictions
            ),
            relationship_density=self._ratio(len(relationships), max(1, len(memories))),
            consolidation_rate=self._ratio(len(knowledge), max(1, len(learning))),
            prediction_accuracy=(
                self._ratio(len(succeeded_predictions), len(evaluated_predictions))
                if evaluated_predictions
                else None
            ),
            working_memory_utilization=None,
            attention_distribution=self._attention_distribution(memories),
            temporal=temporal,
        )

    def _temporal_summary(
        self,
        now: datetime,
        memories: Sequence[MemoryRecord],
        learning: Sequence[LearningRecord],
    ) -> dict[str, Any]:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        memory_times = [
            parsed
            for parsed in (self._parse_time(record.created_at) for record in memories)
            if parsed is not None
        ]
        learning_times = [
            parsed
            for parsed in (self._parse_time(record.created_at) for record in learning)
            if parsed is not None
        ]

        return {
            "today": {
                "experience_count": self._count_since(memory_times, today_start),
                "learning_count": self._count_since(learning_times, today_start),
            },
            "last_7_days": {
                "experience_count": self._count_since(memory_times, week_start),
                "learning_count": self._count_since(learning_times, week_start),
            },
            "history": {
                "first_experience_at": (
                    min(memory_times).isoformat() if memory_times else None
                ),
                "latest_experience_at": (
                    max(memory_times).isoformat() if memory_times else None
                ),
                "first_learning_at": (
                    min(learning_times).isoformat() if learning_times else None
                ),
                "latest_learning_at": (
                    max(learning_times).isoformat() if learning_times else None
                ),
            },
        }

    @staticmethod
    def _subsystem_health(
        *,
        memories: Sequence[MemoryRecord],
        relationships: Sequence[Any],
        learning: Sequence[LearningRecord],
        knowledge: Sequence[SemanticKnowledgeRecord],
        predictions: Sequence[PredictionRecord],
        contradiction_count: int,
    ) -> dict[str, Any]:
        return {
            "memory": {"status": "active" if memories else "empty"},
            "relationships": {"status": "active" if relationships else "empty"},
            "learning": {"status": "active" if learning else "empty"},
            "knowledge": {"status": "active" if knowledge else "empty"},
            "predictions": {"status": "active" if predictions else "empty"},
            "contradictions": {
                "status": "pressurized" if contradiction_count else "clear"
            },
            "goals": {"status": "proposal_layer"},
            "planning": {"status": "proposal_layer"},
        }

    @staticmethod
    def _confidence_distribution(
        *,
        memories: Sequence[MemoryRecord],
        knowledge: Sequence[SemanticKnowledgeRecord],
        predictions: Sequence[PredictionRecord],
    ) -> dict[str, Any]:
        return {
            "memory": SelfModelRegion._bucket_confidence(
                record.confidence for record in memories
            ),
            "semantic_knowledge": SelfModelRegion._bucket_confidence(
                record.confidence for record in knowledge
            ),
            "predictions": SelfModelRegion._bucket_confidence(
                record.confidence for record in predictions
            ),
        }

    @staticmethod
    def _bucket_confidence(values: Iterable[float]) -> dict[str, int]:
        buckets = {"low": 0, "medium": 0, "high": 0}
        for value in values:
            if value < 0.4:
                buckets["low"] += 1
            elif value < 0.75:
                buckets["medium"] += 1
            else:
                buckets["high"] += 1
        return buckets

    @staticmethod
    def _attention_distribution(memories: Sequence[MemoryRecord]) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for record in memories:
            for tag in record.tags:
                distribution[tag] = distribution.get(tag, 0) + 1
        return dict(sorted(distribution.items()))

    @staticmethod
    def _self_observations(
        *,
        metrics: CognitiveMetrics,
        cognitive_health: dict[str, Any],
    ) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        if metrics.learning_record_count and not metrics.semantic_knowledge_count:
            observations.append(
                {
                    "kind": "learning_without_consolidation",
                    "summary": "Learning records exist but semantic knowledge is empty.",
                    "severity": "medium",
                }
            )
        if metrics.open_prediction_count and metrics.prediction_accuracy is None:
            observations.append(
                {
                    "kind": "prediction_evaluation_gap",
                    "summary": "Predictions exist, but no prediction outcomes have been evaluated.",
                    "severity": "medium",
                }
            )
        if cognitive_health["fragmentation"] > 0.75 and metrics.experience_count > 4:
            observations.append(
                {
                    "kind": "memory_fragmentation",
                    "summary": "Experience memory has low relationship density.",
                    "severity": "low",
                }
            )
        if not observations:
            observations.append(
                {
                    "kind": "baseline",
                    "summary": "No high-pressure self-model warnings were generated.",
                    "severity": "info",
                }
            )
        return observations

    @staticmethod
    def _average(values: Iterable[float]) -> float:
        items = [float(value) for value in values]
        if not items:
            return 0.0
        return round(sum(items) / len(items), 4)

    @staticmethod
    def _ratio(numerator: int | float, denominator: int | float) -> float:
        if denominator <= 0:
            return 0.0
        return round(float(numerator) / float(denominator), 4)

    @staticmethod
    def _count_since(times: Sequence[datetime], start: datetime) -> int:
        return sum(1 for item in times if item >= start)

    @staticmethod
    def _parse_time(value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
