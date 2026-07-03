from __future__ import annotations

from orchestration.runtime.v18_manual_provider_live_trial_gate import ProviderLiveTrialGateStatus, check_provider_live_trial_gate, validate_provider_live_trial_gate_safe
from orchestration.runtime.v18_manual_provider_live_trial_gate_report import write_provider_live_trial_gate_report


def test_gate_disabled_by_default():
    payload = check_provider_live_trial_gate("What is a recent fact DELTA cannot know locally?", env={})
    assert payload["decision"]["status"] == ProviderLiveTrialGateStatus.REFUSED.value
    assert validate_provider_live_trial_gate_safe(payload)


def test_refuses_without_provider_enabled():
    env = {"DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}
    payload = check_provider_live_trial_gate("What is a recent fact DELTA cannot know locally?", env=env)
    assert payload["decision"]["status"] == ProviderLiveTrialGateStatus.REFUSED.value


def test_refuses_without_live_call_allowed():
    env = {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}
    payload = check_provider_live_trial_gate("What is a recent fact DELTA cannot know locally?", env=env)
    assert payload["decision"]["status"] == ProviderLiveTrialGateStatus.REFUSED.value


def test_refuses_without_key():
    env = {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true"}
    payload = check_provider_live_trial_gate("What is a recent fact DELTA cannot know locally?", env=env)
    assert payload["decision"]["status"] == ProviderLiveTrialGateStatus.REFUSED.value


def test_refuses_local_known_answer():
    env = {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}
    payload = check_provider_live_trial_gate("What is Model B?", env=env)
    assert payload["decision"]["status"] == ProviderLiveTrialGateStatus.REFUSED.value


def test_permits_only_unsupported_question_with_gates_and_key():
    env = {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}
    payload = check_provider_live_trial_gate("What is a recent fact DELTA cannot know locally?", env=env)
    assert payload["decision"]["status"] == ProviderLiveTrialGateStatus.PERMITTED.value
    assert payload["decision"]["provider_call_performed"] is False
    assert validate_provider_live_trial_gate_safe(payload)


def test_no_mutation_training_hyb1_or_model_change():
    payload = check_provider_live_trial_gate("Unknown", env={})
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_provider_live_trial_gate_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_MANUAL_PROVIDER_LIVE_TRIAL_OPTIONAL_ONE_SHOT"
