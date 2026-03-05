from learning.integrity_consensus.consensus_engine import ConsensusEngine

def test_consensus_is_deterministic():
    engine = ConsensusEngine()

    a = engine.evaluate(
        escalation={"pressure": 2},
        oversight={"aggregate_index": 4},
        calibration={"recommended_adjustment": 3},
    )

    b = engine.evaluate(
        escalation={"pressure": 2},
        oversight={"aggregate_index": 4},
        calibration={"recommended_adjustment": 3},
    )

    assert a == b
