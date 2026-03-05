from learning.momentum_field.momentum_engine import MomentumEngine

def test_momentum_insufficient_history():
    engine = MomentumEngine()

    result = engine.evaluate(stability_history=[{"stability_index": 1}])

    assert result["momentum_index"] == 0
