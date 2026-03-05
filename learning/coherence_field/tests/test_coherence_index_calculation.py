from learning.coherence_field.coherence_engine import CoherenceEngine

def test_coherence_index_calculation():
    engine = CoherenceEngine()

    result = engine.evaluate(
        stability={"stability_index": 5},
        drift={"drift_score": 3},
        risk={"risk_index": 4},
        envelope={"envelope_magnitude": 2},
    )

    assert result["coherence_index"] == 2
