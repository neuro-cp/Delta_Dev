from learning.coherence_field.coherence_engine import CoherenceEngine

def test_coherence_is_deterministic():
    engine = CoherenceEngine()

    a = engine.evaluate(
        stability={"stability_index": 5},
        drift={"drift_score": 3},
        risk={"risk_index": 4},
        envelope={"envelope_magnitude": 2},
    )

    b = engine.evaluate(
        stability={"stability_index": 5},
        drift={"drift_score": 3},
        risk={"risk_index": 4},
        envelope={"envelope_magnitude": 2},
    )

    assert a == b
