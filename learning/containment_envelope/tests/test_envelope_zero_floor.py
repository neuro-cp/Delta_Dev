from learning.containment_envelope.envelope_engine import ContainmentEnvelopeEngine

def test_envelope_zero_floor():
    engine = ContainmentEnvelopeEngine()

    result = engine.evaluate(
        fragility={"fragility_index": 15},
        max_adjustment=10,
    )

    assert result["allowed_adjustment"] == 0
