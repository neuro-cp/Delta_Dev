from learning.session.learning_session import LearningSession
from learning.audit.learning_audit import LearningAudit


def test_frequency_proposal_bounded():
    session = LearningSession(replay_id="replay_1")
    audit = LearningAudit()

    inputs = [
        "sem:alpha",
        "sem:alpha",
        "sem:alpha",
    ]

    proposals = session.run(inputs=inputs)

    # Should emit at most one proposal
    assert len(proposals) <= 1

    # Audit enforces boundedness and replay safety
    audit.audit(proposals=proposals)
