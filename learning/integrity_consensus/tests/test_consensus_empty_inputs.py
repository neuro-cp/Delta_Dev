from learning.integrity_consensus.consensus_engine import ConsensusEngine

def test_consensus_empty_inputs():
    engine = ConsensusEngine()

    result = engine.evaluate()

    assert result["disagreement_score"] == 0
