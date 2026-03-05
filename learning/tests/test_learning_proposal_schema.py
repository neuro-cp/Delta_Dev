from learning.schemas.learning_proposal import LearningProposal
import pytest


def test_learning_proposal_is_frozen():
    proposal = LearningProposal(
        proposal_id="p1",
        source_replay_id="r1",
        deltas=[],
        confidence=0.5,
        justification={},
        bounded=True,
        replay_consistent=True,
    )

    with pytest.raises(Exception):
        proposal.confidence = 0.9
