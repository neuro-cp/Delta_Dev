from learning.integrity_consensus.consensus_engine import ConsensusEngine

def test_consensus_disagreement_score():
    engine = ConsensusEngine()

    result = engine.evaluate(
        escalation={"pressure": 2},
        oversight={"aggregate_index": 4},
        calibration={"recommended_adjustment": 3},
    )

    assert result["disagreement_score"] == 3
