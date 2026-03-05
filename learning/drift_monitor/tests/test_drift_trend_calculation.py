from learning.drift_monitor.drift_engine import DriftEngine

def test_drift_trend_calculation():
    engine = DriftEngine()

    history = [
        {"stability_index": 1},
        {"stability_index": 3},
        {"stability_index": 6},
    ]

    result = engine.evaluate(stability_history=history)

    assert result["drift_score"] == 5
    assert result["trend"] == 2.5
