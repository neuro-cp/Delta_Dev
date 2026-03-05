from learning.governance_record.record_engine import GovernanceRecordEngine

def test_record_identity_consistency():
    engine = GovernanceRecordEngine()

    result = engine.evaluate()

    assert result["fragility_index"] == 0
    assert result["applied_adjustment"] == 0
