from learning.governance_escalation.escalation_engine import EscalationEngine

def test_escalation_zero_pressure():
    engine = EscalationEngine()

    result = engine.evaluate(integrity={})

    assert result["escalation_level"] == "stable"
