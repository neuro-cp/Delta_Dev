from learning.adaptive_calibration.calibration_engine import CalibrationEngine

def test_calibration_adjustment_logic():
    engine = CalibrationEngine()

    result = engine.evaluate(
        stability={"stability_index": 1},
        drift={"drift_score": 2},
        escalation={"pressure": 3},
    )

    assert result["recommended_adjustment"] == 5
