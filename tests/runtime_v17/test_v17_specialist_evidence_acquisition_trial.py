from __future__ import annotations

from orchestration.runtime.v17_specialist_evidence_acquisition_trial import (
    SpecialistEvidenceDecisionValue,
    run_specialist_evidence_trial,
    validate_specialist_evidence_trial_safe,
)
from orchestration.runtime.v17_specialist_evidence_acquisition_trial_report import write_specialist_evidence_trial_report


def test_dry_run_works():
    payload = run_specialist_evidence_trial("Specialized unknown")
    assert payload["decision"]["decision"] == SpecialistEvidenceDecisionValue.DRY_RUN_SPECIALIST_REQUEST.value
    assert validate_specialist_evidence_trial_safe(payload)


def test_known_local_question_needs_no_specialist():
    payload = run_specialist_evidence_trial("What is Model B?", live_specialist=True)
    assert payload["decision"]["decision"] == SpecialistEvidenceDecisionValue.LOCAL_KNOWN_NO_SPECIALIST.value
    assert payload["decision"]["provider_call_performed"] is False
    assert validate_specialist_evidence_trial_safe(payload)


def test_live_refuses_without_gates(monkeypatch):
    monkeypatch.setattr("orchestration.runtime.v17_specialist_evidence_acquisition_trial.parse_env_file", lambda: {})
    payload = run_specialist_evidence_trial("Specialized unknown", live_specialist=True)
    assert payload["decision"]["decision"] == SpecialistEvidenceDecisionValue.LIVE_REFUSED.value
    assert validate_specialist_evidence_trial_safe(payload)


def test_mocked_specialist_result_evidence_only(monkeypatch):
    monkeypatch.setattr("orchestration.runtime.v17_specialist_evidence_acquisition_trial.parse_env_file", lambda: {"DELTA_SPECIALIST_ROUTING_ENABLED": "true", "DELTA_SPECIALIST_ALLOW_LIVE_CALL": "true", "DELTA_EVALUATOR_API_KEY": "test", "DELTA_SPECIALIST_DEFAULT_MODEL": "mock", "DELTA_UNKNOWN_PROVIDER_ENDPOINT": "mock://endpoint"})

    def fake_transport(endpoint, headers, body, timeout):
        return {"choices": [{"message": {"content": "specialist evidence"}}]}

    payload = run_specialist_evidence_trial("Specialized unknown", live_specialist=True, transport=fake_transport)
    assert payload["decision"]["decision"] == SpecialistEvidenceDecisionValue.LIVE_EVIDENCE_PACKET.value
    assert payload["evidence_packet"]["authoritative"] is False
    assert payload["evidence_packet"]["merge_applied"] is False
    assert validate_specialist_evidence_trial_safe(payload)


def test_report_generation():
    data = write_specialist_evidence_trial_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_PROVIDER_EVIDENCE_REVIEW_UI_OR_LIMITED_GENERAL_RECALL_TRIAL"
