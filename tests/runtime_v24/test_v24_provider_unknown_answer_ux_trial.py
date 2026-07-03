from orchestration.runtime.v24_provider_unknown_answer_ux_trial import APPROVAL_TEXT, run_provider_unknown_answer_ux_trial, validate_provider_unknown_answer_ux_safe
from orchestration.runtime.v24_provider_unknown_answer_ux_trial_report import write_provider_unknown_answer_ux_report


def _transport(url, headers, payload, timeout):
    return {"answer_text": "Mock evidence only.", "provenance": "mock", "uncertainty": "unverified"}


def test_dry_run_and_known_question_refuses_provider_path():
    known = run_provider_unknown_answer_ux_trial("What does DELTA know about HYB1?", live_provider=True)
    unknown = run_provider_unknown_answer_ux_trial("unknown topic")
    assert "known_local_question" in known["blocks"]
    assert unknown["decision"]["provider_call_performed"] is False


def test_live_refuses_without_approval_gates_or_key():
    payload = run_provider_unknown_answer_ux_trial("unknown topic", live_provider=True, env={})
    assert payload["decision"]["provider_call_performed"] is False
    assert payload["provider_trial"]["gate"]["blocks"]


def test_mocked_live_returns_evidence_packet_only():
    payload = run_provider_unknown_answer_ux_trial("unknown topic", approval_text=APPROVAL_TEXT, live_provider=True, env={"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}, transport=_transport)
    assert payload["decision"]["provider_call_performed"] is True
    assert payload["decision"]["provider_answer_authoritative"] is False
    assert validate_provider_unknown_answer_ux_safe(payload)


def test_key_redacted_and_no_mutation():
    payload = run_provider_unknown_answer_ux_trial("unknown topic")
    assert payload["redaction"]["api_key_redacted"] is True
    assert payload["decision"]["memory_write_performed"] is False
    assert payload["decision"]["recall_mutated"] is False


def test_report_generation():
    data = write_provider_unknown_answer_ux_report()
    assert data["all_safe"] is True

