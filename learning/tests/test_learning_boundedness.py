import pytest
from learning.schemas.learning_proposal import LearningProposal
from learning.audit.learning_audit import LearningAudit


def test_unbounded_proposal_rejected():
    audit = LearningAudit()

    bad = LearningProposal(
        proposal_id="bad",
        source_replay_id="r1",
        deltas=[],
        confidence=1.0,
        justification={},
        bounded=False,
        replay_consistent=True,
    )

    with pytest.raises(AssertionError):
        audit.audit(proposals=[bad])
