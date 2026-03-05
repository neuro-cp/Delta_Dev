from engine.vta_value.value_policy import ValuePolicy


def test_value_policy_accepts_within_bounds() -> None:
    policy = ValuePolicy(
        max_step_change=0.1,
        min_interval_steps=0,
    )

    accepted, new_value, reason = policy.evaluate(
        current_value=0.0,
        delta=0.05,
        current_step=0,
    )

    assert accepted is True
    assert new_value == 0.05
    assert reason == "accepted"


def test_value_policy_clamps_delta() -> None:
    policy = ValuePolicy(
        max_step_change=0.1,
        min_interval_steps=0,
    )

    accepted, new_value, _ = policy.evaluate(
        current_value=0.0,
        delta=1.0,
        current_step=0,
    )

    assert accepted is True
    assert new_value == 0.1


def test_value_policy_interval_gate() -> None:
    policy = ValuePolicy(
        max_step_change=0.1,
        min_interval_steps=5,
    )

    accepted, _, _ = policy.evaluate(
        current_value=0.0,
        delta=0.05,
        current_step=0,
    )
    assert accepted is True

    accepted, value, reason = policy.evaluate(
        current_value=0.05,
        delta=0.05,
        current_step=3,
    )

    assert accepted is False
    assert value == 0.05
    assert reason == "interval_gate"
