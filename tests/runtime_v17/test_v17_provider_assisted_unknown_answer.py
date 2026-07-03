from __future__ import annotations

from orchestration.runtime.v17_provider_assisted_unknown_answer import (
    UnknownAnswerDecisionValue,
    answer_unknown_with_controlled_provider,
    validate_unknown_answer_safe,
)


def test_known_local_question_does_not_call_provider():
    payload = answer_unknown_with_controlled_provider("What is Model B?", live_provider=True)
    assert payload["decision"]["decision"] == UnknownAnswerDecisionValue.LOCAL_KNOWN.value
    assert payload["decision"]["provider_call_performed"] is False
    assert validate_unknown_answer_safe(payload)


def test_unknown_question_dry_runs_request():
    payload = answer_unknown_with_controlled_provider("What recent thing happened?")
    assert payload["decision"]["decision"] == UnknownAnswerDecisionValue.DRY_RUN_PROVIDER_REQUEST.value
    assert payload["route_or_provider_request"]["api_key_redacted"] is True
    assert validate_unknown_answer_safe(payload)


def test_live_refuses_without_gates():
    payload = answer_unknown_with_controlled_provider("What recent thing happened?", live_provider=True)
    assert payload["decision"]["decision"] in {UnknownAnswerDecisionValue.LIVE_REFUSED.value, UnknownAnswerDecisionValue.LIVE_EVIDENCE_PACKET.value}
    assert validate_unknown_answer_safe(payload)


def test_mocked_provider_response_becomes_evidence_packet(monkeypatch):
    monkeypatch.setattr("orchestration.runtime.v17_provider_assisted_unknown_answer.parse_env_file", lambda: {"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_EVALUATOR_API_KEY": "test", "DELTA_UNKNOWN_PROVIDER_MODEL": "mock", "DELTA_UNKNOWN_PROVIDER_ENDPOINT": "mock://endpoint"})

    def fake_transport(endpoint, headers, body, timeout):
        return {"choices": [{"message": {"content": "provider evidence"}}]}

    payload = answer_unknown_with_controlled_provider("What recent thing happened?", live_provider=True, transport=fake_transport)
    assert payload["decision"]["decision"] == UnknownAnswerDecisionValue.LIVE_EVIDENCE_PACKET.value
    assert payload["evidence_packet"]["authoritative"] is False
    assert validate_unknown_answer_safe(payload)


def test_no_memory_training_action_or_recall_mutation():
    payload = answer_unknown_with_controlled_provider("Unknown question")
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["action_execution_performed"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False
