from learning.authority_envelope.envelope_engine import EnvelopeEngine

def test_envelope_is_deterministic():
    engine = EnvelopeEngine()

    a = engine.evaluate(
        consensus={"disagreement_score": 2},
        escalation={"pressure": 3},
        calibration={"recommended_adjustment": 4},
    )

    b = engine.evaluate(
        consensus={"disagreement_score": 2},
        escalation={"pressure": 3},
        calibration={"recommended_adjustment": 4},
    )

    assert a == b
