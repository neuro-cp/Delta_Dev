from orchestration.runtime.v25_hyb1_shadow_live_comparison import (
    APPROVAL_TEXT,
    run_hyb1_shadow_live_comparison,
    validate_hyb1_shadow_live_comparison_safe,
)


def test_hyb1_shadow_comparison_disabled_by_default():
    data = run_hyb1_shadow_live_comparison()

    assert validate_hyb1_shadow_live_comparison_safe(data)
    assert data["gate"]["permitted"] is False
    assert data["comparison"]["model_b"]["default_runtime"] is True
    assert data["comparison"]["hyb1"]["authoritative"] is False
    assert data["decision"]["promotes_hyb1"] is False
    assert data["decision"]["changes_default"] is False


def test_hyb1_shadow_comparison_opt_in_can_remain_blocked_by_unavailable_runtime():
    data = run_hyb1_shadow_live_comparison(
        approval_text=APPROVAL_TEXT,
        env={"DELTA_HYB1_SHADOW_LIVE_COMPARISON_ENABLED": "true"},
    )

    assert validate_hyb1_shadow_live_comparison_safe(data)
    assert data["gate"]["permitted"] is True
    assert data["gate"]["runtime_available"] is False
    assert data["gate"]["blocked_by_unavailable_runtime"] is True
    assert data["decision"]["provider_call_performed"] is False
    assert data["decision"]["training_performed"] is False
