from orchestration.runtime.v27_full_local_demo import (
    build_full_local_demo,
    validate_full_local_demo_safe,
)


def test_full_local_demo_is_not_executed():
    data = build_full_local_demo()

    assert validate_full_local_demo_safe(data)
    assert data["executed_steps"] == []
    assert data["safety_invariants"]["provider_call_performed"] is False
