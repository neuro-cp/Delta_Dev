from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_selective_activation_plan import (
    RUNTIME_V15B_INVARIANT_FLAGS,
    create_selective_activation_audit,
    create_selective_activation_decision,
    create_selective_activation_plan,
    create_selective_activation_prerequisite,
    create_selective_activation_report_entry,
    create_selective_activation_risk_review,
    create_selective_activation_targets,
)


REPORT_MD = Path("reports/runtime_v15b_selective_live_activation_plan.md")
REPORT_JSON = Path("reports/runtime_v15b_selective_live_activation_plan.json")


def build_selective_activation_plan_report_data() -> dict[str, object]:
    targets = create_selective_activation_targets()
    selected = next(target for target in targets if target.selected_for_first_trial)
    prerequisites = tuple(create_selective_activation_prerequisite(target) for target in targets)
    risk_reviews = tuple(create_selective_activation_risk_review(target) for target in targets)
    plan = create_selective_activation_plan(selected)
    decision = create_selective_activation_decision(plan)
    audit = create_selective_activation_audit(plan, decision)
    entry = create_selective_activation_report_entry(plan, decision)
    return {
        "phase": "Runtime V1.5B",
        "title": "Selective Live-Activation Plan",
        "status": "activation-plan-only_no-activation_all-gates-closed",
        "final_recommendation": "PROCEED_SINGLE_GATE_DRY_RUN_TRIAL_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v15_selective_activation_plan.py",
            "orchestration/runtime/v15_selective_activation_plan_report.py",
            "tests/runtime_v15/test_v15_selective_activation_plan.py",
            "reports/runtime_v15b_selective_live_activation_plan.md",
            "reports/runtime_v15b_selective_live_activation_plan.json",
            "docs/runtime_v15b_selective_live_activation_plan_prompt.txt",
        ],
        "targets": [target.as_dict() for target in targets],
        "prerequisites": [item.as_dict() for item in prerequisites],
        "risk_reviews": [item.as_dict() for item in risk_reviews],
        "activation_plan": plan.as_dict(),
        "decision": decision.as_dict(),
        "audit": audit.as_dict(),
        "report_entry": entry.as_dict(),
        "invariant_flags": dict(RUNTIME_V15B_INVARIANT_FLAGS),
        "inactive_systems": ["provider calls", "memory/canonical/recall mutation", "HYB1 default activation", "action execution", "training", "schedulers"],
        "test_status": "run py_compile and tests/runtime_v14 tests/runtime_v15 to verify",
    }


def write_selective_activation_plan_report() -> dict[str, object]:
    data = build_selective_activation_plan_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.5B - Selective Live-Activation Plan",
        "",
        "Runtime V1.5B selects runtime_console_message_preview for a future first trial, but it is activation-plan-only. No gate opens and no activation is applied.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Targets",
        "",
    ]
    lines.extend(f"- `{target['target_type']}` selected={target['selected_for_first_trial']} active={target['active']} gate_open={target['gate_open']}" for target in data["targets"])
    lines.extend(["", "## Invariant Flags", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["invariant_flags"].items())
    lines.extend(["", "## Continuation Checkpoint", "", "V1.5B is activation-plan-only/no-activation. Proceed to single-gate dry-run trial design."])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_selective_activation_plan_report()
