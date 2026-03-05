from learning.integrity_pressure.integrity_engine import IntegrityEngine

def test_integrity_pressure_calculation():
    engine = IntegrityEngine()

    stability = {"stability_index": 4, "confidence": 2.0}
    drift = {"drift_score": 6, "trend": -1.0}

    result = engine.evaluate(stability=stability, drift=drift)

    assert result["integrity_pressure"] == 2
