from learning.governance_gate.gate_engine import GovernanceGateEngine

def test_gate_is_deterministic():
    engine = GovernanceGateEngine()

    record = {
        "fragility_index": 0,
        "was_clamped": False,
    }

    a = engine.evaluate(record=record)
    b = engine.evaluate(record=record)

    assert a == b
