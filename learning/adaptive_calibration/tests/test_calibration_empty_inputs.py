from learning.adaptive_calibration.calibration_engine import CalibrationEngine

def test_calibration_empty_inputs():
    engine = CalibrationEngine()

    result = engine.evaluate()

    assert result["recommended_adjustment"] == 0
