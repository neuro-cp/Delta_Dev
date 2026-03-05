from learning.containment_envelope.envelope_engine import ContainmentEnvelopeEngine

def test_envelope_is_deterministic():
    engine = ContainmentEnvelopeEngine()

    a = engine.evaluate(fragility={"fragility_index": 3}, max_adjustment=10)
    b = engine.evaluate(fragility={"fragility_index": 3}, max_adjustment=10)

    assert a == b
