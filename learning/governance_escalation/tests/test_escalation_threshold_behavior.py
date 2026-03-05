from learning.governance_escalation.escalation_engine import EscalationEngine

def test_escalation_threshold_behavior():
    engine = EscalationEngine()

    assert engine.evaluate(integrity={"integrity_pressure": 0})["escalation_level"] == "stable"
    assert engine.evaluate(integrity={"integrity_pressure": 3})["escalation_level"] == "watch"
    assert engine.evaluate(integrity={"integrity_pressure": 7})["escalation_level"] == "elevated"
    assert engine.evaluate(integrity={"integrity_pressure": 15})["escalation_level"] == "critical"
