from learning.drift_monitor.drift_engine import DriftEngine

def test_drift_zero_history():
    engine = DriftEngine()

    result = engine.evaluate(stability_history=[])

    assert result["drift_score"] == 0
    assert result["trend"] == 0.0
