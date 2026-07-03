from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_active_specialist_routing import (
    RUNTIME_V14N_INVARIANT_FLAGS,
    SpecialistRoutingOutcome,
    SpecialistRoutingRequestKind,
    SpecialistType,
    create_specialist_provider_contract,
    create_specialist_routing_gate,
    create_specialist_routing_plan,
    create_specialist_routing_report_entry,
    create_specialist_routing_request,
    create_specialist_routing_trace,
    decide_specialist_routing,
    validate_specialist_provider_contract_inactive,
    validate_specialist_routing_decision_report_only,
    validate_specialist_routing_gate_closed,
    validate_specialist_routing_plan_inert,
    validate_specialist_routing_report_entry_review_only,
    validate_specialist_routing_request_inert,
    validate_specialist_routing_trace_review_only,
)
from orchestration.runtime.v14_active_specialist_routing_report import (
    build_active_specialist_routing_report_data,
    write_active_specialist_routing_report,
)


def _routing_parts():
    request = create_specialist_routing_request(
        request_kind=SpecialistRoutingRequestKind.CONTRADICTION_CHECK,
        question="Should this contradiction be checked by a specialist?",
        evidence_gap="contradiction direction is unclear",
        lane_scope=("reasoning",),
        source_trace_ids=("trace-1",),
    )
    gate = create_specialist_routing_gate(request.request_id)
    contract = create_specialist_provider_contract(
        specialist_type=request.preferred_specialist,
        allowed_input_kinds=(request.request_kind,),
    )
    decision = decide_specialist_routing(request, gate, contract)
    trace = create_specialist_routing_trace(request, gate, contract, decision)
    return request, gate, contract, decision, trace


def test_importing_active_specialist_routing_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14N_INVARIANT_FLAGS.values())


def test_specialist_routing_request_is_deterministic_and_inert():
    first = create_specialist_routing_request(
        request_kind=SpecialistRoutingRequestKind.MATH_CHECK,
        question="Calculate whether this plan is feasible.",
        evidence_gap="numeric feasibility needs review",
    )
    second = create_specialist_routing_request(
        request_kind=SpecialistRoutingRequestKind.MATH_CHECK,
        question="Calculate whether this plan is feasible.",
        evidence_gap="numeric feasibility needs review",
    )

    assert first.request_id == second.request_id
    assert first.preferred_specialist == SpecialistType.MATH_SPECIALIST
    assert validate_specialist_routing_request_inert(first)


def test_specialist_gate_is_closed_and_requires_approval():
    request, gate, _, _, _ = _routing_parts()

    assert gate.request_id == request.request_id
    assert gate.human_approval_required is True
    assert gate.human_approval_present is False
    assert validate_specialist_routing_gate_closed(gate)


def test_specialist_contract_is_inactive_and_non_authoritative():
    _, _, contract, _, _ = _routing_parts()

    assert contract.active is False
    assert contract.provider_calls_enabled is False
    assert contract.network_enabled is False
    assert contract.authority_granted is False
    assert contract.may_write_memory is False
    assert validate_specialist_provider_contract_inactive(contract)


def test_specialist_routing_decision_is_gated_report_only():
    _, _, _, decision, _ = _routing_parts()

    assert decision.outcome == SpecialistRoutingOutcome.GATED_OFF
    assert decision.applied is False
    assert decision.provider_called is False
    assert decision.routing_executed is False
    assert decision.memory_written is False
    assert decision.canonical_written is False
    assert decision.merge_protocol_invoked is False
    assert validate_specialist_routing_decision_report_only(decision)


def test_specialist_routing_trace_plan_and_entry_are_review_only():
    request, gate, contract, decision, trace = _routing_parts()
    plan = create_specialist_routing_plan(requests=(request,), decisions=(decision,), traces=(trace,))
    entry = create_specialist_routing_report_entry(
        trace=trace,
        request=request,
        gate=gate,
        contract=contract,
        decision=decision,
        unresolved_gaps=("approval surface missing",),
    )

    assert validate_specialist_routing_trace_review_only(trace)
    assert validate_specialist_routing_plan_inert(plan)
    assert validate_specialist_routing_report_entry_review_only(entry)
    assert plan.provider_calls_enabled is False
    assert entry.generated_for_review_only is True


def test_active_specialist_routing_report_data_is_scaffold_only():
    data = build_active_specialist_routing_report_data()

    assert data["final_recommendation"] == "PROCEED_EXECUTION_AUTHORIZATION_DESIGN"
    assert data["status"] == "design_scaffold_only"
    assert data["decision"]["provider_called"] is False
    assert data["decision"]["routing_executed"] is False
    assert data["contract"]["active"] is False
    assert all(value is False for value in data["invariant_flags"].values())


def test_write_active_specialist_routing_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_active_specialist_routing_report as report_module

    md_path = tmp_path / "routing.md"
    json_path = tmp_path / "routing.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_active_specialist_routing_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
