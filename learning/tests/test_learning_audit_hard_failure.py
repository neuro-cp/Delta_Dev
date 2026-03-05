import pytest

from learning.session.learning_session import LearningSession
from learning.schemas.learning_proposal import LearningProposal


class _BadGenerator:
    """Emits a structurally invalid proposal (empty deltas)."""

    def generate(self, *, replay_id, semantic_ids=None, **kwargs):
        return [
            LearningProposal(
                proposal_id="bad",
                source_replay_id=replay_id,
                deltas=[],  # <-- structural violation
                confidence=1.0,
                justification={},
                bounded=True,
                replay_consistent=True,
            )
        ]


def test_learning_audit_hard_failure_raises():
    session = LearningSession(replay_id="replay_fail")

    # Replace frequency generator with a bad one
    session._freq_gen = _BadGenerator()

    with pytest.raises(AssertionError):
        session.run(inputs=["sem:alpha"])