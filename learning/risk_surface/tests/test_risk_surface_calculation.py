from learning.risk_surface.risk_engine import RiskEngine

def test_risk_surface_calculation():
    engine = RiskEngine()

    result = engine.evaluate(
        envelope={"envelope_magnitude": 4},
        drift={"trend": 2.0},
        escalation={"pressure": 3},
    )

    assert result["risk_index"] == 9
