from learning.risk_surface.risk_engine import RiskEngine

def test_risk_empty_inputs():
    engine = RiskEngine()

    result = engine.evaluate()

    assert result["risk_index"] == 0
