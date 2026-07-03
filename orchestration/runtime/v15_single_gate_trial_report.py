from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_single_gate_trial import (
    RUNTIME_V15C_INVARIANT_FLAGS,
    create_single_gate_expected_trace,
    create_single_gate_safety_boundary,
    create_single_gate_trial_audit,
    create_single_gate_trial_decision,
    create_single_gate_trial_input_case,
    create_single_gate_trial_report_entry,
    create_single_gate_trial_scope,
    create_single_gate_trial_target,
)


REPORT_MD = Path("reports/runtime_v15c_single_gate_dry_run_trial_design.md")
REPORT_JSON = Path("reports/runtime_v15c_single_gate_dry_run_trial_design.json")


def build_single_gate_trial_report_data() -> dict[str, object]:
    target = create_single_gate_trial_target("runtime-v15b-selective-plan")
    scope = create_single_gate_trial_scope(target)
    case = create_single_gate_trial_input_case(target)
    expected_trace = create_single_gate_expected_trace(case)
    boundary = create_single_gate_safety_boundary(target)
    decision = create_single_gate_trial_decision(target)
    audit = create_single_gate_trial_audit(target, decision)
    entry = create_single_gate_trial_report_entry(target, scope, decision)
    return {
        "phase": "Runtime V1.5C",
        "title": "Single-Gate Dry-Run Trial Design",
        "status": "single-gate-design-only_no-gate-opened_no-trial-executed",
        "final_recommendation": "PROCEED_FIRST_LIVE_INTERACTION_PATH_CONSOLE_ONLY",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v15_single_gate_trial.py",
            "orchestration/runtime/v15_single_gate_trial_report.py",
            "tests/runtime_v15/test_v15_single_gate_trial_design.py",
            "reports/runtime_v15c_single_gate_dry_run_trial_design.md",
            "reports/runtime_v15c_single_gate_dry_run_trial_design.json",
            "docs/runtime_v15c_single_gate_dry_run_trial_prompt.txt",
        ],
        "target": target.as_dict(),
        "scope": scope.as_dict(),
        "input_case": case.as_dict(),
        "expected_trace": expected_trace.as_dict(),
        "safety_boundary": boundary.as_dict(),
        "decision": decision.as_dict(),
        "audit": audit.as_dict(),
        "report_entry": entry.as_dict(),
        "invariant_flags": dict(RUNTIME_V15C_INVARIANT_FLAGS),
        "test_status": "run py_compile and tests/runtime_v14 tests/runtime_v15 to verify",
    }


def write_single_gate_trial_report() -> dict[str, object]:
    data = build_single_gate_trial_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    return (
        "# Runtime V1.5C - Single-Gate Dry-Run Trial Design\n\n"
        "Single-gate-design-only. The runtime console message preview gate is not opened and no trial is executed.\n\n"
        f"- Status: `{data['status']}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n"
        f"- Starter case: `{data['input_case']['message']}`\n\n"
        "Provider calls, memory writes, canonical writes, recall mutation, HYB1 default activation, action execution, training, and schedulers remain disabled.\n"
    )


if __name__ == "__main__":
    write_single_gate_trial_report()
