from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_daily_evaluator_manual_run_hardening import (
    build_manual_evaluator_run_request,
    run_hardened_manual_evaluator,
    validate_hardened_manual_evaluator_safe,
)


REPORT_MD = Path("reports/runtime_v16g_daily_evaluator_manual_run_hardening.md")
REPORT_JSON = Path("reports/runtime_v16g_daily_evaluator_manual_run_hardening.json")


def write_manual_run_hardening_report(*, run_id: str = "", live: bool = False, show_request: bool = True) -> dict[str, object]:
    request = build_manual_evaluator_run_request(run_id, live=live, show_request=show_request, output_report=True)
    data = run_hardened_manual_evaluator(request, persist_run_log=False)
    data["manual_run_safe"] = validate_hardened_manual_evaluator_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.6G - Daily Evaluator Manual-Run Hardening",
        "",
        f"- Manual run safe: `{data['manual_run_safe']}`",
        f"- Decision: `{data['decision']['decision']}`",
        f"- Provider call performed: `{data['trial']['trial_result']['provider_call_performed']}`",
        f"- Duplicate run ID: `{data['lock']['duplicate_run_id']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        "- Dry-run remains the default.",
        "- Live requires explicit CLI flag and env gates.",
        "- No scheduler, memory mutation, recall mutation, training, or action execution.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_manual_run_hardening_report()
    print(f"Runtime V1.6G manual evaluator hardening: safe={report['manual_run_safe']} decision={report['decision']['decision']} final={report['final_recommendation']}")
