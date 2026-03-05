from learning.governance_escalation.escalation_engine import EscalationEngine

def test_escalation_is_deterministic():
    engine = EscalationEngine()

    integrity = {"integrity_pressure": 3, "trend": 1.0}

    a = engine.evaluate(integrity=integrity)
    b = engine.evaluate(integrity=integrity)

    assert a == b
