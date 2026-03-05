from learning.governance_record.record_engine import GovernanceRecordEngine

def test_record_contains_all_fields():
    engine = GovernanceRecordEngine()

    result = engine.evaluate()

    expected_keys = {
        "fragility_index",
        "allowed_adjustment",
        "max_adjustment",
        "proposed_adjustment",
        "applied_adjustment",
        "was_clamped",
    }

    assert set(result.keys()) == expected_keys
