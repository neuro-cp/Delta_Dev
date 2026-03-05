from learning.stability_model.stability_engine import StabilityEngine

def test_stability_index_consistency():
    engine = StabilityEngine()

    history = [{"stability_index": 2}, {"stability_index": 3}]
    result = engine.evaluate(evaluation_history=history)

    assert result["stability_index"] == 5
