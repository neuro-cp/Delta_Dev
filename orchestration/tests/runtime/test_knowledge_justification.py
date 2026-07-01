from __future__ import annotations

from knowledge import (
    KnowledgeJustificationEngine,
    PredictionRecord,
    SemanticKnowledgeRecord,
    SemanticKnowledgeStore,
)
from knowledge.contradiction_record import ContradictionRecord


def _record(**overrides):
    base = {
        "concept_id": "concept-1",
        "created_at": "2026-06-30T00:00:00+00:00",
        "updated_at": "2026-06-30T00:00:00+00:00",
        "concept": "test claim",
        "definition": "A test claim is supported by evidence.",
        "confidence": 0.1,
        "supporting_evidence": ["m1", "m2"],
        "contradicting_evidence": [],
        "relationship_ids": ["r1"],
        "creation_source": "learning:l1",
    }
    base.update(overrides)
    return SemanticKnowledgeRecord(**base)


def test_confidence_is_derived_from_justification_not_prior_value():
    prediction = PredictionRecord(
        prediction_id="p1",
        created_at="2026-06-30T00:00:00+00:00",
        source_concept_id="concept-1",
        expectation="expect evidence",
        confidence=0.4,
        status="supported",
        supporting_observations=["m3"],
    )

    report = KnowledgeJustificationEngine().derive(
        _record(confidence=0.0),
        predictions=[prediction],
    )

    assert report.confidence > 0.35
    assert report.prediction_success_count == 1
    assert report.support_count == 2
    assert "support=2" in report.rationale


def test_counter_evidence_and_contradictions_lower_derived_confidence():
    contradiction = ContradictionRecord(
        contradiction_id="c1",
        created_at="2026-06-30T00:00:00+00:00",
        claim_a_id="concept-1",
        claim_b_id="concept-2",
        reason="test",
        severity=0.5,
    )
    failed_prediction = PredictionRecord(
        prediction_id="p1",
        created_at="2026-06-30T00:00:00+00:00",
        source_concept_id="concept-1",
        expectation="expect evidence",
        confidence=0.4,
        status="failed",
        failing_observations=["m3"],
    )

    report = KnowledgeJustificationEngine().derive(
        _record(contradicting_evidence=["m4"]),
        predictions=[failed_prediction],
        contradictions=[contradiction],
    )

    assert report.confidence < 0.35
    assert report.prediction_failure_count == 1
    assert report.contradiction_count == 1


def test_semantic_revision_appends_history_and_becomes_latest(tmp_path):
    store = SemanticKnowledgeStore(tmp_path / "knowledge.jsonl")
    original = store.add(_record())
    justification = KnowledgeJustificationEngine().derive(original)

    revision = store.add_revision(
        original,
        justification=justification,
        reason="derive confidence from justification",
    )

    assert revision.concept_id != original.concept_id
    assert original.concept_id in revision.revision_history
    assert revision.metadata["previous_concept_id"] == original.concept_id
    assert revision.metadata["justification"]["method"] == "evidence_justification_v1"
    assert store.latest() == [revision]
    assert store.all() == [original, revision]
