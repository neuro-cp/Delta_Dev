from __future__ import annotations

import json

from orchestration.runtime.rc11_rc12_systems_plateau import (
    architecture_inventory,
    build_integrated_trace,
    build_plateau_operator_dashboard,
    capability_matrix,
    cross_layer_contract_audit,
    long_conversation_campaign_stress,
    plateau_benchmark,
    plateau_operator_workflow,
    plateau_readiness_final,
    post_rc_transition_proposal,
    practical_usefulness_review,
    rc11_cross_layer_adversarial_report,
    rc11_integrated_hardening_report,
    rc11_operational_readiness_report,
    rc12_governance_audit,
    render_plateau_operator_dashboard,
    resource_stress_measurement,
    risk_escalation_stress,
    safety_metadata,
    write_reports,
)


def test_integrated_trace_exposes_every_layer_without_live_authority():
    trace = build_integrated_trace("Review a low-risk UI wording proposal and keep it proposal-only.")
    for key in (
        "discourse_frame",
        "pragmatic_frame",
        "goal",
        "plan",
        "governance",
        "risk",
        "specialist_selection",
        "retrieval_decision",
        "provider_decision",
        "action_proposal",
        "validation",
        "developmental_evaluation",
        "campaign_update",
        "final_response_policy",
    ):
        assert key in trace
    assert trace["provider_decision"]["provider_call_performed"] is False
    assert trace["retrieval_decision"]["external_retrieval_performed"] is False
    assert trace["action_proposal"]["implementation_performed"] is False


def test_cross_layer_contract_audit_and_stress_fixtures_pass():
    assert cross_layer_contract_audit()["passed"] is True
    assert long_conversation_campaign_stress()["passed"] is True
    assert risk_escalation_stress()["passed"] is True
    assert practical_usefulness_review()["passed"] is True
    assert resource_stress_measurement()["optimization_performed"] is False


def test_rc11_reports_pass_without_external_activity():
    hardening = rc11_integrated_hardening_report()
    adversarial = rc11_cross_layer_adversarial_report()
    readiness = rc11_operational_readiness_report()
    assert hardening["recommendation"] == "RC11_INTEGRATED_OPERATIONAL_HARDENING_COMPLETE"
    assert adversarial["passed"] is True
    assert readiness["passed"] is True
    assert safety_metadata()["provider_calls_performed"] is False
    assert safety_metadata()["network_calls_performed"] is False
    json.dumps(hardening)
    json.dumps(adversarial)
    json.dumps(readiness)


def test_rc12_inventory_matrix_benchmark_and_governance_are_honest():
    inventory = architecture_inventory()
    matrix = capability_matrix()
    benchmark = plateau_benchmark()
    governance = rc12_governance_audit()
    readiness = plateau_readiness_final()
    assert inventory["passed"] is True
    assert matrix["passed"] is True
    assert benchmark["passed"] is True
    assert governance["passed"] is True
    assert readiness["plateau_recommendation"] == "DELTA_RC_PLATEAU_READY_WITH_GATED_CAPABILITIES"
    assert any(row["status"] == "DISABLED" for row in matrix["matrix"])
    assert "real operator campaign evidence gap" in readiness["remaining_risks"]


def test_plateau_operator_dashboard_and_post_rc_transition_are_review_only():
    dashboard = build_plateau_operator_dashboard()
    rendered = render_plateau_operator_dashboard(dashboard)
    transition = post_rc_transition_proposal()
    workflow = plateau_operator_workflow()
    assert "Provider status: disabled" in rendered
    assert "Network status: disabled" in rendered
    assert transition["do_not_begin_post_rc_implementation"] is True
    assert workflow[0] == "normal_conversation"
    assert workflow[-1] == "operator_disposition"


def test_plateau_write_reports_creates_required_payloads():
    reports = write_reports()
    required = {
        "RC11_INTEGRATED_HARDENING",
        "RC11_CROSS_LAYER_ADVERSARIAL_EVALUATION",
        "RC11_OPERATIONAL_READINESS",
        "RC12_RC_ERA_ARCHITECTURE_INVENTORY",
        "RC12_CAPABILITY_MATRIX",
        "RC12_PLATEAU_BENCHMARK",
        "RC12_GOVERNANCE_AUDIT",
        "RC12_PLATEAU_READINESS_FINAL",
        "POST_RC_TRANSITION_PROPOSAL",
    }
    assert required.issubset(reports)
    assert reports["RC12_PLATEAU_READINESS_FINAL"]["recommendation"] == "DELTA_RC_PLATEAU_READY_WITH_GATED_CAPABILITIES"
    json.dumps(reports)
