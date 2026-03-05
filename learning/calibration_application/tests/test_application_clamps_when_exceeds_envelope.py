from learning.calibration_application.application_engine import CalibrationApplicationEngine

def test_application_clamps_when_exceeds_envelope():
    engine = CalibrationApplicationEngine()

    result = engine.evaluate(proposed_adjustment=10, allowed_adjustment=6)

    assert result["applied_adjustment"] == 6
    assert result["was_clamped"] is True
