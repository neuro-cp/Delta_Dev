from learning.containment_envelope.envelope_engine import ContainmentEnvelopeEngine

def test_envelope_reduces_with_fragility():
    engine = ContainmentEnvelopeEngine()

    result = engine.evaluate(
        fragility={"fragility_index": 4},
        max_adjustment=10,
    )

    assert result["allowed_adjustment"] == 6
