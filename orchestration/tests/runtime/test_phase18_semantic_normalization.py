from __future__ import annotations

from datetime import datetime, timezone

from knowledge import SemanticKnowledgeRecord, SemanticKnowledgeStore
from memory.persistent import MemoryStore
from knowledge.prediction_record import PredictionRecord
from knowledge.prediction_engine import PredictionEngine
from tools.phase18_semantic_normalization import normalize_text, run_normalization


def test_normalize_text_recovers_risk_likelihood_impact():
    result = normalize_text(
        "Likelihood refers to the probability of a risk",
        "Likelihood refers to the probability of a risk event occurring, while impact assesses the potential consequences if the risk materializes.",
    )

    assert result["normalized"] is True
    assert result["concept"] == "Risk assessment separates likelihood from impact"


def test_normalize_text_rejects_empty_scaffold():
    result = normalize_text(
        "Evidence that would change the answer could be",
        "Evidence that would change the answer could be.",
    )

    assert result["normalized"] is False


def test_phase18_normalization_revalidates_only_normalized_concepts(tmp_path):
    store_root = tmp_path / "phase15"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    memory = MemoryStore(store_root / "memory.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    now = datetime.now(timezone.utc).isoformat()
    record = knowledge.add(
        SemanticKnowledgeRecord(
            concept_id="concept-risk",
            created_at=now,
            updated_at=now,
            concept="Likelihood refers to the probability of a risk",
            definition=(
                "Likelihood refers to the probability of a risk event occurring, "
                "while impact assesses the potential consequences if the risk materializes."
            ),
            confidence=0.8,
            supporting_evidence=["seed"],
            creation_source="test",
            metadata={"cycle_id": "cycle-risk"},
        )
    )
    memory.add(
        kind="orchestration_output",
        text="Risk output",
        source="delta:llm",
        tags=["cycle", "output", "risk_assessment", "qwen2-5-7b-instruct-q4-k-m"],
        metadata={"cycle_id": "cycle-risk"},
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="prediction-risk",
                created_at=now,
                source_concept_id=record.concept_id,
                expectation="If relevant again, expect likelihood and impact.",
                confidence=0.5,
                status="failed",
                metadata={"concept": record.concept},
            )
        ]
    )
    phase17 = {
        "failed_predictions": [
            {
                "prediction_id": "prediction-risk",
                "source_concept_id": record.concept_id,
                "concept": record.concept,
            }
        ]
    }
    reports_dir.mkdir(parents=True)
    (reports_dir / "phase17_validation_report.json").write_text(
        __import__("json").dumps(phase17),
        encoding="utf-8",
    )

    summary = run_normalization(
        store_root=store_root,
        reports_dir=reports_dir,
        max_items=1,
    )

    assert summary["normalized_concepts"] == 1
    assert summary["recovered_concepts"] == 1
    assert summary["normalization_precision"] == 1.0
    assert summary["revalidation_records"][0]["source_provider"] == "qwen"
    assert summary["revalidation_records"][0]["source_profile"] == "risk_assessment"
    assert summary["revalidation_records"][0]["validation_changed_outcome"] is True
    assert (reports_dir / "phase18_normalization_report.md").exists()
