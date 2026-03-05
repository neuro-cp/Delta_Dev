from learning.momentum_field.momentum_engine import MomentumEngine

def test_momentum_is_deterministic():
    engine = MomentumEngine()

    history = [
        {"stability_index": 1},
        {"stability_index": 3},
        {"stability_index": 6},
    ]

    a = engine.evaluate(stability_history=history)
    b = engine.evaluate(stability_history=history)

    assert a == b
