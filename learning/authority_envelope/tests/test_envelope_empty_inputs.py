from learning.authority_envelope.envelope_engine import EnvelopeEngine

def test_envelope_empty_inputs():
    engine = EnvelopeEngine()

    result = engine.evaluate()

    assert result["envelope_magnitude"] == 0
