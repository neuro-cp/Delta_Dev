from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_action_ledger import (
    RUNTIME_V14P_INVARIANT_FLAGS,
    ActionLedgerStatus,
    create_action_audit_trace,
    create_action_ledger_entry,
    create_action_ledger_plan,
    create_action_ledger_report_entry,
    create_action_rollback_reference,
    decide_action_ledger,
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


REPORT_MD = Path("reports/runtime_v14p_action_ledger_design.md")
REPORT_JSON = Path("reports/runtime_v14p_action_ledger_design.json")


def build_action_ledger_report_data() -> dict[str, object]:
    intent = create_action_intent(
        intent_kind=ActionIntentKind.CALL_TOOL,
        description="future runtime might request a tool call",
        target_reference="future-tool-placeholder",
        requested_mode=RequestedExecutionMode.REVIEW_ONLY,
        lane_scope=("execution", "audit"),
        source_trace_ids=("execution-auth-trace-demo",),
    )
    risk = assess_execution_risk(intent)
    auth_request = create_execution_authorization_request(intent, risk)
    approval = create_execution_approval_requirement(auth_request, risk)
    auth_decision = decide_execution_authorization(auth_request, approval)
    dry_run = create_execution_dry_run_plan(intent, auth_decision, planned_steps=("record only", "do not execute"))
    ledger_entry = create_action_ledger_entry(
        action_intent_id=intent.intent_id,
        authorization_decision_id=auth_decision.decision_id,
        risk_assessment_id=risk.assessment_id,
        dry_run_plan_id=dry_run.dry_run_plan_id,
        source_reference_ids=intent.source_trace_ids,
        ledger_status=ActionLedgerStatus.BLOCKED_MISSING_APPROVAL,
        action_summary="future tool call requires ledgering before any execution path",
    )
    plan = create_action_ledger_plan((ledger_entry,))
    audit_trace = create_action_audit_trace(
        ledger_entry,
        authorization_reference_ids=(auth_decision.decision_id,),
        risk_reference_ids=(risk.assessment_id,),
        decision_reference_ids=(auth_decision.decision_id,),
        trace_summary="audit trace is generated for review only and is not persisted",
    )
    rollback_reference = create_action_rollback_reference(
        ledger_entry,
        rollback_possible=False,
        rollback_strategy="no rollback can execute because no action can execute",
        rollback_target_reference=intent.target_reference,
    )
    ledger_decision = decide_action_ledger(ledger_entry)
    report_entry = create_action_ledger_report_entry(
        entry=ledger_entry,
        audit_trace=audit_trace,
        rollback_reference=rollback_reference,
        decision=ledger_decision,
        unresolved_gaps=(
            "active ledger persistence is not implemented",
            "dry-run execution is not implemented",
            "human approval workflow is not implemented",
        ),
    )
    return {
        "phase": "Runtime V1.4P",
        "title": "Action Ledger Design",
        "status": "ledger_design_only_no_execution_no_side_effects",
        "final_recommendation": "PROCEED_DRY_RUN_ACTION_EXECUTION_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v14_action_ledger.py",
            "orchestration/runtime/v14_action_ledger_report.py",
            "tests/runtime_v14/test_v14_action_ledger_design.py",
            "reports/runtime_v14p_action_ledger_design.md",
            "reports/runtime_v14p_action_ledger_design.json",
            "docs/runtime_v14p_action_ledger_prompt.txt",
        ],
        "invariant_flags": dict(RUNTIME_V14P_INVARIANT_FLAGS),
        "pipeline_summary": (
            "ActionIntent -> ExecutionRiskAssessment -> ExecutionAuthorizationDecision -> "
            "ActionLedgerEntry -> ActionAuditTrace -> ActionRollbackReference -> ActionLedgerDecision"
        ),
        "ledger_entry": ledger_entry.as_dict(),
        "ledger_plan": plan.as_dict(),
        "audit_trace": audit_trace.as_dict(),
        "rollback_reference": rollback_reference.as_dict(),
        "ledger_decision": ledger_decision.as_dict(),
        "report_entry": report_entry.as_dict(),
        "safety_boundaries": [
            "ledger design is not action execution",
            "audit entry is not a side effect",
            "rollback reference is not rollback execution",
            "record shape is not active tool control",
            "append-only plan is not active persistence",
            "ledger eligibility is not execution permission",
        ],
        "inactive_systems": [
            "active ledger persistence",
            "action execution",
            "dry-run execution",
            "tool calls",
            "provider calls",
            "file/network/database side effects",
            "autonomous approval",
            "rollback execution",
            "memory mutation",
            "runtime recall mutation",
            "training",
            "schedulers/background workers/timers/queues",
        ],
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_action_ledger_report() -> dict[str, object]:
    data = build_action_ledger_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4P - Action Ledger Design",
        "",
        "## Summary",
        "",
        "Runtime V1.4P defines an inert, deterministic action ledger scaffold required before any future dry-run or real action execution can exist.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Design Summary",
        "",
        f"- Pipeline: {data['pipeline_summary']}",
        "- The ledger entry is inactive and is not persisted to an active ledger.",
        "- The audit trace is review-only.",
        "- The rollback reference does not execute rollback.",
        "- The decision is not applied and writes no ledger.",
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(["", "## Inactive Systems", ""])
    lines.extend(f"- {item}" for item in data["inactive_systems"])
    lines.extend(
        [
            "",
            "## Invariant Flags",
            "",
        ]
    )
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["invariant_flags"].items())
    lines.extend(
        [
            "",
            "## Test Status",
            "",
            str(data["test_status"]),
            "",
            "## Continuation Checkpoint",
            "",
            "Runtime V1.4P is ledger-design-only. It does not add active ledger persistence, action execution, tool/provider calls, side effects, autonomous approval, rollback execution, memory mutation, recall mutation, training, schedulers, queues, timers, or runtime behavior changes.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_action_ledger_report()
