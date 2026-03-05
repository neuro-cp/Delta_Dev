from learning.governance_record.record_engine import GovernanceRecordEngine

def test_record_is_deterministic():
    engine = GovernanceRecordEngine()

    fragility = {"fragility_index": 5}
    envelope = {"allowed_adjustment": 4, "max_adjustment": 10}
    application = {
        "proposed_adjustment": 6,
        "applied_adjustment": 4,
        "was_clamped": True,
    }

    a = engine.evaluate(
        fragility=fragility,
        envelope=envelope,
        application=application,
    )
    b = engine.evaluate(
        fragility=fragility,
        envelope=envelope,
        application=application,
    )

    assert a == b
