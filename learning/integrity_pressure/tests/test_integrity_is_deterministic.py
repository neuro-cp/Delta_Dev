from learning.integrity_pressure.integrity_engine import IntegrityEngine

def test_integrity_is_deterministic():
    engine = IntegrityEngine()

    stability = {"stability_index": 5, "confidence": 2.5}
    drift = {"drift_score": 3, "trend": 1.0}

    a = engine.evaluate(stability=stability, drift=drift)
    b = engine.evaluate(stability=stability, drift=drift)

    assert a == b
