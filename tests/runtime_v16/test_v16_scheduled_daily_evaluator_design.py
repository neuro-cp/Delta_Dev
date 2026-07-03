from __future__ import annotations

import subprocess
import sys

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v16_scheduled_daily_evaluator_design import (
    build_scheduled_daily_evaluator_plan,
    validate_scheduled_daily_evaluator_plan_safe,
)
from orchestration.runtime.v16_scheduled_daily_evaluator_design_report import (
    write_scheduled_daily_evaluator_design_report,
)


def test_schedule_plan_is_disabled_by_default():
    plan = build_scheduled_daily_evaluator_plan()
    data = plan.as_dict()
    assert data["run_window"]["active"] is False
    assert data["decision"]["applied"] is False
    assert validate_scheduled_daily_evaluator_plan_safe(plan)


def test_no_scheduler_or_os_task_is_created():
    plan = build_scheduled_daily_evaluator_plan().as_dict()
    assert plan["gate_status"]["active_scheduler_enabled"] is False
    assert plan["lockfile_plan"]["create_lockfile_now"] is False
    assert plan["decision"]["active_scheduler_enabled"] is False


def test_no_api_memory_recall_training_or_action_side_effects(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    data = write_scheduled_daily_evaluator_design_report()
    flags = data["invariant_flags"]
    assert flags["api_call_performed"] is False
    assert flags["memory_write_enabled"] is False
    assert flags["runtime_recall_mutation_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False
    assert flags["hyb1_promoted"] is False


def test_manual_run_command_is_text_only():
    command = build_scheduled_daily_evaluator_plan().manual_run_command
    assert command.text_only is True
    assert command.executed is False
    assert "scripts\\run_delta_evaluator_trial.py" in command.command_text


def test_report_generation(tmp_path, monkeypatch):
    from orchestration.runtime import v16_scheduled_daily_evaluator_design_report as report_module

    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "v16e.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "v16e.json")
    data = write_scheduled_daily_evaluator_design_report()
    assert data["plan_safe"] is True
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()


def test_script_prints_plan_without_registering_schedule():
    completed = subprocess.run(
        [sys.executable, "scripts/plan_delta_daily_evaluator.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "manual_run_command" in completed.stdout
    assert "schtasks" not in completed.stdout.lower()
    assert "cron" not in completed.stdout.lower()
