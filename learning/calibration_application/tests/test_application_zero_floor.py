from learning.calibration_application.application_engine import CalibrationApplicationEngine

def test_application_zero_floor():
    engine = CalibrationApplicationEngine()

    result = engine.evaluate(proposed_adjustment=-5, allowed_adjustment=3)

    assert result["applied_adjustment"] == 0
