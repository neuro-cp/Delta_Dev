from orchestration.runtime.v27_evaluator_daily_dry_run_dashboard import (
    build_evaluator_daily_dry_run_dashboard,
    validate_evaluator_daily_dry_run_dashboard_safe,
)


def test_evaluator_daily_dashboard_starts_no_scheduler():
    data = build_evaluator_daily_dry_run_dashboard()

    assert validate_evaluator_daily_dry_run_dashboard_safe(data)
    assert data["scheduled"] is False
    assert data["background_worker_started"] is False
