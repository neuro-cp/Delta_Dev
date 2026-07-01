from __future__ import annotations

from knowledge import PredictionEngine, PredictionRecord


def test_prediction_quality_metrics_summarize_latest_prediction_state(tmp_path):
    engine = PredictionEngine(tmp_path / "predictions.jsonl")
    engine.add_all(
        [
            PredictionRecord(
                prediction_id="p1",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="c1",
                expectation="supported",
                confidence=0.7,
                status="supported",
                metadata={"validation": {"score": 0.8}},
            ),
            PredictionRecord(
                prediction_id="p2",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="c2",
                expectation="failed",
                confidence=0.4,
                status="failed",
                metadata={"validation": {"score": 0.6}},
            ),
            PredictionRecord(
                prediction_id="p3",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="c3",
                expectation="open",
                confidence=0.5,
            ),
        ]
    )

    metrics = engine.quality_metrics()

    assert metrics["total"] == 3
    assert metrics["open"] == 1
    assert metrics["evaluated"] == 2
    assert metrics["supported"] == 1
    assert metrics["failed"] == 1
    assert metrics["accuracy"] == 0.5
    assert metrics["coverage"] == 0.6667
    assert metrics["failure_rate"] == 0.5
    assert metrics["average_evidence_score"] == 0.7


def test_prediction_quality_metrics_use_latest_revisions(tmp_path):
    engine = PredictionEngine(tmp_path / "predictions.jsonl")
    engine.add_all(
        [
            PredictionRecord(
                prediction_id="p1",
                created_at="2026-06-30T00:00:00+00:00",
                source_concept_id="c1",
                expectation="open",
                confidence=0.5,
                status="open",
            ),
            PredictionRecord(
                prediction_id="p1",
                created_at="2026-06-30T00:01:00+00:00",
                source_concept_id="c1",
                expectation="open",
                confidence=0.55,
                status="supported",
                metadata={"validation": {"score": 0.9}},
            ),
        ]
    )

    metrics = engine.quality_metrics()

    assert metrics["total"] == 1
    assert metrics["open"] == 0
    assert metrics["evaluated"] == 1
    assert metrics["accuracy"] == 1.0
