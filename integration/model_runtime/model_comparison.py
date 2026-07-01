from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from integration.model_runtime.inference_types import CanonicalInferenceResult


@dataclass(frozen=True)
class ModelComparisonReport:
    compared_model_ids: list[str]
    agreement_score: float
    confidence_spread: float
    latency_spread: float
    evidence_counts: dict[str, int]
    consensus_answer: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelComparisonEngine:
    """
    Compare canonical model outputs without averaging away disagreements.
    """

    def compare(
        self,
        results: Sequence[CanonicalInferenceResult],
    ) -> ModelComparisonReport:
        items = list(results)
        if not items:
            return ModelComparisonReport(
                compared_model_ids=[],
                agreement_score=0.0,
                confidence_spread=0.0,
                latency_spread=0.0,
                evidence_counts={},
                consensus_answer=None,
                metadata={"empty": True},
            )

        answers = [self._normalize(item.answer) for item in items]
        majority_answer = max(set(answers), key=answers.count)
        agreement_score = round(answers.count(majority_answer) / len(answers), 4)
        confidences = [float(item.confidence) for item in items]
        latencies = [float(item.latency_seconds) for item in items]
        evidence_counts = {item.model_id: len(item.evidence) for item in items}

        consensus_answer = None
        if agreement_score > 0.5:
            for item in items:
                if self._normalize(item.answer) == majority_answer:
                    consensus_answer = item.answer
                    break

        return ModelComparisonReport(
            compared_model_ids=[item.model_id for item in items],
            agreement_score=agreement_score,
            confidence_spread=round(max(confidences) - min(confidences), 4),
            latency_spread=round(max(latencies) - min(latencies), 4),
            evidence_counts=evidence_counts,
            consensus_answer=consensus_answer,
            metadata={
                "method": "canonical_inference_comparison_v1",
                "disagreement": agreement_score < 1.0,
            },
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(str(value).strip().lower().split())
