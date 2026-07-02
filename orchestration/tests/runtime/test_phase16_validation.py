from __future__ import annotations

from datetime import datetime, timezone

from knowledge import PredictionEngine, SemanticKnowledgeRecord, SemanticKnowledgeStore
from knowledge.prediction_record import PredictionRecord
from tools.phase16_validation import run_validation


def test_phase16_validation_writes_reports_and_revises_predictions(tmp_path):
    store_root = tmp_path / "phase15"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    now = datetime.now(timezone.utc).isoformat()

    record = knowledge.add(
        SemanticKnowledgeRecord(
            concept_id="concept-1",
            created_at=now,
            updated_at=now,
            concept="evidence supports reusable planning",
            definition=(
                "Reusable planning concepts should connect evidence, constraints, "
                "prediction, and revision."
            ),
            confidence=0.6,
            supporting_evidence=["seed"],
            creation_source="test",
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="prediction-1",
                created_at=now,
                source_concept_id=record.concept_id,
                expectation="If relevant again, expect reusable planning concepts.",
                confidence=0.5,
                metadata={"concept": record.concept},
            )
        ]
    )

    summary = run_validation(
        store_root=store_root,
        max_predictions=1,
        reports_dir=reports_dir,
    )

    assert summary["validations_recorded"] == 1
    assert summary["after_prediction_quality"]["open"] == 0
    assert (reports_dir / "phase16_validation_report.json").exists()
    assert (reports_dir / "phase16_validation_report.md").exists()
    assert len(knowledge.latest()) == 1
    assert len(knowledge.all()) == 2
