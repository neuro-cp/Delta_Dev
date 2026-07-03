from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_action_ledger import (
    RUNTIME_V14P_INVARIANT_FLAGS,
    ActionLedgerOutcome,
    ActionLedgerStatus,
    create_action_audit_trace,
    create_action_ledger_entry,
    create_action_ledger_plan,
    create_action_ledger_report_entry,
    create_action_rollback_reference,
    decide_action_ledger,
    validate_action_audit_trace_review_only,
    validate_action_ledger_decision_inert,
    validate_action_ledger_entry_inactive,
    validate_action_ledger_plan_inert,
    validate_action_ledger_report_entry_review_only,
    validate_action_rollback_reference_inert,
)
from orchestration.runtime.v14_action_ledger_report import (
    build_action_ledger_report_data,
    write_action_ledger_report,
)
from orchestration.runtime.v14_execution_authorization import (
    ActionIntentKind,
    RequestedExecutionMode,
    assess_execution_risk,
    create_action_intent,
    create_execution_approval_requirement,
    create_execution_authorization_request,
    create_execution_dry_run_plan,
    decide_execution_authorization,
)


def _ledger_parts():
    intent = create_action_intent(
        intent_kind=ActionIntentKind.NETWORK_OPERATION,
        description="future network action",
        requested_mode=RequestedExecutionMode.REVIEW_ONLY,
        source_trace_ids=("trace-1",),
    )
    risk = assess_execution_risk(intent)
    request = create_execution_authorization_request(intent, risk)
    approval = create_execution_approval_requirement(request, risk)
    auth_decision = decide_execution_authorization(request, approval)
    dry_run = create_execution_dry_run_plan(intent, auth_decision, planned_steps=("would not run network action",))
    entry = create_action_ledger_entry(
        action_intent_id=intent.intent_id,
        authorization_decision_id=auth_decision.decision_id,
        risk_assessment_id=risk.assessment_id,
        dry_run_plan_id=dry_run.dry_run_plan_id,
        source_reference_ids=intent.source_trace_ids,
        ledger_status=ActionLedgerStatus.BLOCKED_MISSING_APPROVAL,
        action_summary="network action remains blocked",
    )
    audit = create_action_audit_trace(
        entry,
        authorization_reference_ids=(auth_decision.decision_id,),
        risk_reference_ids=(risk.assessment_id,),
        decision_reference_ids=(auth_decision.decision_id,),
        trace_summary="review-only audit",
    )
    rollback = create_action_rollback_reference(entry, rollback_possible=False)
    decision = decide_action_ledger(entry)
    return entry, audit, rollback, decision


def test_importing_action_ledger_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V14P_INVARIANT_FLAGS["human_approval_required_for_risky_actions"] is True
    assert RUNTIME_V14P_INVARIANT_FLAGS["authorization_required_before_ledger"] is True
    assert RUNTIME_V14P_INVARIANT_FLAGS["ledger_required_before_execution"] is True
    assert all(
        value is False
        for key, value in RUNTIME_V14P_INVARIANT_FLAGS.items()
        if key
        not in {
            "human_approval_required_for_risky_actions",
            "authorization_required_before_ledger",
            "ledger_required_before_execution",
        }
    )


def test_action_ledger_entry_is_deterministic_inactive_and_not_persisted():
    first = create_action_ledger_entry(
        action_intent_id="intent-1",
        source_reference_ids=("trace-1",),
        action_summary="future action",
    )
    second = create_action_ledger_entry(
        action_intent_id="intent-1",
        source_reference_ids=("trace-1",),
        action_summary="future action",
    )

    assert first.ledger_entry_id == second.ledger_entry_id
    assert first.ledger_status == ActionLedgerStatus.BLOCKED_MISSING_AUTHORIZATION
    assert first.active is False
    assert first.persisted_to_active_ledger is False
    assert first.action_executed is False
    assert first.side_effects_created is False
    assert first.tool_called is False
    assert first.provider_called is False
    assert first.autonomous_approval_used is False
    assert first.memory_mutated is False
    assert first.runtime_recall_mutated is False
    assert first.training_triggered is False
    assert validate_action_ledger_entry_inactive(first)


def test_action_ledger_plan_is_append_only_shape_but_not_active():
    entry, _, _, _ = _ledger_parts()
    plan = create_action_ledger_plan((entry,))

    assert plan.required_before_execution is True
    assert plan.append_only_required is True
    assert plan.immutable_audit_required is True
    assert plan.rollback_reference_required is True
    assert plan.active_ledger_enabled is False
    assert plan.ledger_persistence_enabled is False
    assert plan.action_execution_enabled is False
    assert plan.side_effects_enabled is False
    assert plan.scheduler_enabled is False
    assert plan.background_queue_enabled is False
    assert validate_action_ledger_plan_inert(plan)


def test_audit_trace_is_review_only_and_not_persisted():
    _, audit, _, _ = _ledger_parts()

    assert audit.generated_for_review_only is True
    assert audit.persisted_to_active_ledger is False
    assert audit.applied is False
    assert validate_action_audit_trace_review_only(audit)


def test_rollback_reference_does_not_execute_rollback():
    _, _, rollback, _ = _ledger_parts()

    assert rollback.rollback_requires_human_approval is True
    assert rollback.rollback_executed is False
    assert rollback.side_effect_reversal_executed is False
    assert validate_action_rollback_reference_inert(rollback)


def test_action_ledger_decision_is_not_applied_and_writes_nothing():
    _, _, _, decision = _ledger_parts()

    assert decision.outcome == ActionLedgerOutcome.BLOCKED_MISSING_HUMAN_APPROVAL
    assert decision.applied is False
    assert decision.ledger_written is False
    assert decision.action_executed is False
    assert decision.side_effects_created is False
    assert validate_action_ledger_decision_inert(decision)


def test_action_ledger_report_entry_is_review_only():
    entry, audit, rollback, decision = _ledger_parts()
    report_entry = create_action_ledger_report_entry(
        entry=entry,
        audit_trace=audit,
        rollback_reference=rollback,
        decision=decision,
        unresolved_gaps=("approval missing",),
    )

    assert report_entry.generated_for_review_only is True
    assert report_entry.unresolved_gaps == ("approval missing",)
    assert validate_action_ledger_report_entry_review_only(report_entry)


def test_action_ledger_report_data_states_no_execution_or_side_effects():
    data = build_action_ledger_report_data()

    assert data["final_recommendation"] == "PROCEED_DRY_RUN_ACTION_EXECUTION_DESIGN"
    assert data["status"] == "ledger_design_only_no_execution_no_side_effects"
    assert data["ledger_entry"]["persisted_to_active_ledger"] is False
    assert data["ledger_entry"]["action_executed"] is False
    assert data["ledger_entry"]["side_effects_created"] is False
    assert data["ledger_decision"]["ledger_written"] is False
    assert data["ledger_decision"]["action_executed"] is False
    assert data["rollback_reference"]["rollback_executed"] is False
    assert "action execution" in data["inactive_systems"]
    assert "tool calls" in data["inactive_systems"]
    assert "provider calls" in data["inactive_systems"]


def test_write_action_ledger_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_action_ledger_report as report_module

    md_path = tmp_path / "ledger.md"
    json_path = tmp_path / "ledger.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_action_ledger_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    md_text = md_path.read_text(encoding="utf-8")

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
    assert "ledger-design-only" in md_text.lower() or "ledger design" in md_text.lower()
    assert "no action execution" in md_text.lower() or "does not add active ledger persistence" in md_text.lower()
