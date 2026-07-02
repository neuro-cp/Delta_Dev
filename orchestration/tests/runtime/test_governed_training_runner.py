from __future__ import annotations

from tools.governed_training_run import saturation_status


def test_saturation_status_detects_exhausted_repetitive_window():
    history = [
        {
            "objective_id": "same-objective",
            "semantic_knowledge": 10,
            "prediction_quality_score": 0.5,
        }
        for _ in range(20)
    ]
    history[-1]["semantic_knowledge"] = 11
    history[-1]["prediction_quality_score"] = 0.51

    status = saturation_status(
        history,
        window=20,
        min_semantic_delta=2,
        min_prediction_quality_delta=0.05,
        repetition_threshold=0.75,
    )

    assert status["saturated"] is True
    assert status["reason"] == "learning_saturation"


def test_saturation_status_allows_recent_semantic_growth():
    history = [
        {
            "objective_id": f"objective-{index % 4}",
            "semantic_knowledge": 10 + index,
            "prediction_quality_score": 0.5,
        }
        for index in range(20)
    ]

    status = saturation_status(
        history,
        window=20,
        min_semantic_delta=2,
        min_prediction_quality_delta=0.05,
        repetition_threshold=0.75,
    )

    assert status["saturated"] is False
