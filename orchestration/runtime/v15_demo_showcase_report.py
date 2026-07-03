from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_demo_showcase import (
    build_runtime_demo_showcase,
    format_runtime_demo_showcase,
    validate_runtime_demo_showcase_safe,
)
from orchestration.runtime.v15_explicit_canonical_memory_write_trial import DEFAULT_TRIAL_STORE


REPORT_MD = Path("reports/runtime_v15k_demo_script_showcase.md")
REPORT_JSON = Path("reports/runtime_v15k_demo_script_showcase.json")


def write_runtime_demo_showcase_report(store_path: str | Path = DEFAULT_TRIAL_STORE) -> dict[str, object]:
    data = build_runtime_demo_showcase(store_path)
    data["showcase_safe"] = validate_runtime_demo_showcase_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.5K - Demo Script / Showcase Report",
        "",
        f"- Status: `{data['status']}`",
        f"- All steps safe: `{data['all_steps_safe']}`",
        f"- Showcase safe: `{data['showcase_safe']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Demo Output",
        "",
        "```text",
        format_runtime_demo_showcase(data),
        "```",
        "",
        "## Safety",
        "",
        "- Demonstrates local answer routing, memory-candidate preview, and limited recall candidate context.",
        "- Does not perform provider calls, tool calls, action execution, memory writes, canonical writes, recall mutation, or training.",
        "- HYB1 remains dormant/env-gated and Model B remains default.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_runtime_demo_showcase_report()
    print(
        "Runtime V1.5K demo showcase: "
        f"safe={report['showcase_safe']} "
        f"steps={len(report['showcase_steps'])} "
        f"final={report['final_recommendation']}"
    )
