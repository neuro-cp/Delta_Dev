from __future__ import annotations

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v16_scheduler_activation_gate import (
    SCHEDULER_APPROVAL_TOKEN,
    SchedulerActivationDecisionValue,
    build_scheduler_activation_request,
    evaluate_scheduler_activation_gate,
    validate_scheduler_activation_gate_safe,
)
from orchestration.runtime.v16_scheduler_activation_gate_report import write_scheduler_activation_gate_report


def test_scheduler_disabled_by_default():
    payload = evaluate_scheduler_activation_gate()
    assert payload["decision"]["decision"] == SchedulerActivationDecisionValue.REFUSED.value
    assert payload["decision"]["scheduler_started"] is False
    assert validate_scheduler_activation_gate_safe(payload)


def test_missing_approval_refuses():
    payload = evaluate_scheduler_activation_gate(build_scheduler_activation_request(dry_run_reviewed=True))
    assert payload["decision"]["decision"] == SchedulerActivationDecisionValue.REFUSED.value


def test_valid_gate_creates_decision_only(monkeypatch):
    monkeypatch.setenv("DELTA_EVALUATOR_SCHEDULE_ENABLED", "true")
    monkeypatch.setenv("DELTA_EVALUATOR_ENABLED", "true")
    monkeypatch.setenv("DELTA_EVALUATOR_ALLOW_LIVE_CALL", "true")
    monkeypatch.setenv("DELTA_EVALUATOR_API_KEY", "test-key")
    request = build_scheduler_activation_request(SCHEDULER_APPROVAL_TOKEN, dry_run_reviewed=True)
    payload = evaluate_scheduler_activation_gate(request)
    assert payload["decision"]["decision"] == SchedulerActivationDecisionValue.DECISION_ONLY_ALLOWED.value
    assert payload["decision"]["applied"] is False
    assert payload["decision"]["scheduler_started"] is False
    assert validate_scheduler_activation_gate_safe(payload)


def test_missing_key_or_live_gate_refuses(monkeypatch):
    monkeypatch.setenv("DELTA_EVALUATOR_SCHEDULE_ENABLED", "true")
    monkeypatch.setenv("DELTA_EVALUATOR_ENABLED", "true")
    monkeypatch.setenv("DELTA_EVALUATOR_ALLOW_LIVE_CALL", "false")
    monkeypatch.delenv("DELTA_EVALUATOR_API_KEY", raising=False)
    request = build_scheduler_activation_request(SCHEDULER_APPROVAL_TOKEN, dry_run_reviewed=True)
    payload = evaluate_scheduler_activation_gate(request)
    assert payload["decision"]["decision"] == SchedulerActivationDecisionValue.REFUSED.value
    assert validate_scheduler_activation_gate_safe(payload)


def test_no_side_effects_and_model_defaults(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    payload = write_scheduler_activation_gate_report()
    flags = payload["invariant_flags"]
    assert flags["api_call_performed"] is False
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False
