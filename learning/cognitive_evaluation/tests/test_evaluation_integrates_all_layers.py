from learning.cognitive_evaluation.cognitive_evaluation_engine import CognitiveEvaluationEngine

def test_evaluation_integrates_all_layers():
    engine = CognitiveEvaluationEngine()

    result = engine.evaluate(
        proposals=[object(), object()],
        bias_scores={"p1": 0.5},
        selected_ids=["p1"],
        promotable_ids=["p1"],
        delta_surface={"p1": 2},
    )

    assert result["proposal_count"] == 2
    assert result["selected_count"] == 1
    assert result["promotable_count"] == 1
    assert result["delta_surface"]["p1"] == 2
