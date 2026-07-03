from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v15_integration_gate import (
    RUNTIME_V15A_INVARIANT_FLAGS,
    IntegrationGateDecisionOutcome,
    IntegrationGateStatus,
    IntegrationPrerequisiteType,
    IntegrationRequestedMode,
    IntegrationTargetType,
    create_closed_integration_targets,
    create_integration_activation_request,
    create_integration_gate_audit_record,
    create_integration_gate_decision,
    create_integration_gate_report_entry,
    create_integration_prerequisite,
    create_integration_rollback_requirement,
    create_integration_safety_gate,
    validate_activation_request_inert,
    validate_audit_record_review_only,
    validate_gate_decision_closed,
    validate_integration_target_closed,
    validate_prerequisite_unsatisfied,
    validate_report_entry_review_only,
    validate_rollback_requirement_inert,
    validate_safety_gate_closed,
)
from orchestration.runtime.v15_integration_gate_report import build_integration_gate_report_data, write_integration_gate_report


def _parts():
    target = create_closed_integration_targets()[0]
    prereq = create_integration_prerequisite(
        target=target,
        prerequisite_type=IntegrationPrerequisiteType.HUMAN_APPROVAL_REQUIRED,
        rationale="approval required",
    )
    gate = create_integration_safety_gate(
        target=target,
        invariant_requirements=("model_b_default_changed=false",),
        unresolved_gaps=("human approval",),
        blocked_capabilities=("activation",),
        gate_status=IntegrationGateStatus.CLOSED_BY_DEFAULT,
    )
    request = create_integration_activation_request(
        target=target,
        requested_mode=IntegrationRequestedMode.FUTURE_TRIAL_DESIGN,
        requester_summary="test",
        justification="future only",
    )
    decision = create_integration_gate_decision(
        target=target,
        request=request,
        outcome=IntegrationGateDecisionOutcome.KEEP_CLOSED,
        rationale="closed",
    )
    rollback = create_integration_rollback_requirement(target=target, rollback_strategy="restore baseline")
    audit = create_integration_gate_audit_record(
        target=target,
        prerequisite_ids=(prereq.prerequisite_id,),
        audit_summary="review only",
        decision=decision,
        safety_gate=gate,
    )
    entry = create_integration_gate_report_entry(
        target=target,
        prerequisite_summary="missing",
        safety_summary="closed",
        activation_request_summary="not applied",
        decision_summary="keep closed",
        rollback_summary="not executed",
        unresolved_gaps=("approval",),
        recommended_next_review_step="v15b",
    )
    return target, prereq, gate, request, decision, rollback, audit, entry


def test_importing_integration_gate_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V15A_INVARIANT_FLAGS.values())


def test_all_integration_targets_are_closed_by_default():
    targets = create_closed_integration_targets()
    assert len(targets) == 12
    assert {target.target_type for target in targets} == set(IntegrationTargetType)
    assert all(validate_integration_target_closed(target) for target in targets)
    hyb1 = next(target for target in targets if target.target_type == IntegrationTargetType.HYB1_RUNTIME_VARIANT)
    assert hyb1.gate_open is False
    assert hyb1.default_change_allowed is False


def test_prerequisite_safety_gate_request_decision_and_rollback_are_inert():
    target, prereq, gate, request, decision, rollback, audit, entry = _parts()
    assert validate_integration_target_closed(target)
    assert validate_prerequisite_unsatisfied(prereq)
    assert validate_safety_gate_closed(gate)
    assert validate_activation_request_inert(request)
    assert validate_gate_decision_closed(decision)
    assert validate_rollback_requirement_inert(rollback)
    assert validate_audit_record_review_only(audit)
    assert validate_report_entry_review_only(entry)


def test_report_data_states_all_gates_closed_no_activation():
    data = build_integration_gate_report_data()
    assert data["final_recommendation"] == "PROCEED_V15B_SELECTIVE_LIVE_ACTIVATION_PLAN_STILL_OFF_BY_DEFAULT"
    assert data["status"] == "integration-gate-design-only_all-gates-closed_no-activation"
    assert len(data["target_capabilities"]) == 12
    assert all(target["gate_open"] is False and target["active"] is False for target in data["target_capabilities"])
    assert data["decision"]["gate_opened"] is False
    assert data["decision"]["activation_enabled"] is False
    assert data["rollback_requirement"]["rollback_executed"] is False
    assert all(value is False for value in data["invariant_flags"].values())


def test_write_integration_gate_report(tmp_path, monkeypatch):
    from orchestration.runtime import v15_integration_gate_report as report_module

    md_path = tmp_path / "integration.md"
    json_path = tmp_path / "integration.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_integration_gate_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8").lower()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "integration-gate-design-only" in text
    assert "every gate remains closed" in text
