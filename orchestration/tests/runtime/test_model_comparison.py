from __future__ import annotations

from integration.model_runtime import CanonicalInferenceResult, ModelComparisonEngine


def _result(model_id: str, answer: str, confidence: float, latency: float, evidence=None):
    return CanonicalInferenceResult(
        provider="mock",
        model_id=model_id,
        answer=answer,
        raw_output=answer,
        confidence=confidence,
        latency_seconds=latency,
        prompt_tokens=4,
        response_tokens=3,
        evidence=list(evidence or []),
    )


def test_model_comparison_reports_majority_agreement_without_averaging_outputs():
    report = ModelComparisonEngine().compare(
        [
            _result("phi3", "Delta should validate evidence.", 0.7, 1.0, ["e1"]),
            _result("phi4", "Delta should validate evidence.", 0.8, 2.0, ["e1", "e2"]),
            _result("qwen", "Delta should ask a human.", 0.6, 3.0),
        ]
    )

    assert report.compared_model_ids == ["phi3", "phi4", "qwen"]
    assert report.agreement_score == 0.6667
    assert report.confidence_spread == 0.2
    assert report.latency_spread == 2.0
    assert report.consensus_answer == "Delta should validate evidence."
    assert report.evidence_counts == {"phi3": 1, "phi4": 2, "qwen": 0}
    assert report.metadata["disagreement"] is True


def test_model_comparison_keeps_consensus_empty_without_majority():
    report = ModelComparisonEngine().compare(
        [
            _result("phi3", "A", 0.7, 1.0),
            _result("phi4", "B", 0.8, 2.0),
        ]
    )

    assert report.agreement_score == 0.5
    assert report.consensus_answer is None


def test_model_comparison_handles_empty_inputs():
    report = ModelComparisonEngine().compare([])

    assert report.compared_model_ids == []
    assert report.agreement_score == 0.0
    assert report.metadata["empty"] is True
