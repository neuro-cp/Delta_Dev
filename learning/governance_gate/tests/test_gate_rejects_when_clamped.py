from learning.governance_gate.gate_engine import GovernanceGateEngine

def test_gate_rejects_when_clamped():
    engine = GovernanceGateEngine()

    record = {
        "fragility_index": 0,
        "was_clamped": True,
    }

    result = engine.evaluate(record=record)

    assert result["approved"] is False
    assert result["reason"] == "adjustment_clamped"
