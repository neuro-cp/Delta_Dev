from __future__ import annotations

from orchestration.runtime.v18_manual_provider_live_trial import run_provider_live_trial, validate_provider_live_trial_safe
from orchestration.runtime.v18_manual_provider_live_trial_report import write_provider_live_trial_report


def test_dry_run_works_without_key():
    payload = run_provider_live_trial("What is a recent fact DELTA cannot know locally?", env={})
    assert payload["trace"]["decision"]["decision"] == "dry_run_provider_request"
    assert payload["trace"]["decision"]["provider_call_performed"] is False
    assert validate_provider_live_trial_safe(payload)


def test_live_refuses_without_env_gates():
    payload = run_provider_live_trial("What is a recent fact DELTA cannot know locally?", live_provider=True, env={})
    assert payload["trace"]["decision"]["decision"] == "live_refused_by_gate"
    assert validate_provider_live_trial_safe(payload)


def test_live_refuses_without_key():
    env = {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true"}
    payload = run_provider_live_trial("What is a recent fact DELTA cannot know locally?", live_provider=True, env=env)
    assert payload["trace"]["decision"]["decision"] == "live_refused_by_gate"
    assert validate_provider_live_trial_safe(payload)


def test_known_local_question_refuses_provider_path():
    env = {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}
    payload = run_provider_live_trial("What is Model B?", live_provider=True, env=env)
    assert payload["trace"]["decision"]["decision"] == "local_known_provider_refused"
    assert payload["trace"]["decision"]["provider_call_performed"] is False


def test_mocked_live_response_becomes_evidence_packet():
    env = {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test", "DELTA_UNKNOWN_PROVIDER_ENDPOINT": "mock://endpoint", "DELTA_UNKNOWN_PROVIDER_MODEL": "mock"}

    def fake_transport(endpoint, headers, body, timeout):
        return {"choices": [{"message": {"content": "mock provider evidence"}}]}

    payload = run_provider_live_trial("What is a recent fact DELTA cannot know locally?", live_provider=True, env=env, transport=fake_transport)
    assert payload["trace"]["decision"]["decision"] == "live_evidence_packet"
    assert payload["trace"]["evidence_packet"]["authoritative"] is False
    assert payload["trace"]["redacted_request"]["api_key_redacted"] is True
    assert validate_provider_live_trial_safe(payload)


def test_no_mutation_training_action_scheduler_or_hyb1_change():
    payload = run_provider_live_trial("Unknown", env={})
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["action_execution_performed"] is False
    assert flags["scheduler_enabled"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_provider_live_trial_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_PROVIDER_EVIDENCE_POST_REVIEW"
