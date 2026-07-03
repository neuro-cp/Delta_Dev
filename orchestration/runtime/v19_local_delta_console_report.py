from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v19_local_delta_console import run_delta_console_command, validate_local_delta_console_safe


REPORT_MD = Path("reports/runtime_v19b_ux_first_local_delta_console.md")
REPORT_JSON = Path("reports/runtime_v19b_ux_first_local_delta_console.json")


def write_local_delta_console_report() -> dict[str, object]:
    cases = [
        run_delta_console_command("status"),
        run_delta_console_command("ask", "What is HYB1?"),
        run_delta_console_command("recall", "What does DELTA know about HYB1?"),
        run_delta_console_command("synthesize", "What does DELTA know about memory writes?"),
        run_delta_console_command("provider-dry-run", "What is a recent fact DELTA cannot know locally?"),
    ]
    data = {"phase": "Runtime V1.9B", "cases": cases, "all_safe": all(validate_local_delta_console_safe(case) for case in cases), "final_recommendation": "PROCEED_CONSOLE_APPROVAL_REJECT_DEFER_WORKFLOW"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = ["# Runtime V1.9B - UX-first Local DELTA Console", "", f"- Cases: `{len(data['cases'])}`", f"- All safe: `{data['all_safe']}`", "", "Command-mode local console only. No live provider call, memory write, recall mutation, training, action execution, scheduler, HYB1 activation, or Model B change.", "", "## Commands Exercised", ""]
    for case in data["cases"]:
        lines.append(f"- `{case['command']['command']}`")
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_local_delta_console_report()
    print(f"Runtime V1.9B console: safe={result['all_safe']} final={result['final_recommendation']}")
