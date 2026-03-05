from learning.drift_monitor.drift_engine import DriftEngine

def test_drift_is_deterministic():
    engine = DriftEngine()

    history = [{"stability_index": 1}, {"stability_index": 3}]
    a = engine.evaluate(stability_history=history)
    b = engine.evaluate(stability_history=history)

    assert a == b
