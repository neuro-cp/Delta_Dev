from learning.stability_model.stability_engine import StabilityEngine

def test_stability_is_deterministic():
    engine = StabilityEngine()

    history = [{"stability_index": 2}, {"stability_index": 3}]

    a = engine.evaluate(evaluation_history=history)
    b = engine.evaluate(evaluation_history=history)

    assert a == b
