from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_execution_authorization import (
    RUNTIME_V14O_INVARIANT_FLAGS,
    ActionIntentKind,
    RequestedExecutionMode,
    assess_execution_risk,
    create_action_intent,
    create_execution_approval_requirement,
    create_execution_authorization_report_entry,
    create_execution_authorization_request,
    create_execution_authorization_trace,
    create_execution_dry_run_plan,
    decide_execution_authorization,
)


REPORT_MD = Path("reports/runtime_v14o_execution_authorization_design.md")
REPORT_JSON = Path("reports/runtime_v14o_execution_authorization_design.json")


def build_execution_authorization_report_data() -> dict[str, object]:
    intent = create_action_intent(
        intent_kind=ActionIntentKind.CALL_TOOL,
        description="future runtime might ask to call a specialist or tool",
        target_reference="future-tool-placeholder",
        requested_mode=RequestedExecutionMode.REVIEW_ONLY,
        lane_scope=("execution", "safety"),
        source_trace_ids=("specialist-routing-trace-demo",),
    )
    assessment = assess_execution_risk(intent)
    request = create_execution_authorization_request(intent, assessment)
    requirement = create_execution_approval_requirement(request, assessment)
    decision = decide_execution_authorization(request, requirement)
    dry_run_plan = create_execution_dry_run_plan(
        intent,
        decision,
        planned_steps=(
            "record intended action",
            "assess risk",
            "require action ledger before any future execution",
        ),
    )
    trace = create_execution_authorization_trace(
        intent=intent,
        assessment=assessment,
        request=request,
        requirement=requirement,
        decision=decision,
        dry_run_plan=dry_run_plan,
    )
    entry = create_execution_authorization_report_entry(
        trace=trace,
        intent=intent,
        assessment=assessment,
        requirement=requirement,
        decision=decision,
        unresolved_gaps=(
            "action ledger is not implemented",
            "human approval surface is not implemented",
            "no execution engine exists",
        ),
    )
    return {
        "phase": "Runtime V1.4O",
        "title": "Execution Authorization Design Scaffold",
        "status": "design_scaffold_only",
        "final_recommendation": "PROCEED_ACTION_LEDGER_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "invariant_flags": dict(RUNTIME_V14O_INVARIANT_FLAGS),
        "intent": intent.as_dict(),
        "risk_assessment": assessment.as_dict(),
        "authorization_request": request.as_dict(),
        "approval_requirement": requirement.as_dict(),
        "decision": decision.as_dict(),
        "dry_run_plan": dry_run_plan.as_dict(),
        "trace": trace.as_dict(),
        "report_entry": entry.as_dict(),
        "safety_boundaries": [
            "execution authorization is not enabled",
            "actions are not executable",
            "dry-run execution is not enabled",
            "tool/provider/network/file/database side effects are not possible",
            "autonomous approval is not allowed",
            "future execution requires an action ledger first",
            "no memory, recall, training, scheduler, or runtime default changes are made",
        ],
        "inactive_systems": [
            "action execution",
            "dry-run execution",
            "tool calls",
            "provider calls",
            "side effects",
            "autonomous approval",
            "action ledger execution",
            "memory mutation",
            "runtime recall mutation",
            "training",
            "schedulers",
        ],
    }


def write_execution_authorization_report() -> dict[str, object]:
    data = build_execution_authorization_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4O - Execution Authorization Design Scaffold",
        "",
        "## Summary",
        "",
        "Runtime V1.4O defines the inert shape of future execution authorization. It does not authorize execution, run dry-runs, call tools, call providers, perform side effects, or approve actions autonomously.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(
        [
            "",
            "## Inactive Systems",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["inactive_systems"])
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Outcome: `{data['decision']['outcome']}`",
            f"- Rationale: {data['decision']['rationale']}",
            "",
            "## Continuation Checkpoint",
            "",
            "Runtime V1.4O is scaffold-only. Execution remains impossible; future action support must begin with an action ledger before any authorization or execution behavior is considered.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_execution_authorization_report()
