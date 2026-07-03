from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from scripts.runtime_console_smoke import (
    MANUAL_E2E_CASES,
    build_runtime_console_manual_e2e_report_data,
    run_runtime_console_manual_e2e_cases,
    write_runtime_console_manual_e2e_report,
)


def test_manual_e2e_imports_do_not_change_model_b_or_hyb1_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False


def test_manual_e2e_cases_cover_required_message_set():
    case_ids = {case.case_id for case in MANUAL_E2E_CASES}

    assert {
        "simple_user_question",
        "correction_message",
        "action_intent_message",
        "specialist_gap_message",
        "training_sensitive_message",
        "memory_sensitive_message",
        "unsafe_execution_message",
    }.issubset(case_ids)


def test_manual_e2e_cases_are_deterministic_review_only_and_non_mutating():
    results = run_runtime_console_manual_e2e_cases()

    assert len(results) == 7
    for result in results:
        assert result["passed"] is True
        assert result["checks"]["deterministic_preview"] is True
        assert result["checks"]["review_only"] is True
        assert result["checks"]["raw_input_not_memory"] is True
        assert result["checks"]["raw_input_not_training"] is True
        assert result["checks"]["record_not_memory"] is True
        assert result["checks"]["record_not_canonical"] is True
        assert result["checks"]["record_not_learned"] is True
        assert result["checks"]["no_memory_write"] is True
        assert result["checks"]["no_training_trigger"] is True
        assert result["checks"]["no_provider_call"] is True
        assert result["checks"]["no_action_execution"] is True
        assert result["checks"]["all_disabled_flags_false"] is True


def test_manual_e2e_report_data_states_no_training_export_or_side_effects():
    data = build_runtime_console_manual_e2e_report_data()

    assert data["final_recommendation"] == "PROCEED_TRAINING_DATASET_CANDIDATE_EXPORT_DESIGN"
    assert data["actual_verification_summary"]["all_cases_passed"] is True
    assert "training dataset export" in data["inactive_systems"]
    assert "provider calls" in data["inactive_systems"]
    assert "action execution" in data["inactive_systems"]
    assert "memory mutation" in data["inactive_systems"]
    assert "runtime recall mutation" in data["inactive_systems"]
    assert data["invariant_flags"]["training_enabled"] is False
    assert data["invariant_flags"]["provider_calls_enabled"] is False
    assert data["invariant_flags"]["action_execution_enabled"] is False


def test_write_manual_e2e_report(tmp_path, monkeypatch):
    import scripts.runtime_console_smoke as smoke

    md_path = tmp_path / "runtime_console_manual_e2e_testing.md"
    json_path = tmp_path / "runtime_console_manual_e2e_testing.json"
    monkeypatch.setattr(smoke, "REPORT_MD", md_path)
    monkeypatch.setattr(smoke, "REPORT_JSON", json_path)

    data = write_runtime_console_manual_e2e_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "Manual E2E" in text
    assert "provider" in text
    assert "training" in text
