from learning.governance_gate.gate_engine import GovernanceGateEngine

def test_gate_rejects_when_fragile():
    engine = GovernanceGateEngine()

    record = {
        "fragility_index": 5,
        "was_clamped": False,
    }

    result = engine.evaluate(record=record)

    assert result["approved"] is False
    assert result["reason"] == "fragility_detected"
