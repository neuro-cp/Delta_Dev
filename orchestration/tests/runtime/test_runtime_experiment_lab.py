from __future__ import annotations

from tools.runtime_experiment import SUPPORTED_EXPERIMENT_TICKS, run_experiment


def test_runtime_experiment_supports_curriculum_runs_with_isolated_summary(tmp_path):
    summary = run_experiment(
        ticks=2,
        store_root=tmp_path,
        experiment_kind="curriculum",
        curriculum_domains=("arithmetic", "logic"),
    )

    assert summary["ticks_requested"] == 2
    assert summary["ticks_completed"] == 2
    assert summary["experiment_kind"] == "curriculum"
    assert summary["curriculum"]["enabled"] is True
    assert summary["curriculum"]["domains"] == {"arithmetic": 1, "logic": 1}
    assert summary["counts"]["memories"] >= 2


def test_runtime_experiment_reports_supported_large_tick_targets(tmp_path):
    summary = run_experiment(
        ticks=1,
        store_root=tmp_path,
        experiment_kind="runtime",
    )

    assert summary["supported_large_tick_targets"] == list(SUPPORTED_EXPERIMENT_TICKS)
    assert summary["large_tick_target"] is False
    assert summary["curriculum"] == {"enabled": False}
