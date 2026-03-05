from learning.cognitive_evaluation.cognitive_evaluation_engine import CognitiveEvaluationEngine

def test_evaluation_is_deterministic():
    engine = CognitiveEvaluationEngine()

    result_a = engine.evaluate(
        proposals=[],
        bias_scores={},
        selected_ids=[],
        promotable_ids=[],
        delta_surface={},
    )

    result_b = engine.evaluate(
        proposals=[],
        bias_scores={},
        selected_ids=[],
        promotable_ids=[],
        delta_surface={},
    )

    assert result_a == result_b
