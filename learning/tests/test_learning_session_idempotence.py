from learning.session.learning_session import LearningSession


def test_learning_session_idempotent():
    session = LearningSession(replay_id="r1")

    a = session.run(inputs=[])
    b = session.run(inputs=[])

    # Returned proposals must be identical
    assert a == b

    # Must not mutate across runs
    assert isinstance(a, list)
    assert isinstance(b, list)

    # Deterministic length check
    assert len(a) == len(b)