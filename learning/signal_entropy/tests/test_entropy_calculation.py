from learning.signal_entropy.entropy_engine import EntropyEngine

def test_entropy_calculation():
    engine = EntropyEngine()

    signals = {"a": 1, "b": 1}

    result = engine.evaluate(signals=signals)

    assert result["entropy_index"] > 0
    assert result["signal_count"] == 2
