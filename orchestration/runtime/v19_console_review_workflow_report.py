from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v19_console_review_workflow import export_console_review_action, validate_console_review_workflow_safe


REPORT_MD = Path("reports/runtime_v19c_console_approval_reject_defer_workflow.md")
REPORT_JSON = Path("reports/runtime_v19c_console_approval_reject_defer_workflow.json")


def write_console_review_workflow_report() -> dict[str, object]:
    cases = [export_console_review_action(action, "memory-candidate-demo") for action in ("approve", "reject", "defer")]
    data = {"phase": "Runtime V1.9C", "cases": cases, "all_safe": all(validate_console_review_workflow_safe(case) for case in cases), "final_recommendation": "PROCEED_SESSION_TO_CANDIDATE_MEMORY_PROPOSAL_FLOW"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = ["# Runtime V1.9C - Console Approval / Reject / Defer Workflow", "", f"- Cases: `{len(data['cases'])}`", f"- All safe: `{data['all_safe']}`", "", "Exports exact review strings only. No memory write, recall mutation, provider call, training, HYB1 activation, or Model B change.", ""]
    for case in data["cases"]:
        lines.append(f"## {case['result']['action']}")
        lines.append("```text")
        lines.append(case["result"]["export_text"])
        lines.append("```")
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_console_review_workflow_report()
    print(f"Runtime V1.9C console review: safe={result['all_safe']} final={result['final_recommendation']}")
