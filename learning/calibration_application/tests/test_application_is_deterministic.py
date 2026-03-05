from learning.calibration_application.application_engine import CalibrationApplicationEngine

def test_application_is_deterministic():
    engine = CalibrationApplicationEngine()

    a = engine.evaluate(proposed_adjustment=8, allowed_adjustment=5)
    b = engine.evaluate(proposed_adjustment=8, allowed_adjustment=5)

    assert a == b
