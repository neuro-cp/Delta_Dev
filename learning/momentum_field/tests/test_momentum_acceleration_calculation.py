from learning.momentum_field.momentum_engine import MomentumEngine

def test_momentum_acceleration_calculation():
    engine = MomentumEngine()

    history = [
        {"stability_index": 1},
        {"stability_index": 3},
        {"stability_index": 6},
    ]

    result = engine.evaluate(stability_history=history)

    assert result["momentum_index"] == 1
