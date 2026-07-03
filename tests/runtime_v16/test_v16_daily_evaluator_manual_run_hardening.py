from __future__ import annotations

from orchestration.runtime.v16_daily_evaluator_manual_run_hardening import (
    ManualEvaluatorRunDecisionValue,
    build_manual_evaluator_run_request,
    run_hardened_manual_evaluator,
    validate_hardened_manual_evaluator_safe,
)
from orchestration.runtime.v16_daily_evaluator_manual_run_hardening_report import write_manual_run_hardening_report
from orchestration.runtime.v16_env import DeltaEvaluatorEnv


def test_dry_run_requires_no_key():
    payload = run_hardened_manual_evaluator(env=DeltaEvaluatorEnv(api_key_present=False))
    assert payload["decision"]["decision"] == ManualEvaluatorRunDecisionValue.DRY_RUN_READY.value
    assert payload["trial"]["trial_result"]["provider_call_performed"] is False
    assert validate_hardened_manual_evaluator_safe(payload)


def test_live_refuses_without_env_gates_or_key():
    payload = run_hardened_manual_evaluator(build_manual_evaluator_run_request(live=True), env=DeltaEvaluatorEnv(api_key_present=False, enabled=False, allow_live_call=False))
    assert payload["decision"]["decision"] == ManualEvaluatorRunDecisionValue.LIVE_REFUSED.value
    assert payload["trial"]["trial_result"]["provider_call_performed"] is False
    assert validate_hardened_manual_evaluator_safe(payload)


def test_request_redacts_key():
    payload = run_hardened_manual_evaluator(env=DeltaEvaluatorEnv(api_key_present=True, api_key_masked="sk-t...test"))
    text = str(payload["trial"]["request"])
    assert "api_key_redacted" in text
    assert "sk-t" not in text


def test_duplicate_run_id_blocked(tmp_path):
    log = tmp_path / "runs.jsonl"
    request = build_manual_evaluator_run_request("run-1")
    run_hardened_manual_evaluator(request, run_log_path=log, persist_run_log=True)
    duplicate = run_hardened_manual_evaluator(request, run_log_path=log, persist_run_log=False)
    assert duplicate["decision"]["decision"] == ManualEvaluatorRunDecisionValue.DUPLICATE_RUN_ID.value
    assert duplicate["lock"]["duplicate_run_id"] is True


def test_no_scheduler_memory_recall_training_or_model_change():
    payload = write_manual_run_hardening_report(run_id="test-run")
    flags = payload["invariant_flags"]
    assert flags["scheduler_enabled"] is False
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False
    assert validate_hardened_manual_evaluator_safe(payload)
