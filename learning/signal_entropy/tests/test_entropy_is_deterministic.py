from learning.signal_entropy.entropy_engine import EntropyEngine

def test_entropy_is_deterministic():
    engine = EntropyEngine()

    signals = {"a": 3, "b": 3}

    a = engine.evaluate(signals=signals)
    b = engine.evaluate(signals=signals)

    assert a == b
