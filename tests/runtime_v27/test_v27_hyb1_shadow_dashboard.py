from orchestration.runtime.v27_hyb1_shadow_dashboard import (
    build_hyb1_shadow_dashboard,
    validate_hyb1_shadow_dashboard_safe,
)


def test_hyb1_shadow_dashboard_keeps_model_b_default():
    data = build_hyb1_shadow_dashboard()

    assert validate_hyb1_shadow_dashboard_safe(data)
    assert data["model_b_default"] is True
    assert data["hyb1_promoted"] is False
