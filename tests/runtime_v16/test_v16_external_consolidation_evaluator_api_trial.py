from __future__ import annotations

import json
import subprocess
import sys

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v16_env import DeltaEvaluatorEnv
from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import (
    ExternalEvaluatorTrialStatus,
    parse_external_evaluator_advisory_review,
    run_external_evaluator_api_trial,
    validate_external_evaluator_api_trial_safe,
)


def test_dry_run_works_without_key():
    env = DeltaEvaluatorEnv(api_key_present=False, enabled=False, allow_live_call=False)
    payload = run_external_evaluator_api_trial(env, live=False)
    assert payload["trial_result"]["status"] == ExternalEvaluatorTrialStatus.DRY_RUN_READY.value
    assert payload["trial_result"]["provider_call_performed"] is False
    assert payload["request"]["api_key_redacted"] is True
    assert validate_external_evaluator_api_trial_safe(payload)


def test_live_refuses_without_enabled_gate():
    env = DeltaEvaluatorEnv(api_key_present=True, enabled=False, allow_live_call=True)
    payload = run_external_evaluator_api_trial(env, live=True)
    assert payload["trial_result"]["status"] == ExternalEvaluatorTrialStatus.REFUSED_LIVE_DISABLED.value
    assert payload["trial_result"]["provider_call_performed"] is False
    assert validate_external_evaluator_api_trial_safe(payload)


def test_live_refuses_without_allow_live_gate():
    env = DeltaEvaluatorEnv(api_key_present=True, enabled=True, allow_live_call=False)
    payload = run_external_evaluator_api_trial(env, live=True)
    assert payload["trial_result"]["status"] == ExternalEvaluatorTrialStatus.REFUSED_LIVE_NOT_ALLOWED.value
    assert payload["trial_result"]["provider_call_performed"] is False
    assert validate_external_evaluator_api_trial_safe(payload)


def test_live_refuses_without_api_key():
    env = DeltaEvaluatorEnv(api_key_present=False, enabled=True, allow_live_call=True)
    payload = run_external_evaluator_api_trial(env, live=True)
    assert payload["trial_result"]["status"] == ExternalEvaluatorTrialStatus.REFUSED_API_KEY_MISSING.value
    assert payload["trial_result"]["provider_call_performed"] is False
    assert validate_external_evaluator_api_trial_safe(payload)


def test_request_redacts_api_key():
    env = DeltaEvaluatorEnv(api_key_present=True, api_key_masked="sk-t...test", enabled=True, allow_live_call=True)
    payload = run_external_evaluator_api_trial(env, live=False)
    assert payload["request"]["api_key_present"] is True
    assert payload["request"]["api_key_redacted"] is True
    assert "sk-t" not in json.dumps(payload["request"])


def test_mocked_live_response_parses_into_advisory_review():
    env = DeltaEvaluatorEnv(api_key_present=True, api_key_masked="sk-t...test", enabled=True, allow_live_call=True)
    calls = []

    def fake_transport(endpoint, headers, body, timeout_seconds):
        calls.append((endpoint, headers, body, timeout_seconds))
        return {"choices": [{"message": {"content": "{\"disposition\":\"hold_for_review\",\"rationale\":\"review only\",\"risk\":\"low\"}"}}]}

    payload = run_external_evaluator_api_trial(env, live=True, transport=fake_transport)
    assert len(calls) == 1
    assert payload["trial_result"]["status"] == ExternalEvaluatorTrialStatus.LIVE_CALL_COMPLETED.value
    assert payload["trial_result"]["provider_call_performed"] is True
    assert payload["advisory_review"]["disposition"] == "hold_for_review"
    assert payload["advisory_review"]["evaluator_result_authoritative"] is False
    assert validate_external_evaluator_api_trial_safe(payload)


def test_malformed_evaluator_response_becomes_parse_error_review():
    review = parse_external_evaluator_advisory_review("request-1", "not-json")
    assert review.parse_error is True
    assert review.disposition == "parse_error"
    assert review.evaluator_result_authoritative is False


def test_failed_live_call_is_safe():
    env = DeltaEvaluatorEnv(api_key_present=True, api_key_masked="sk-t...test", enabled=True, allow_live_call=True)

    def failing_transport(endpoint, headers, body, timeout_seconds):
        raise RuntimeError("network unavailable")

    payload = run_external_evaluator_api_trial(env, live=True, transport=failing_transport)
    assert payload["trial_result"]["status"] == ExternalEvaluatorTrialStatus.LIVE_CALL_FAILED_SAFE.value
    assert payload["trial_result"]["provider_call_performed"] is False
    assert validate_external_evaluator_api_trial_safe(payload)


def test_no_canonical_memory_recall_training_action_or_scheduler_side_effects(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    payload = run_external_evaluator_api_trial(live=False)
    result = payload["trial_result"]
    flags = payload["invariant_flags"]
    assert result["canonical_write_performed"] is False
    assert result["memory_mutated"] is False
    assert result["recall_mutated"] is False
    assert result["training_triggered"] is False
    assert result["action_execution_performed"] is False
    assert result["scheduler_started"] is False
    assert flags["scheduler_enabled"] is False
    assert flags["listener_enabled"] is False
    assert flags["queue_enabled"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False
    assert flags["hyb1_promoted"] is False


def test_script_show_request_is_dry_run_and_redacted():
    completed = subprocess.run(
        [sys.executable, "scripts/run_delta_evaluator_trial.py", "--show-request"],
        check=True,
        text=True,
        capture_output=True,
    )
    request = json.loads(completed.stdout)
    assert request["api_key_redacted"] is True
    assert "Authorization" not in completed.stdout
    assert "sk-" not in completed.stdout
