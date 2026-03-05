from learning.calibration_application.application_engine import CalibrationApplicationEngine

def test_application_passes_when_within_envelope():
    engine = CalibrationApplicationEngine()

    result = engine.evaluate(proposed_adjustment=4, allowed_adjustment=6)

    assert result["applied_adjustment"] == 4
    assert result["was_clamped"] is False
