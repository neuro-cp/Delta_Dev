from learning.adaptive_calibration.calibration_engine import CalibrationEngine

def test_calibration_is_deterministic():
    engine = CalibrationEngine()

    a = engine.evaluate(
        stability={"stability_index": 1},
        drift={"drift_score": 2},
        escalation={"pressure": 3},
    )

    b = engine.evaluate(
        stability={"stability_index": 1},
        drift={"drift_score": 2},
        escalation={"pressure": 3},
    )

    assert a == b
