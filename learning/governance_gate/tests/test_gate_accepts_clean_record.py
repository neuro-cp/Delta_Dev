from learning.governance_gate.gate_engine import GovernanceGateEngine

def test_gate_accepts_clean_record():
    engine = GovernanceGateEngine()

    record = {
        "fragility_index": 0,
        "was_clamped": False,
    }

    result = engine.evaluate(record=record)

    assert result["approved"] is True
    assert result["reason"] == "structurally_clean"
