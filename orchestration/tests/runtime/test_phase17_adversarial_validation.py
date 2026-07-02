from __future__ import annotations

from datetime import datetime, timezone

from knowledge import PredictionEngine, SemanticKnowledgeRecord, SemanticKnowledgeStore
from knowledge.prediction_record import PredictionRecord
from tools.phase17_adversarial_validation import run_adversarial_validation


def test_phase17_adversarial_validation_can_fail_prompt_shaped_prediction(tmp_path):
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
            concept="The evidence that would change the answer",
            definition=(
                "The evidence that would change the answer would be more evidence "
                "that changes the answer."
            ),
            confidence=0.8,
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
                expectation="If relevant again, expect prompt-shaped evidence wording.",
                confidence=0.64,
                metadata={"concept": record.concept},
            )
        ]
    )

    summary = run_adversarial_validation(
        store_root=store_root,
        max_predictions=1,
        reports_dir=reports_dir,
    )

    assert summary["validation_status_counts"]["failed"] == 1
    assert summary["after_prediction_quality"]["failed"] == 1
    assert summary["confidence_changes"]["largest_loss"] < 0
    assert (reports_dir / "phase17_validation_report.md").exists()
    assert (reports_dir / "prediction_revision_report.md").exists()
