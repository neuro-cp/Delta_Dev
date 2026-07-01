from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from knowledge.quality_analyzer import KnowledgeQualityReport


@dataclass(frozen=True)
class KnowledgeDistillationReport:
    stable_concepts: list[str]
    weak_concepts: list[str]
    discarded_concepts: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeDistiller:
    """
    Read-only distillation report for stable and weak knowledge.
    """

    def distill(
        self,
        reports: Sequence[KnowledgeQualityReport],
        *,
        stable_confidence_threshold: float = 0.75,
        weak_confidence_threshold: float = 0.45,
        min_evidence: int = 2,
        min_validations: int = 1,
    ) -> KnowledgeDistillationReport:
        stable: list[str] = []
        weak: list[str] = []
        discarded: list[str] = []
        for report in reports:
            if (
                report.derived_confidence >= stable_confidence_threshold
                and report.evidence_count >= min_evidence
                and report.validation_count >= min_validations
                and report.prediction_failure_count == 0
                and report.contradiction_count == 0
            ):
                stable.append(report.concept_id)
            elif report.derived_confidence < weak_confidence_threshold:
                weak.append(report.concept_id)
                if report.evidence_count == 0 and report.validation_count == 0:
                    discarded.append(report.concept_id)

        return KnowledgeDistillationReport(
            stable_concepts=stable,
            weak_concepts=weak,
            discarded_concepts=discarded,
            metadata={
                "method": "knowledge_distillation_report_v1",
                "read_only": True,
                "stable_confidence_threshold": stable_confidence_threshold,
                "weak_confidence_threshold": weak_confidence_threshold,
                "min_evidence": min_evidence,
                "min_validations": min_validations,
            },
        )
