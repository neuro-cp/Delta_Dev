from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from knowledge.contradiction_record import ContradictionRecord
from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord


@dataclass(frozen=True)
class JustificationReport:
    confidence: float
    support_count: int
    counter_evidence_count: int
    validation_count: int
    prediction_success_count: int
    prediction_failure_count: int
    contradiction_count: int
    provenance_count: int
    rationale: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "support_count": self.support_count,
            "counter_evidence_count": self.counter_evidence_count,
            "validation_count": self.validation_count,
            "prediction_success_count": self.prediction_success_count,
            "prediction_failure_count": self.prediction_failure_count,
            "contradiction_count": self.contradiction_count,
            "provenance_count": self.provenance_count,
            "rationale": list(self.rationale),
            "derived_at": datetime.now(timezone.utc).isoformat(),
            "method": "evidence_justification_v1",
        }


class KnowledgeJustificationEngine:
    """
    Derive semantic confidence from evidence-backed justification.

    This is not a new cognitive region. It is a knowledge-layer policy utility:
    confidence is computed from preserved evidence, prediction outcomes,
    contradictions, and provenance instead of being treated as free mutable
    state.
    """

    def derive(
        self,
        record: SemanticKnowledgeRecord,
        *,
        predictions: Sequence[PredictionRecord] = (),
        contradictions: Sequence[ContradictionRecord] = (),
    ) -> JustificationReport:
        related_predictions = [
            prediction
            for prediction in predictions
            if prediction.source_concept_id == record.concept_id
        ]
        supporting_prediction_ids = set(
            self._metadata_list(record.metadata, "supporting_prediction_ids")
        )
        failing_prediction_ids = set(
            self._metadata_list(record.metadata, "failing_prediction_ids")
        )

        for prediction in related_predictions:
            if prediction.status in {"supported", "succeeded"}:
                supporting_prediction_ids.add(prediction.prediction_id)
            if prediction.status == "failed":
                failing_prediction_ids.add(prediction.prediction_id)

        related_contradictions = [
            contradiction
            for contradiction in contradictions
            if record.concept_id in {contradiction.claim_a_id, contradiction.claim_b_id}
        ]

        support_count = len(set(record.supporting_evidence))
        counter_evidence_count = len(set(record.contradicting_evidence))
        prediction_success_count = len(supporting_prediction_ids)
        prediction_failure_count = len(failing_prediction_ids)
        contradiction_count = len(related_contradictions)
        validation_count = prediction_success_count + prediction_failure_count
        provenance_count = len(
            [
                item
                for item in [
                    record.creation_source,
                    *record.supporting_evidence,
                    *record.relationship_ids,
                ]
                if item
            ]
        )

        score = 0.35
        score += min(0.25, support_count * 0.04)
        score += min(0.20, prediction_success_count * 0.08)
        score += min(0.10, provenance_count * 0.02)
        score -= min(0.20, counter_evidence_count * 0.06)
        score -= min(0.25, prediction_failure_count * 0.10)
        score -= min(0.20, contradiction_count * 0.05)
        confidence = round(max(0.0, min(1.0, score)), 4)

        rationale = [
            f"support={support_count}",
            f"counter_evidence={counter_evidence_count}",
            f"prediction_success={prediction_success_count}",
            f"prediction_failure={prediction_failure_count}",
            f"contradictions={contradiction_count}",
            f"provenance={provenance_count}",
        ]

        return JustificationReport(
            confidence=confidence,
            support_count=support_count,
            counter_evidence_count=counter_evidence_count,
            validation_count=validation_count,
            prediction_success_count=prediction_success_count,
            prediction_failure_count=prediction_failure_count,
            contradiction_count=contradiction_count,
            provenance_count=provenance_count,
            rationale=rationale,
        )

    @staticmethod
    def _metadata_list(metadata: dict[str, Any], key: str) -> list[str]:
        value = metadata.get(key, [])
        if isinstance(value, str):
            return [value]
        if isinstance(value, Iterable):
            return [str(item) for item in value]
        return []
