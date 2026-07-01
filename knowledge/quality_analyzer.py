from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from knowledge.contradiction_record import ContradictionRecord
from knowledge.justification_engine import KnowledgeJustificationEngine
from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord
from memory.relationships import RelationshipRecord


@dataclass(frozen=True)
class KnowledgeQualityReport:
    concept_id: str
    concept: str
    evidence_count: int
    counter_evidence_count: int
    relationship_count: int
    prediction_success_count: int
    prediction_failure_count: int
    validation_count: int
    revision_count: int
    contradiction_count: int
    derived_confidence: float
    uncertainty: float
    last_validated: str | None = None
    justification: dict[str, Any] = field(default_factory=dict)


class KnowledgeQualityAnalyzer:
    """
    Read-only knowledge quality analysis.

    Quality reports summarize why a knowledge record is currently justified.
    They do not rewrite semantic records or promote new knowledge.
    """

    def __init__(
        self,
        *,
        justification_engine: KnowledgeJustificationEngine | None = None,
    ) -> None:
        self._justification = justification_engine or KnowledgeJustificationEngine()

    def analyze(
        self,
        record: SemanticKnowledgeRecord,
        *,
        predictions: Sequence[PredictionRecord] = (),
        contradictions: Sequence[ContradictionRecord] = (),
        relationships: Sequence[RelationshipRecord] = (),
    ) -> KnowledgeQualityReport:
        related_predictions = [
            prediction
            for prediction in predictions
            if prediction.source_concept_id == record.concept_id
        ]
        related_relationships = [
            relationship
            for relationship in relationships
            if record.concept_id in {relationship.source_id, relationship.target_id}
            or relationship.relationship_id in record.relationship_ids
        ]
        related_contradictions = [
            contradiction
            for contradiction in contradictions
            if record.concept_id in {contradiction.claim_a_id, contradiction.claim_b_id}
        ]
        justification = self._justification.derive(
            record,
            predictions=predictions,
            contradictions=contradictions,
        )
        validation_count = len(
            [
                prediction
                for prediction in related_predictions
                if prediction.status in {"supported", "succeeded", "failed"}
            ]
        )

        return KnowledgeQualityReport(
            concept_id=record.concept_id,
            concept=record.concept,
            evidence_count=len(set(record.supporting_evidence)),
            counter_evidence_count=len(set(record.contradicting_evidence)),
            relationship_count=len({item.relationship_id for item in related_relationships}),
            prediction_success_count=len(
                [
                    prediction
                    for prediction in related_predictions
                    if prediction.status in {"supported", "succeeded"}
                ]
            ),
            prediction_failure_count=len(
                [
                    prediction
                    for prediction in related_predictions
                    if prediction.status == "failed"
                ]
            ),
            validation_count=validation_count,
            revision_count=len(set(record.revision_history)),
            contradiction_count=len(related_contradictions),
            derived_confidence=justification.confidence,
            uncertainty=round(1.0 - justification.confidence, 4),
            last_validated=record.last_validation,
            justification=justification.to_metadata(),
        )

    def analyze_many(
        self,
        records: Sequence[SemanticKnowledgeRecord],
        *,
        predictions: Sequence[PredictionRecord] = (),
        contradictions: Sequence[ContradictionRecord] = (),
        relationships: Sequence[RelationshipRecord] = (),
    ) -> list[KnowledgeQualityReport]:
        return [
            self.analyze(
                record,
                predictions=predictions,
                contradictions=contradictions,
                relationships=relationships,
            )
            for record in records
        ]
