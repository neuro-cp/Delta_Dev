from __future__ import annotations

from knowledge import PredictionEngine, PredictionRecord
from memory.persistent import MemoryStore


def test_prediction_validation_supports_structured_state_evidence(tmp_path):
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    memory = MemoryStore(tmp_path / "memory.jsonl")
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="prediction-1",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="concept-1",
                expectation="The contractor will finish Job #42 tomorrow.",
                confidence=0.6,
                metadata={
                    "expected_claims": [
                        {"subject": "job:42", "state": "completed"}
                    ]
                },
            )
        ]
    )
    observation = memory.add(
        text="Job #42 completed at 4:18 PM on June 30.",
        kind="observation",
        source="test",
    )

    validated = predictions.validate_against_observations([observation])

    assert len(validated) == 1
    assert validated[0].status == "supported"
    assert validated[0].supporting_observations == [observation.memory_id]
    assert validated[0].metadata["validation"]["method"] == "evidence_claim_score"
    assert validated[0].metadata["validation"]["score"] >= 0.65


def test_prediction_validation_fails_conflicting_structured_state(tmp_path):
    predictions = PredictionEngine(tmp_path / "predictions.jsonl")
    memory = MemoryStore(tmp_path / "memory.jsonl")
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="prediction-1",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="concept-1",
                expectation="Job #42 will be completed.",
                confidence=0.6,
                metadata={
                    "expected_claims": [
                        {"subject": "job:42", "state": "completed"}
                    ]
                },
            )
        ]
    )
    observation = memory.add(
        text="Job #42 was cancelled before work started.",
        kind="observation",
        source="test",
    )

    validated = predictions.validate_against_observations([observation])

    assert len(validated) == 1
    assert validated[0].status == "failed"
    assert validated[0].failing_observations == [observation.memory_id]
    assert validated[0].metadata["validation"]["outcome"] == "failed"
    assert validated[0].confidence < 0.6
