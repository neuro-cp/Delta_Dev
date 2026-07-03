from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_runtime_console import (
    RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS,
    build_runtime_console_preview,
    create_runtime_console_input,
    create_runtime_console_plan,
    validate_runtime_console_plan_inert,
    validate_runtime_console_preview_review_only,
)
from orchestration.runtime.v14_runtime_console_report import (
    build_runtime_console_report_data,
    write_runtime_console_report,
)


def test_importing_runtime_console_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS.values())


def test_runtime_console_input_is_deterministic():
    first = create_runtime_console_input("  Please   inspect this.  ")
    second = create_runtime_console_input("Please inspect this.")

    assert first.console_input_id == second.console_input_id
    assert first.user_message == "Please inspect this."


def test_runtime_console_preview_is_review_only_and_non_mutating():
    preview = build_runtime_console_preview("Can DELTA inspect this without learning?")

    assert validate_runtime_console_preview_review_only(preview)
    assert preview.raw_input.memory is False
    assert preview.raw_input.training_example is False
    assert preview.raw_input.ingested_automatically is False
    assert preview.experience_record.memory is False
    assert preview.experience_record.canonical is False
    assert preview.experience_record.learned is False
    assert preview.semantic_frame.canonical is False
    assert preview.semantic_frame.learned is False
    assert preview.trace_summary.memory_written is False
    assert preview.trace_summary.training_triggered is False


def test_runtime_console_preview_disables_provider_specialist_action_and_tools():
    preview = build_runtime_console_preview("Please write a file later.")
    flags = preview.safety_status.disabled_capability_flags

    assert flags["provider_calls_enabled"] is False
    assert flags["specialist_routing_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["tool_calls_enabled"] is False
    assert flags["side_effects_enabled"] is False
    assert flags["scheduler_enabled"] is False
    assert preview.trace_summary.provider_called is False
    assert preview.trace_summary.action_executed is False


def test_runtime_console_preview_does_not_mutate_recall_memory_or_training():
    preview = build_runtime_console_preview("This is feedback, but do not train.")
    flags = preview.safety_status.disabled_capability_flags

    assert flags["memory_mutation_enabled"] is False
    assert flags["runtime_recall_mutation_enabled"] is False
    assert flags["canonical_write_enabled"] is False
    assert flags["training_enabled"] is False
    assert preview.safety_status.no_training_data_created is True


def test_runtime_console_plan_is_manual_and_inert():
    preview = build_runtime_console_preview("Manual preview only.")
    plan = create_runtime_console_plan((preview,))

    assert plan.preview_ids == (preview.preview_id,)
    assert validate_runtime_console_plan_inert(plan)


def test_runtime_console_report_data_states_manual_console_status():
    data = build_runtime_console_report_data()

    assert data["final_recommendation"] == "PROCEED_MANUAL_END_TO_END_MESSAGE_TESTING"
    assert data["implementation_choice"] == "CLI/script console"
    assert data["status"] == "manual_review_only_no_provider_no_mutation_no_execution"
    assert data["preview"]["safety_status"]["provider_free"] is True
    assert data["preview"]["safety_status"]["execution_free"] is True
    assert data["preview"]["trace_summary"]["memory_written"] is False
    assert data["disabled_capability_flags"]["runtime_defaults_changed"] is False


def test_write_runtime_console_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_runtime_console_report as report_module

    md_path = tmp_path / "console.md"
    json_path = tmp_path / "console.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_runtime_console_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "manual" in text.lower()
    assert "provider" in text.lower()
    assert "memory" in text.lower()
