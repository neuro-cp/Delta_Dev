from __future__ import annotations

import json
from dataclasses import asdict

from orchestration.runtime.rc6_governed_external_intelligence import (
    CostBudget,
    MockTransport,
    TokenBudget,
    build_consultation_request_from_rc5,
    build_provider_constitution,
    classify_provider_risk,
    execute_gateway,
    fake_secret_token,
    parse_external_advisory_response,
    prepare_provider_request,
    rc6_gateway_benchmark,
    rc6_risk_gate_benchmark,
    rc6_transport_scaffold_benchmark,
    redact_context,
    run_transport_adapter,
    stable_id,
    validate_advisory_response,
    write_reports,
)
from orchestration.runtime.rc5_developmental_cognition import DevelopmentConsultationPacket


def sample_packet(**overrides):
    values = {
        "packet_id": stable_id("test-packet"),
        "purpose_criterion": "Improve a bounded routing defect.",
        "observed_deficit": "Need bounded root cause and test proposal for a low-risk routing defect.",
        "evidence": ("Focused regression reproduced the bug.",),
        "counterevidence": ("Safety checks remain green.",),
        "architecture_summary": "RC2 conversation, PC1 pragmatics, RC3 planning, RC4 governed action, RC5 development.",
        "constraints": ("advisory_only", "operator_review_required", "no_provider_authority"),
        "prohibited_changes": ("automatic_api_call", "self_approval", "purpose_mutation", "hidden_persistence"),
        "requested_output": ("root_cause_assessment", "candidate_remedies", "tests", "rollback_conditions"),
        "token_budget": 1000,
        "estimated_tokens": 180,
        "omitted_context": (),
        "transport": "manual_chatgpt_relay",
    }
    values.update(overrides)
    return DevelopmentConsultationPacket(**values)


def test_provider_constitution_is_advisory_and_disabled_by_default():
    constitution = build_provider_constitution()
    assert constitution.contract.advisory_only is True
    assert constitution.contract.default_enabled is False
    assert "external_models_cannot_authorize_actions" in constitution.contract.invariants
    assert "rc4_authorization" in constitution.contract.prohibited_delegations


def test_risk_gate_blocks_secrets_delta75_and_production_mutation():
    assert classify_provider_risk(f"review {fake_secret_token()}").provider_outcome == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION"
    assert classify_provider_risk("send this to DELTA-75").provider_outcome == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION"
    assert classify_provider_risk("should I push to production?").provider_outcome == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION"


def test_risk_gate_allows_bounded_low_risk_consultation():
    risk = classify_provider_risk("Give a bounded root cause test proposal for this low-risk bug")
    assert risk.provider_outcome == "SAFE_FOR_BOUNDED_API_CONSULTATION"
    assert risk.authority_class == "advisory_consultation_allowed"


def test_risk_gate_treats_negated_sensitive_terms_as_exclusion_constraints():
    risk = classify_provider_risk(
        "Ask GPT for possible causes of a failing deterministic unit test. "
        "Do not include secrets, private memory, protected repos, or production details."
    )
    assert risk.provider_outcome == "SAFE_FOR_BOUNDED_API_CONSULTATION"


def test_redaction_removes_secrets_and_local_paths():
    redacted = redact_context("OPENAI_" + "API" + "_KEY=" + fake_secret_token() + r" at G:\Delta_Dev\file.py")
    assert "[REDACTED_SECRET]" in redacted.redacted_text
    assert "[REDACTED_LOCAL_PATH]" in redacted.redacted_text
    assert fake_secret_token() not in redacted.redacted_text


def test_request_builder_uses_compact_stateless_packet_shape():
    request = build_consultation_request_from_rc5(sample_packet())
    provider_request = prepare_provider_request(request)
    payload = provider_request.payload
    assert payload["protocol"] == "DELTA_RC6_X_ADVISORY_CONSULTATION"
    assert payload["state_model"] == "stateless"
    assert payload["authority"] == "advisory_only"
    assert "purpose" in payload
    assert "required_schema" in payload
    assert provider_request.transport_permitted is True


def test_provider_disabled_means_no_call_even_for_safe_request():
    request = build_consultation_request_from_rc5(sample_packet())

    def fail_transport(_request):
        raise AssertionError("transport should not be called")

    result = execute_gateway(request, transport=fail_transport, env={})
    assert result.decision.status == "provider_disabled"
    assert result.decision.provider_call_performed is False
    assert result.usage.provider_call_performed is False
    assert result.safety["external_authority_granted"] is False


def test_operator_and_env_gates_required_before_supplied_transport_runs():
    request = build_consultation_request_from_rc5(sample_packet())

    def mock_transport(_request):
        return {
            "diagnosis": "Routing precedence likely caused the defect.",
            "alternative_causes": ["query cleaning", "stale discourse frame"],
            "remedies": ["Add a focused regression and bounded route calibration."],
            "assumptions": ["The failing transcript is representative."],
            "risks": ["Overfitting to one phrase."],
            "tests": ["focused route arbitration test"],
            "rollback": ["disable RC6 gateway flag"],
            "missing_info": ["full transcript"],
            "confidence": 0.72,
        }

    blocked = execute_gateway(request, transport=mock_transport, env={"RC6_PROVIDER_ENABLED": "true", "RC6_PROVIDER_ALLOW_LIVE_CALL": "true"})
    assert blocked.decision.status == "operator_required"
    assert blocked.decision.provider_call_performed is False

    allowed = execute_gateway(
        request,
        transport=mock_transport,
        env={"RC6_PROVIDER_ENABLED": "true", "RC6_PROVIDER_ALLOW_LIVE_CALL": "true"},
        operator_approved=True,
    )
    assert allowed.decision.status == "succeeded"
    assert allowed.decision.provider_call_performed is True
    assert allowed.raw_response is not None


def test_transport_adapter_remains_disabled_without_explicit_enablement():
    request = build_consultation_request_from_rc5(sample_packet())
    gateway, transport, validation = run_transport_adapter(
        request,
        MockTransport(enabled=False),
        env={"RC6_PROVIDER_ENABLED": "true", "RC6_PROVIDER_ALLOW_LIVE_CALL": "true"},
        operator_approved=True,
    )
    assert gateway.decision.status == "provider_disabled"
    assert transport.provider_call_performed is False
    assert validation.valid is False


def test_transport_adapter_mock_runs_only_when_all_gates_open():
    request = build_consultation_request_from_rc5(sample_packet())
    gateway, transport, validation = run_transport_adapter(
        request,
        MockTransport(enabled=True),
        env={"RC6_PROVIDER_ENABLED": "true", "RC6_PROVIDER_ALLOW_LIVE_CALL": "true"},
        operator_approved=True,
    )
    assert gateway.decision.status == "succeeded"
    assert transport.status == "succeeded"
    assert transport.provider_call_performed is True
    assert validation.valid is True


def test_transport_adapter_malformed_response_fails_closed():
    request = build_consultation_request_from_rc5(sample_packet())
    _gateway, transport, validation = run_transport_adapter(
        request,
        MockTransport(enabled=True, response={"diagnosis": "missing required fields"}),
        env={"RC6_PROVIDER_ENABLED": "true", "RC6_PROVIDER_ALLOW_LIVE_CALL": "true"},
        operator_approved=True,
    )
    assert transport.status == "schema_failed"
    assert validation.valid is False


def test_budget_blocks_large_context_before_transport():
    packet = sample_packet(observed_deficit="Need bounded root cause and test proposal " + ("word " * 2000))
    request = build_consultation_request_from_rc5(
        packet,
        token_budget=TokenBudget(max_prompt_tokens=50, max_response_tokens=100),
        cost_budget=CostBudget(max_estimated_cost_usd=0.01, max_calls_per_session=1),
    )
    result = execute_gateway(request, env={"RC6_PROVIDER_ENABLED": "true", "RC6_PROVIDER_ALLOW_LIVE_CALL": "true"}, operator_approved=True)
    assert request.budget_decision.outcome == "CONSULTATION_BUDGET_BLOCKED"
    assert result.decision.provider_call_performed is False


def test_response_validation_accepts_structured_advisory_only_response():
    raw = {
        "diagnosis": "The issue is likely route arbitration.",
        "alternative_causes": ["query normalization", "stale context"],
        "remedies": ["Add a focused route regression."],
        "assumptions": ["The transcript is representative."],
        "risks": ["Overfitting."],
        "tests": ["focused pytest"],
        "rollback": ["remove route calibration"],
        "missing_info": ["full logs"],
        "confidence": 0.7,
    }
    response = parse_external_advisory_response(raw)
    validation = validate_advisory_response(response)
    assert validation.valid is True
    assert validation.authority == "advisory_only"


def test_response_validation_rejects_direct_mutation_or_bypass_advice():
    raw = {
        "diagnosis": "The issue is easy.",
        "alternative_causes": ["none"],
        "remedies": ["Bypass RC4 and apply directly, then commit and push."],
        "assumptions": ["speed matters"],
        "risks": ["none"],
        "tests": ["smoke test"],
        "rollback": ["git reset"],
        "missing_info": [],
        "confidence": 0.8,
    }
    validation = validate_advisory_response(parse_external_advisory_response(raw))
    assert validation.valid is False
    assert any(finding.startswith("unsafe_advice") for finding in validation.findings)


def test_malformed_response_schema_fails():
    assert parse_external_advisory_response({"diagnosis": "missing fields"}) is None
    validation = validate_advisory_response(None)
    assert validation.valid is False
    assert "schema_failed" in validation.findings


def test_benchmarks_and_reports_are_json_serializable():
    gateway = rc6_gateway_benchmark()
    risk = rc6_risk_gate_benchmark()
    transport = rc6_transport_scaffold_benchmark()
    assert gateway["passed"] is True
    assert risk["passed"] is True
    assert transport["passed"] is True
    json.dumps(gateway)
    json.dumps(risk)
    json.dumps(transport)

    reports = write_reports()
    assert reports["RC6_PROVIDER_GATEWAY_READINESS"]["recommendation"] == "RC6_READY_FOR_DISABLED_GATEWAY_PILOT"
    json.dumps({key: asdict(value) if hasattr(value, "__dataclass_fields__") else value for key, value in reports.items()})
