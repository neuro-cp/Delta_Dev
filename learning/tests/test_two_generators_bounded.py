from learning.session.learning_session import LearningSession
from learning.audit.learning_audit import LearningAudit


def test_two_generators_bounded():
    session = LearningSession(replay_id="r1")
    audit = LearningAudit()

    inputs = [
        "sem:alpha",
        "sem:alpha",
        ("sem:alpha", 1),
        ("sem:alpha", 2),
        ("sem:alpha", 3),
    ]

    proposals = session.run(inputs=inputs)

    # At most one proposal per generator
    assert len(proposals) <= 2

    # Audit enforces boundedness and replay safety
    audit.audit(proposals=proposals)
#validated#