from learning.session.learning_session import LearningSession


def test_two_generators_idempotent():
    session = LearningSession(replay_id="r1")

    inputs = [
        "sem:alpha",
        "sem:alpha",
        ("sem:alpha", 1),
        ("sem:alpha", 2),
    ]

    a = session.run(inputs=inputs)
    b = session.run(inputs=inputs)

    assert a == b
#validated#