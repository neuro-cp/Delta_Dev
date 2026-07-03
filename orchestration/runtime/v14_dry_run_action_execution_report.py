from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_action_ledger import ActionLedgerStatus, create_action_ledger_entry
from orchestration.runtime.v14_dry_run_action_execution import (
    RUNTIME_V14Q_INVARIANT_FLAGS,
    DryRunActionKind,
    DryRunRequestedMode,
    DryRunSideEffectRisk,
    create_dry_run_action,
    create_dry_run_execution_input,
    create_dry_run_execution_report_entry,
    create_dry_run_execution_result,
    create_dry_run_execution_step,
    create_dry_run_execution_trace,
    create_dry_run_rollback_plan,
    create_execution_side_effect_boundary,
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


REPORT_MD = Path("reports/runtime_v14q_dry_run_action_execution_design.md")
REPORT_JSON = Path("reports/runtime_v14q_dry_run_action_execution_design.json")


def build_dry_run_action_execution_report_data() -> dict[str, object]:
    intent = create_action_intent(
        intent_kind=ActionIntentKind.FILE_OPERATION,
        description="future runtime might write a report",
        target_reference="reports/future.md",
        requested_mode=RequestedExecutionMode.REVIEW_ONLY,
        source_trace_ids=("action-ledger-trace-demo",),
    )
    risk = assess_execution_risk(intent)
    auth_request = create_execution_authorization_request(intent, risk)
    approval = create_execution_approval_requirement(auth_request, risk)
    auth_decision = decide_execution_authorization(auth_request, approval)
    dry_run_plan = create_execution_dry_run_plan(intent, auth_decision, planned_steps=("simulate report write",))
    ledger_entry = create_action_ledger_entry(
        action_intent_id=intent.intent_id,
        authorization_decision_id=auth_decision.decision_id,
        risk_assessment_id=risk.assessment_id,
        dry_run_plan_id=dry_run_plan.dry_run_plan_id,
        source_reference_ids=intent.source_trace_ids,
        ledger_status=ActionLedgerStatus.BLOCKED_MISSING_APPROVAL,
        action_summary="future report write remains blocked",
    )
    action = create_dry_run_action(
        action_intent_id=intent.intent_id,
        action_kind=DryRunActionKind.FILE_OPERATION,
        action_summary="simulate future report write without touching the filesystem",
        source_reference_ids=intent.source_trace_ids,
        ledger_entry_id=ledger_entry.ledger_entry_id,
        authorization_decision_id=auth_decision.decision_id,
    )
    execution_input = create_dry_run_execution_input(
        action,
        requested_mode=DryRunRequestedMode.SIMULATE_STEPS,
        preconditions=("authorization reviewed", "ledger entry drafted"),
    )
    steps = (
        create_dry_run_execution_step(
            execution_input,
            step_order=1,
            step_summary="would validate authorization and ledger references",
            side_effect_risk=DryRunSideEffectRisk.LOW,
        ),
        create_dry_run_execution_step(
            execution_input,
            step_order=2,
            step_summary="would describe filesystem write without performing it",
            would_touch_target=intent.target_reference,
            side_effect_risk=DryRunSideEffectRisk.HIGH,
        ),
    )
    result = create_dry_run_execution_result(execution_input, steps)
    boundary = create_execution_side_effect_boundary(action)
    trace = create_dry_run_execution_trace(
        action=action,
        execution_input=execution_input,
        steps=steps,
        result=result,
        boundary=boundary,
    )
    rollback_plan = create_dry_run_rollback_plan(
        action,
        result_id=result.result_id,
        rollback_strategy="rollback remains hypothetical because no file was written",
    )
    report_entry = create_dry_run_execution_report_entry(
        action=action,
        execution_input=execution_input,
        steps=steps,
        result=result,
        boundary=boundary,
        trace=trace,
        rollback_plan=rollback_plan,
        unresolved_gaps=(
            "minimal runtime UI/message console is not implemented",
            "real action execution remains forbidden",
            "active ledger persistence remains disabled",
        ),
    )
    return {
        "phase": "Runtime V1.4Q",
        "title": "Dry-Run Action Execution Design",
        "status": "dry_run_design_only_no_real_execution_no_side_effects",
        "final_recommendation": "PROCEED_MINIMAL_RUNTIME_UI_MESSAGE_CONSOLE",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v14_dry_run_action_execution.py",
            "orchestration/runtime/v14_dry_run_action_execution_report.py",
            "tests/runtime_v14/test_v14_dry_run_action_execution_design.py",
            "reports/runtime_v14q_dry_run_action_execution_design.md",
            "reports/runtime_v14q_dry_run_action_execution_design.json",
            "docs/runtime_v14q_dry_run_action_execution_prompt.txt",
        ],
        "invariant_flags": dict(RUNTIME_V14Q_INVARIANT_FLAGS),
        "pipeline_summary": (
            "ActionIntent -> ActionLedgerEntry -> DryRunAction -> DryRunExecutionInput -> "
            "DryRunExecutionStep -> DryRunExecutionResult -> ExecutionSideEffectBoundary -> DryRunExecutionTrace"
        ),
        "dry_run_action": action.as_dict(),
        "execution_input": execution_input.as_dict(),
        "execution_steps": [step.as_dict() for step in steps],
        "execution_result": result.as_dict(),
        "side_effect_boundary": boundary.as_dict(),
        "execution_trace": trace.as_dict(),
        "rollback_plan": rollback_plan.as_dict(),
        "report_entry": report_entry.as_dict(),
        "safety_boundaries": [
            "dry-run execution is not action execution",
            "simulated result is not a side effect",
            "execution trace is not external mutation",
            "rollback plan is not applied rollback",
            "side-effect boundary is not a side effect",
            "ledger reference is not active ledger write",
            "dry-run eligibility is not execution permission",
        ],
        "inactive_systems": [
            "real action execution",
            "tool calls",
            "provider calls",
            "file mutation",
            "network calls",
            "database mutation",
            "external side effects",
            "active ledger persistence",
            "autonomous approval",
            "rollback execution",
            "memory mutation",
            "runtime recall mutation",
            "training",
            "schedulers/background workers/timers/queues",
        ],
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_dry_run_action_execution_report() -> dict[str, object]:
    data = build_dry_run_action_execution_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4Q - Dry-Run Action Execution Design",
        "",
        "## Summary",
        "",
        "Runtime V1.4Q defines an inert, deterministic dry-run action execution scaffold that simulates execution shape without real execution or side effects.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Design Summary",
        "",
        f"- Pipeline: {data['pipeline_summary']}",
        "- DryRunAction is inactive.",
        "- DryRunExecutionInput is simulation-only.",
        "- DryRunExecutionResult is simulated and not real.",
        "- DryRunExecutionTrace is review-only and not persisted to an active ledger.",
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(["", "## Inactive Systems", ""])
    lines.extend(f"- {item}" for item in data["inactive_systems"])
    lines.extend(["", "## Invariant Flags", ""])
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
            "Runtime V1.4Q is dry-run-design-only. It does not add real execution, tool/provider calls, file/network/database side effects, active ledger persistence, autonomous approval, rollback execution, memory mutation, recall mutation, training, schedulers, queues, timers, or runtime behavior changes.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_dry_run_action_execution_report()
