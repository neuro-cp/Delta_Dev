from __future__ import annotations

from knowledge import KnowledgeDistiller, KnowledgeQualityReport


def _report(
    concept_id: str,
    *,
    confidence: float,
    evidence: int,
    validations: int,
    failures: int = 0,
    contradictions: int = 0,
) -> KnowledgeQualityReport:
    return KnowledgeQualityReport(
        concept_id=concept_id,
        concept=concept_id,
        evidence_count=evidence,
        counter_evidence_count=0,
        relationship_count=0,
        prediction_success_count=max(0, validations - failures),
        prediction_failure_count=failures,
        validation_count=validations,
        revision_count=0,
        contradiction_count=contradictions,
        derived_confidence=confidence,
        uncertainty=round(1.0 - confidence, 4),
    )


def test_knowledge_distiller_identifies_stable_and_weak_concepts_without_mutation():
    report = KnowledgeDistiller().distill(
        [
            _report("stable", confidence=0.9, evidence=3, validations=2),
            _report("weak", confidence=0.3, evidence=1, validations=0),
            _report("unsupported", confidence=0.2, evidence=0, validations=0),
            _report("conflicted", confidence=0.9, evidence=3, validations=2, contradictions=1),
        ]
    )

    assert report.stable_concepts == ["stable"]
    assert report.weak_concepts == ["weak", "unsupported"]
    assert report.discarded_concepts == ["unsupported"]
    assert report.metadata["read_only"] is True
