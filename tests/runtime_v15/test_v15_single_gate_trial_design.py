from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_single_gate_trial import (
    RUNTIME_V15C_INVARIANT_FLAGS,
    STARTER_DELTA_QUESTION,
    create_single_gate_expected_trace,
    create_single_gate_trial_decision,
    create_single_gate_trial_input_case,
    create_single_gate_trial_scope,
    create_single_gate_trial_target,
    validate_expected_trace_non_mutating,
    validate_single_gate_scope_safe,
    validate_single_gate_target_closed,
)
from orchestration.runtime.v15_single_gate_trial_report import build_single_gate_trial_report_data, write_single_gate_trial_report


def test_single_gate_import_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V15C_INVARIANT_FLAGS.values())


def test_single_gate_target_scope_and_trace_are_design_only():
    target = create_single_gate_trial_target("plan")
    scope = create_single_gate_trial_scope(target)
    case = create_single_gate_trial_input_case(target)
    trace = create_single_gate_expected_trace(case)
    decision = create_single_gate_trial_decision(target)
    assert target.target_name == "runtime_console_message_preview"
    assert validate_single_gate_target_closed(target)
    assert validate_single_gate_scope_safe(scope)
    assert case.message == STARTER_DELTA_QUESTION
    assert case.training_example is False
    assert case.memory_candidate is False
    assert validate_expected_trace_non_mutating(trace)
    assert decision.gate_opened is False
    assert decision.trial_executed is False


def test_report_data_states_no_gate_opened_or_trial_executed():
    data = build_single_gate_trial_report_data()
    assert data["final_recommendation"] == "PROCEED_FIRST_LIVE_INTERACTION_PATH_CONSOLE_ONLY"
    assert data["target"]["gate_open"] is False
    assert data["target"]["trial_execution_enabled"] is False
    assert data["input_case"]["message"] == STARTER_DELTA_QUESTION
    assert data["expected_trace"]["expected_memory_write"] is False
    assert data["expected_trace"]["expected_provider_call"] is False
    assert data["decision"]["trial_executed"] is False
    assert all(value is False for value in data["invariant_flags"].values())


def test_write_single_gate_trial_report(tmp_path, monkeypatch):
    from orchestration.runtime import v15_single_gate_trial_report as report_module

    md_path = tmp_path / "single_gate.md"
    json_path = tmp_path / "single_gate.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_single_gate_trial_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8").lower()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "single-gate-design-only" in text
    assert "no trial is executed" in text
