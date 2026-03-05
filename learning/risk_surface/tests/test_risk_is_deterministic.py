from learning.risk_surface.risk_engine import RiskEngine

def test_risk_is_deterministic():
    engine = RiskEngine()

    a = engine.evaluate(
        envelope={"envelope_magnitude": 4},
        drift={"trend": 2.0},
        escalation={"pressure": 3},
    )

    b = engine.evaluate(
        envelope={"envelope_magnitude": 4},
        drift={"trend": 2.0},
        escalation={"pressure": 3},
    )

    assert a == b
