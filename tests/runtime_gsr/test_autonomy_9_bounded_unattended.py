from __future__ import annotations

from orchestration.runtime.autonomy_bounded_unattended import run_bounded_unattended_window
from orchestration.runtime.autonomy_multi_goal_scheduler import run_scheduler


def _scheduler(root):
    return run_scheduler(root / "a8", seed_goals=(
        {"condition_key": "transfer_beyond_retained_fixture_families", "priority": 10},
        {"condition_key": "attended_visible_button_closure", "priority": 6},
        {"condition_key": "blocked_provider_goal", "priority": 99, "state": "blocked"},
    ))


def test_a9_unattended_window_respects_budgets_and_stops(tmp_path):
    _scheduler(tmp_path)
    result = run_bounded_unattended_window(scheduler_root=tmp_path / "a8", output_root=tmp_path / "a9")
    summary = result["summary"]

    assert result["status"] == "AUTONOMY_9_BOUNDED_UNATTENDED_DEVELOPMENT_PASSED"
    assert summary["provider_calls"] == 0
    assert summary["network_calls"] == 0
    assert summary["tracked_source_mutation"] is False
    assert summary["deployment"] is False
    assert summary["learning_campaigns"] <= 1
    assert summary["strategy_revisions"] <= 1
    assert summary["filler_goals_created"] == 0
    assert summary["noop_repetition_count"] == 0


def test_a9_restart_exactness_suppresses_duplicate_window(tmp_path):
    _scheduler(tmp_path)
    first = run_bounded_unattended_window(scheduler_root=tmp_path / "a8", output_root=tmp_path / "a9")
    second = run_bounded_unattended_window(scheduler_root=tmp_path / "a8", output_root=tmp_path / "a9")

    assert second["duplicate_suppressed"] is True
    assert second["summary"]["summary_id"] == first["summary"]["summary_id"]
    assert len(tuple((tmp_path / "a9" / "final_summaries").glob("*.json"))) == 1
    assert (tmp_path / "a9" / "restart_state" / "state.json").exists()


def test_a9_blocks_missing_active_goal_or_oversized_budget(tmp_path):
    missing = run_bounded_unattended_window(scheduler_root=tmp_path / "missing", output_root=tmp_path / "missing-a9")
    assert missing["status"] == "AUTONOMY_9_BOUNDED_UNATTENDED_DEVELOPMENT_BLOCKED"
    too_long_root = tmp_path / "long"
    _scheduler(too_long_root)
    too_long = run_bounded_unattended_window(scheduler_root=too_long_root / "a8", output_root=tmp_path / "long-a9", duration_minutes=61)
    assert too_long["status"] == "AUTONOMY_9_BOUNDED_UNATTENDED_DEVELOPMENT_BLOCKED"
