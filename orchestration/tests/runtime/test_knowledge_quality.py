from __future__ import annotations

from knowledge import (
    ContradictionRecord,
    KnowledgeQualityAnalyzer,
    PredictionRecord,
    SemanticKnowledgeRecord,
)
from memory.relationships import RelationshipRecord


def _record() -> SemanticKnowledgeRecord:
    return SemanticKnowledgeRecord(
        concept_id="concept-1",
        created_at="2026-06-30T00:00:00+00:00",
        updated_at="2026-06-30T00:00:00+00:00",
        concept="job completion",
        definition="Job #42 completed after inspection.",
        confidence=0.1,
        supporting_evidence=["obs-1", "obs-2"],
        contradicting_evidence=["obs-3"],
        relationship_ids=["rel-1"],
        creation_source="learning",
        last_validation="2026-06-30T00:01:00+00:00",
        revision_history=["concept-0"],
    )


def test_knowledge_quality_report_summarizes_justification_without_mutation():
    record = _record()
    report = KnowledgeQualityAnalyzer().analyze(
        record,
        predictions=[
            PredictionRecord(
                prediction_id="pred-1",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="concept-1",
                expectation="Job #42 will complete",
                confidence=0.7,
                status="supported",
            ),
            PredictionRecord(
                prediction_id="pred-2",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="concept-1",
                expectation="Job #42 will not complete",
                confidence=0.7,
                status="failed",
            ),
        ],
        contradictions=[
            ContradictionRecord(
                contradiction_id="contradiction-1",
                created_at="2026-06-30T00:00:00+00:00",
                claim_a_id="concept-1",
                claim_b_id="concept-2",
                reason="conflict",
                severity=0.5,
            )
        ],
        relationships=[
            RelationshipRecord(
                relationship_id="rel-1",
                created_at="2026-06-30T00:00:00+00:00",
                source_id="concept-1",
                target_id="concept-2",
                relationship_type="supports",
            )
        ],
    )

    assert report.concept_id == "concept-1"
    assert report.evidence_count == 2
    assert report.counter_evidence_count == 1
    assert report.relationship_count == 1
    assert report.prediction_success_count == 1
    assert report.prediction_failure_count == 1
    assert report.validation_count == 2
    assert report.revision_count == 1
    assert report.contradiction_count == 1
    assert report.derived_confidence != record.confidence
    assert report.uncertainty == round(1.0 - report.derived_confidence, 4)
    assert report.last_validated == record.last_validation


def test_knowledge_quality_analyzes_many_records():
    reports = KnowledgeQualityAnalyzer().analyze_many([_record()])

    assert len(reports) == 1
    assert reports[0].concept == "job completion"
