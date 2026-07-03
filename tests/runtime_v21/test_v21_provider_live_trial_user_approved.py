from __future__ import annotations

from orchestration.runtime.v21_provider_live_trial_user_approved import (
    APPROVAL_TEXT,
    parse_provider_trial_approval,
    run_user_approved_provider_live_trial,
    validate_user_approved_provider_trial_safe,
)
from orchestration.runtime.v21_provider_live_trial_user_approved_report import write_provider_live_trial_user_approved_report


def _env(key: bool = True) -> dict[str, str]:
    return {
        "DELTA_UNKNOWN_PROVIDER_ENABLED": "true",
        "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true",
        "DELTA_UNKNOWN_PROVIDER_API_KEY": "test-key" if key else "put_key_here",
        "DELTA_UNKNOWN_PROVIDER_ENDPOINT": "https://example.invalid",
        "DELTA_UNKNOWN_PROVIDER_MODEL": "mock-model",
    }


def test_dry_run_works_without_key():
    payload = run_user_approved_provider_live_trial("recent unknown", env=_env(key=False))
    assert "dry_run_no_live_provider" in payload["gate"]["blocks"]
    assert payload["decision"]["provider_call_performed"] is False
    assert validate_user_approved_provider_trial_safe(payload)


def test_live_refuses_without_exact_approval():
    payload = run_user_approved_provider_live_trial("recent unknown", live_provider=True, env=_env())
    assert "exact_user_approval_required" in payload["gate"]["blocks"]


def test_live_refuses_without_env_gates():
    payload = run_user_approved_provider_live_trial("recent unknown", approval_text=APPROVAL_TEXT, live_provider=True, env={})
    assert "env_gates_required" in payload["gate"]["blocks"]


def test_live_refuses_without_key():
    payload = run_user_approved_provider_live_trial("recent unknown", approval_text=APPROVAL_TEXT, live_provider=True, env=_env(key=False))
    assert "api_key_required" in payload["gate"]["blocks"]


def test_known_local_question_refuses_provider():
    payload = run_user_approved_provider_live_trial("What is HYB1?", approval_text=APPROVAL_TEXT, live_provider=True, env=_env())
    assert "known_local_question" in payload["gate"]["blocks"]


def test_mocked_live_response_becomes_evidence_packet():
    def transport(endpoint, headers, body, timeout):
        return {"choices": [{"message": {"content": "mock provider answer"}}]}

    payload = run_user_approved_provider_live_trial("recent unknown", approval_text=APPROVAL_TEXT, live_provider=True, env=_env(), transport=transport)
    assert payload["decision"]["provider_call_performed"] is True
    assert payload["provider_evidence_packet"]["authoritative"] is False


def test_approval_parser_exact():
    assert parse_provider_trial_approval(APPROVAL_TEXT)["matches_required_shape"] is True


def test_report_generation():
    data = write_provider_live_trial_user_approved_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_DAILY_EVALUATOR_SCHEDULER_ACTIVATION_USER_APPROVED"
