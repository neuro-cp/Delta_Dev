from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_scheduler_activation_gate import (
    evaluate_scheduler_activation_gate,
    validate_scheduler_activation_gate_safe,
)


REPORT_MD = Path("reports/runtime_v16f_explicit_scheduler_activation_gate.md")
REPORT_JSON = Path("reports/runtime_v16f_explicit_scheduler_activation_gate.json")


def write_scheduler_activation_gate_report() -> dict[str, object]:
    data = evaluate_scheduler_activation_gate()
    data["gate_safe"] = validate_scheduler_activation_gate_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.6F - Explicit Scheduler Activation Gate",
        "",
        f"- Gate safe: `{data['gate_safe']}`",
        f"- Decision: `{data['decision']['decision']}`",
        f"- Scheduler started: `{data['decision']['scheduler_started']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        "- No scheduler, OS task, Windows scheduled task, cron entry, background worker, API call, memory write, recall mutation, training, or action execution.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_scheduler_activation_gate_report()
    print(f"Runtime V1.6F scheduler gate: safe={report['gate_safe']} decision={report['decision']['decision']} final={report['final_recommendation']}")
