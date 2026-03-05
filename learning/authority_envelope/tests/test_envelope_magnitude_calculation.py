from learning.authority_envelope.envelope_engine import EnvelopeEngine

def test_envelope_magnitude_calculation():
    engine = EnvelopeEngine()

    result = engine.evaluate(
        consensus={"disagreement_score": 2},
        escalation={"pressure": 3},
        calibration={"recommended_adjustment": 4},
    )

    assert result["envelope_magnitude"] == 9
