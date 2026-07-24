from __future__ import annotations

from orchestration.runtime.autonomy_multi_goal_scheduler import run_scheduler


def _pilot_goals():
    return (
        {"condition_key": "transfer_beyond_retained_fixture_families", "priority": 10},
        {"condition_key": "attended_visible_button_closure", "priority": 6},
        {"condition_key": "blocked_provider_goal", "priority": 99, "state": "blocked"},
        {"condition_key": "transfer_beyond_retained_fixture_families", "priority": 1},
    )


def test_a8_selects_one_highest_ready_goal_and_defers_blocked_duplicate(tmp_path):
    result = run_scheduler(tmp_path / "a8", seed_goals=_pilot_goals())
    scheduler = result["scheduler"]

    assert result["status"] == "AUTONOMY_8_MULTI_GOAL_SCHEDULER_PASSED"
    assert scheduler["selected_goal"]["condition_key"] == "transfer_beyond_retained_fixture_families"
    assert scheduler["one_active_goal_maximum"] is True
    assert scheduler["execution_started"] is False
    states = {goal["condition_key"]: goal["state"] for goal in scheduler["queue_snapshot"]}
    assert states["blocked_provider_goal"] == "blocked"
    assert any(goal["selection_reason"] in {"goal_blocked", "duplicate_equivalent_goal"} for goal in scheduler["deferred_goals"])


def test_a8_restart_preserves_exact_queue_without_duplicates(tmp_path):
    first = run_scheduler(tmp_path / "a8", seed_goals=_pilot_goals())
    second = run_scheduler(tmp_path / "a8")

    assert second["scheduler"]["queue_snapshot"] == first["scheduler"]["queue_snapshot"]
    assert second["scheduler"]["active_runner_ownership"] == first["scheduler"]["active_runner_ownership"]
    assert len(tuple((tmp_path / "a8" / "goals").glob("*.json"))) == 3


def test_a8_completed_active_allows_next_eligible_goal_to_be_selectable(tmp_path):
    first = run_scheduler(tmp_path / "a8", seed_goals=_pilot_goals())
    active = first["scheduler"]["selected_goal"]["goal_id"]
    second = run_scheduler(tmp_path / "a8", mark_completed=active)

    assert second["scheduler"]["selected_goal"]["condition_key"] == "attended_visible_button_closure"
    assert second["scheduler"]["one_active_goal_maximum"] is True
    assert all(not goal["execution_started"] for goal in second["scheduler"]["queue_snapshot"])


def test_a8_mutation_capable_goal_not_selected_concurrently(tmp_path):
    result = run_scheduler(tmp_path / "a8", seed_goals=(
        {"condition_key": "source_repair", "priority": 100, "authority_requirements": ("tracked_source_mutation",)},
        {"condition_key": "safe_read_only_goal", "priority": 5},
    ))

    assert result["scheduler"]["selected_goal"]["condition_key"] == "safe_read_only_goal"
    assert any(goal["selection_reason"] == "mutation_capable_goal_requires_separate_authority" for goal in result["scheduler"]["deferred_goals"])
