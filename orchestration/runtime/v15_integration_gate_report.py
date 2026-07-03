from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_integration_gate import (
    RUNTIME_V15A_INVARIANT_FLAGS,
    IntegrationGateDecisionOutcome,
    IntegrationGateStatus,
    IntegrationPrerequisiteType,
    IntegrationRequestedMode,
    create_closed_integration_targets,
    create_integration_activation_request,
    create_integration_gate_audit_record,
    create_integration_gate_decision,
    create_integration_gate_report_entry,
    create_integration_prerequisite,
    create_integration_rollback_requirement,
    create_integration_safety_gate,
)


REPORT_MD = Path("reports/runtime_v15a_integration_gate_design.md")
REPORT_JSON = Path("reports/runtime_v15a_integration_gate_design.json")


def build_integration_gate_report_data() -> dict[str, object]:
    targets = create_closed_integration_targets()
    target = targets[0]
    prerequisite = create_integration_prerequisite(
        target=target,
        prerequisite_type=IntegrationPrerequisiteType.HUMAN_APPROVAL_REQUIRED,
        rationale="HYB1 cannot be activated without explicit human approval.",
        required_reference_id="runtime-v14v-promotion-rollback-report",
    )
    safety_gate = create_integration_safety_gate(
        target=target,
        invariant_requirements=("model_b_default_changed=false", "hyb1_default_activation_enabled=false"),
        unresolved_gaps=("human approval missing", "future trial design missing"),
        blocked_capabilities=("default_change", "runtime_activation"),
        gate_status=IntegrationGateStatus.CLOSED_BY_DEFAULT,
    )
    request = create_integration_activation_request(
        target=target,
        requested_mode=IntegrationRequestedMode.FUTURE_TRIAL_DESIGN,
        requester_summary="operator review placeholder",
        justification="future trial design only",
    )
    decision = create_integration_gate_decision(
        target=target,
        request=request,
        outcome=IntegrationGateDecisionOutcome.KEEP_CLOSED,
        rationale="all V1.5A gates remain closed by default",
    )
    rollback = create_integration_rollback_requirement(target=target, rollback_strategy="restore Model B default before any future trial")
    audit = create_integration_gate_audit_record(
        target=target,
        prerequisite_ids=(prerequisite.prerequisite_id,),
        audit_summary="integration gate design only; no gate opened",
        decision=decision,
        safety_gate=safety_gate,
    )
    entry = create_integration_gate_report_entry(
        target=target,
        prerequisite_summary="unsatisfied by default",
        safety_summary="closed by default",
        activation_request_summary="dry-run future trial design request only",
        decision_summary=decision.outcome.value,
        rollback_summary="rollback required before activation; not ready or executed",
        unresolved_gaps=("human approval", "rollback validation", "selective trial design"),
        recommended_next_review_step="V1.5B selective live activation plan, still off by default",
    )
    return {
        "phase": "Runtime V1.5A",
        "title": "Integration Gate Design",
        "status": "integration-gate-design-only_all-gates-closed_no-activation",
        "final_recommendation": "PROCEED_V15B_SELECTIVE_LIVE_ACTIVATION_PLAN_STILL_OFF_BY_DEFAULT",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v15_integration_gate.py",
            "orchestration/runtime/v15_integration_gate_report.py",
            "tests/runtime_v15/test_v15_integration_gate_design.py",
            "reports/runtime_v15a_integration_gate_design.md",
            "reports/runtime_v15a_integration_gate_design.json",
            "docs/runtime_v15a_integration_gate_prompt.txt",
        ],
        "target_capabilities": [item.as_dict() for item in targets],
        "prerequisite": prerequisite.as_dict(),
        "safety_gate": safety_gate.as_dict(),
        "activation_request": request.as_dict(),
        "decision": decision.as_dict(),
        "rollback_requirement": rollback.as_dict(),
        "audit": audit.as_dict(),
        "report_entry": entry.as_dict(),
        "invariant_flags": dict(RUNTIME_V15A_INVARIANT_FLAGS),
        "inactive_systems": [
            "integration gates",
            "HYB1 default activation",
            "recall bridge",
            "canonical memory",
            "training/export",
            "provider/tool calls",
            "specialist routing",
            "action/dry-run execution",
            "memory/canonical/recall mutation",
            "schedulers/workers/queues",
        ],
        "test_status": "run py_compile and tests/runtime_v14 tests/runtime_v15 to verify",
    }


def write_integration_gate_report() -> dict[str, object]:
    data = build_integration_gate_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.5A - Integration Gate Design",
        "",
        "Runtime V1.5A defines closed integration gates for dormant V1.4 capabilities. It does not activate integration, open gates, change defaults, train, call providers/tools, execute actions, write memory, mutate recall, or create schedulers.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Target Capabilities",
        "",
    ]
    for target in data["target_capabilities"]:
        lines.append(f"- `{target['target_type']}` from {target['source_phase']}: gate_open={target['gate_open']}, active={target['active']}")
    lines.extend(["", "## Invariant Flags", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["invariant_flags"].items())
    lines.extend(["", "## Continuation Checkpoint", ""])
    lines.append("Runtime V1.5A is integration-gate-design-only. Every gate remains closed by default and no live integration path was added.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_integration_gate_report()
