from learning.session.learning_session import LearningSession


def test_frequency_proposal_idempotent():
    session = LearningSession(replay_id="replay_1")

    inputs = [
        "sem:alpha",
        "sem:beta",
        "sem:alpha",  # recurrent
    ]

    a = session.run(inputs=inputs)
    b = session.run(inputs=inputs)

    assert a == b
