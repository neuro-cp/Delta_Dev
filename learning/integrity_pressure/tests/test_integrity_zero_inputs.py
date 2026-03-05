from learning.integrity_pressure.integrity_engine import IntegrityEngine

def test_integrity_zero_inputs():
    engine = IntegrityEngine()

    result = engine.evaluate(stability={}, drift={})

    assert result["integrity_pressure"] == 0
