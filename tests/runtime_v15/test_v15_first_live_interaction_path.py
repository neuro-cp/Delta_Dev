from __future__ import annotations

import subprocess
import sys

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_first_interaction import (
    RUNTIME_V15D_INVARIANT_FLAGS,
    STARTER_DELTA_QUESTION,
    build_first_interaction_result,
    validate_first_interaction_result_safe,
)
from orchestration.runtime.v15_first_interaction_report import build_first_interaction_report_data, write_first_interaction_report


def test_first_interaction_import_does_not_activate_hyb1(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V15D_INVARIANT_FLAGS["first_live_console_interaction_enabled"] is True
    assert RUNTIME_V15D_INVARIANT_FLAGS["runtime_console_gate_open"] is True
    assert RUNTIME_V15D_INVARIANT_FLAGS["only_runtime_console_gate_open"] is True
    assert all(value is False for key, value in RUNTIME_V15D_INVARIANT_FLAGS.items() if key not in {"first_live_console_interaction_enabled", "runtime_console_gate_open", "only_runtime_console_gate_open"})


def test_starter_question_returns_local_deterministic_safe_preview():
    data = build_first_interaction_result(STARTER_DELTA_QUESTION)
    text = data["response_preview"]["response_text"].lower()
    assert "replay markers/batches" in text
    assert "consolidation candidate" in text
    assert "canonical writes remain disabled" in text
    assert validate_first_interaction_result_safe(data)


def test_unknown_question_abstains_from_provider_style_answer():
    data = build_first_interaction_result("Who won a game yesterday?")
    text = data["response_preview"]["response_text"].lower()
    assert "cannot answer" in text
    assert "provider calls" in text
    assert validate_first_interaction_result_safe(data)


def test_report_data_states_first_live_console_only_no_side_effects():
    data = build_first_interaction_report_data()
    result = data["starter_result"]
    assert data["final_recommendation"] == "PROCEED_V15E_HYB1_LIMITED_OPT_IN_TRIAL_DESIGN"
    assert result["gate_status"]["runtime_console_gate_open"] is True
    assert result["safety_status"]["provider_calls_enabled"] is False
    assert result["trace"]["persisted_to_memory"] is False
    assert result["result"]["side_effects_created"] is False


def test_write_first_interaction_report(tmp_path, monkeypatch):
    from orchestration.runtime import v15_first_interaction_report as report_module

    md_path = tmp_path / "first.md"
    json_path = tmp_path / "first.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_first_interaction_report()
    text = md_path.read_text(encoding="utf-8").lower()
    assert data["final_recommendation"] == "PROCEED_V15E_HYB1_LIMITED_OPT_IN_TRIAL_DESIGN"
    assert "first-live-console-interaction-only" in text
    assert "starter output" in text


def test_ask_delta_script_works_in_one_shot_mode():
    completed = subprocess.run(
        [sys.executable, "scripts/ask_delta.py", STARTER_DELTA_QUESTION],
        check=True,
        text=True,
        capture_output=True,
    )
    output = completed.stdout.lower()
    assert "delta first interaction preview" in output
    assert "canonical writes remain disabled" in output
    assert "provider_calls_enabled: false" in output
    assert "action_execution_enabled: false" in output
    assert "training_enabled: false" in output
    assert "hyb1_default_activation_enabled: false" in output
