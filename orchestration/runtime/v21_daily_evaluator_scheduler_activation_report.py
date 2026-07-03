from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v21_daily_evaluator_scheduler_activation import build_scheduler_activation_plan, validate_scheduler_activation_safe


REPORT_MD = Path("reports/runtime_v21d_daily_evaluator_scheduler_activation_user_approved.md")
REPORT_JSON = Path("reports/runtime_v21d_daily_evaluator_scheduler_activation_user_approved.json")


def write_scheduler_activation_report() -> dict[str, object]:
    payload = build_scheduler_activation_plan()
    payload["decision"] = {"permitted": False, "local_artifact_created": False, "os_task_registered": False, "background_worker_started": False}
    data = {**payload, "all_safe": validate_scheduler_activation_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.1D - Daily Evaluator Scheduler Activation, User-Approved",
        "",
        "Scheduler activation remains gated. This report creates no OS task, cron entry, background worker, or API call.",
        "",
        f"OS task registered: `{data['decision']['os_task_registered']}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_scheduler_activation_report()
    print(f"Runtime V2.1D scheduler activation: safe={result['all_safe']} final={result['final_recommendation']}")
