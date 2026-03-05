from learning.stability_model.stability_engine import StabilityEngine

def test_stability_confidence_calculation():
    engine = StabilityEngine()

    history = [{"stability_index": 4}, {"stability_index": 6}]
    result = engine.evaluate(evaluation_history=history)

    assert result["confidence"] == 5.0
