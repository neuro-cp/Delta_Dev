from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_execution_authorization import (
    RUNTIME_V14O_INVARIANT_FLAGS,
    ActionIntentKind,
    ExecutionApprovalType,
    ExecutionAuthorizationOutcome,
    ExecutionRiskLevel,
    RequestedExecutionMode,
    assess_execution_risk,
    create_action_intent,
    create_execution_approval_requirement,
    create_execution_authorization_report_entry,
    create_execution_authorization_request,
    create_execution_authorization_trace,
    create_execution_dry_run_plan,
    decide_execution_authorization,
    validate_action_intent_inert,
    validate_execution_approval_requirement_unsatisfied,
    validate_execution_authorization_decision_inert,
    validate_execution_authorization_request_inert,
    validate_execution_dry_run_plan_inert,
    validate_execution_report_entry_review_only,
    validate_execution_risk_assessment_review_only,
    validate_execution_trace_review_only,
)
from orchestration.runtime.v14_execution_authorization_report import (
    build_execution_authorization_report_data,
    write_execution_authorization_report,
)


def _authorization_parts():
    intent = create_action_intent(
        intent_kind=ActionIntentKind.FILE_OPERATION,
        description="write a future report file",
        target_reference="reports/future.md",
        requested_mode=RequestedExecutionMode.REVIEW_ONLY,
        lane_scope=("execution",),
        source_trace_ids=("trace-1",),
    )
    assessment = assess_execution_risk(intent)
    request = create_execution_authorization_request(intent, assessment)
    requirement = create_execution_approval_requirement(request, assessment)
    decision = decide_execution_authorization(request, requirement)
    dry_run_plan = create_execution_dry_run_plan(intent, decision, planned_steps=("would write report",))
    trace = create_execution_authorization_trace(
        intent=intent,
        assessment=assessment,
        request=request,
        requirement=requirement,
        decision=decision,
        dry_run_plan=dry_run_plan,
    )
    return intent, assessment, request, requirement, decision, dry_run_plan, trace


def test_importing_execution_authorization_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert RUNTIME_V14O_INVARIANT_FLAGS["human_approval_required_for_risky_actions"] is True
    assert RUNTIME_V14O_INVARIANT_FLAGS["action_ledger_required_before_execution"] is True
    assert all(
        value is False
        for key, value in RUNTIME_V14O_INVARIANT_FLAGS.items()
        if key not in {"human_approval_required_for_risky_actions", "action_ledger_required_before_execution"}
    )


def test_action_intent_is_deterministic_and_non_executable():
    first = create_action_intent(
        intent_kind=ActionIntentKind.CALL_TOOL,
        description="call a future tool",
        target_reference="tool-x",
    )
    second = create_action_intent(
        intent_kind=ActionIntentKind.CALL_TOOL,
        description="call a future tool",
        target_reference="tool-x",
    )

    assert first.intent_id == second.intent_id
    assert first.executable is False
    assert first.side_effects_allowed is False
    assert first.tool_calls_allowed is False
    assert validate_action_intent_inert(first)


def test_execution_risk_assessment_requires_action_ledger():
    intent = create_action_intent(intent_kind=ActionIntentKind.DATABASE_OPERATION, description="change a database")
    assessment = assess_execution_risk(intent)

    assert assessment.risk_level == ExecutionRiskLevel.HIGH
    assert assessment.side_effect_potential is True
    assert assessment.requires_action_ledger is True
    assert validate_execution_risk_assessment_review_only(assessment)


def test_authorization_request_and_requirement_are_not_satisfied():
    intent, assessment, request, requirement, _, _, _ = _authorization_parts()

    assert request.intent_id == intent.intent_id
    assert request.assessment_id == assessment.assessment_id
    assert request.human_approval_present is False
    assert request.autonomous_approval_allowed is False
    assert requirement.approval_type == ExecutionApprovalType.ADMIN_REQUIRED
    assert requirement.satisfied is False
    assert validate_execution_authorization_request_inert(request)
    assert validate_execution_approval_requirement_unsatisfied(requirement)


def test_execution_authorization_decision_is_review_only_and_inert():
    _, _, _, _, decision, _, _ = _authorization_parts()

    assert decision.outcome == ExecutionAuthorizationOutcome.REVIEW_ONLY
    assert decision.execution_authorized is False
    assert decision.action_executed is False
    assert decision.dry_run_executed is False
    assert decision.side_effects_performed is False
    assert decision.tool_called is False
    assert decision.provider_called is False
    assert decision.memory_mutated is False
    assert validate_execution_authorization_decision_inert(decision)


def test_execution_dry_run_trace_and_report_entry_are_review_only():
    intent, assessment, request, requirement, decision, dry_run_plan, trace = _authorization_parts()
    entry = create_execution_authorization_report_entry(
        trace=trace,
        intent=intent,
        assessment=assessment,
        requirement=requirement,
        decision=decision,
        unresolved_gaps=("action ledger missing",),
    )

    assert dry_run_plan.dry_run_enabled is False
    assert dry_run_plan.real_execution_enabled is False
    assert dry_run_plan.side_effects_enabled is False
    assert validate_execution_dry_run_plan_inert(dry_run_plan)
    assert validate_execution_trace_review_only(trace)
    assert validate_execution_report_entry_review_only(entry)


def test_execution_authorization_report_data_is_scaffold_only():
    data = build_execution_authorization_report_data()

    assert data["final_recommendation"] == "PROCEED_ACTION_LEDGER_DESIGN"
    assert data["status"] == "design_scaffold_only"
    assert data["decision"]["execution_authorized"] is False
    assert data["decision"]["action_executed"] is False
    assert data["dry_run_plan"]["real_execution_enabled"] is False
    assert data["invariant_flags"]["human_approval_required_for_risky_actions"] is True


def test_write_execution_authorization_report(tmp_path, monkeypatch):
    from orchestration.runtime import v14_execution_authorization_report as report_module

    md_path = tmp_path / "execution.md"
    json_path = tmp_path / "execution.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)

    data = write_execution_authorization_report()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))

    assert md_path.exists()
    assert parsed["final_recommendation"] == data["final_recommendation"]
