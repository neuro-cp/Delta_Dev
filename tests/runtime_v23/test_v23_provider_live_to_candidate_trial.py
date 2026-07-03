from orchestration.runtime.v21_provider_live_trial_user_approved import APPROVAL_TEXT as LIVE_APPROVAL_TEXT
from orchestration.runtime.v23_provider_live_to_candidate_trial import CONVERSION_APPROVAL_TEXT, run_provider_live_to_candidate_trial, validate_provider_live_to_candidate_safe
from orchestration.runtime.v23_provider_live_to_candidate_trial_report import write_provider_live_to_candidate_report


def _transport(url, headers, payload, timeout):
    return {"answer_text": "Provider evidence with provenance.", "provenance": "mock-provider", "uncertainty": "unverified"}


def test_dry_run_generates_no_call():
    payload = run_provider_live_to_candidate_trial("unknown", live_provider=False)
    assert payload["decision"]["provider_call_performed"] is False


def test_live_refuses_without_approval_gates_or_key():
    payload = run_provider_live_to_candidate_trial("unknown", live_provider=True, env={})
    assert payload["decision"]["provider_call_performed"] is False
    assert payload["provider_trial"]["gate"]["blocks"]


def test_mocked_live_evidence_can_become_candidate_draft_only():
    payload = run_provider_live_to_candidate_trial("unknown", live_provider=True, live_approval_text=LIVE_APPROVAL_TEXT, conversion_approval_text=CONVERSION_APPROVAL_TEXT, env={"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}, transport=_transport)
    assert payload["decision"]["candidate_created"] is True
    proposal = payload["candidate_conversion"]["proposal"]
    assert proposal["canonical_write_ready"] is False
    assert proposal["written"] is False
    assert validate_provider_live_to_candidate_safe(payload)


def test_conversion_refuses_without_exact_conversion_approval():
    payload = run_provider_live_to_candidate_trial("unknown", live_provider=True, live_approval_text=LIVE_APPROVAL_TEXT, env={"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}, transport=_transport)
    assert "exact_conversion_approval_required" in payload["blocks"]
    assert payload["candidate_conversion"] is None


def test_report_generation():
    data = write_provider_live_to_candidate_report()
    assert data["all_safe"] is True

