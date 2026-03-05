from learning.signal_entropy.entropy_engine import EntropyEngine

def test_entropy_empty_inputs():
    engine = EntropyEngine()

    result = engine.evaluate()

    assert result["entropy_index"] == 0.0
    assert result["signal_count"] == 0
