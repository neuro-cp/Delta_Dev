from learning.coherence_field.coherence_engine import CoherenceEngine

def test_coherence_empty_inputs():
    engine = CoherenceEngine()

    result = engine.evaluate()

    assert result["coherence_index"] == 0
