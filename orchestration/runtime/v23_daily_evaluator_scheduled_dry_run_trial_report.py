from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v23_daily_evaluator_scheduled_dry_run_trial import APPROVAL_TEXT, run_scheduled_dry_run_trial, validate_scheduled_dry_run_safe


REPORT_MD = Path("reports/runtime_v23e_daily_evaluator_scheduled_dry_run_trial.md")
REPORT_JSON = Path("reports/runtime_v23e_daily_evaluator_scheduled_dry_run_trial.json")


def write_scheduled_dry_run_report() -> dict[str, object]:
    cases = [run_scheduled_dry_run_trial(), run_scheduled_dry_run_trial(approval_text=APPROVAL_TEXT, env={"DELTA_DAILY_EVALUATOR_SCHEDULE_DRY_RUN_ENABLED": "true"})]
    data = {"phase": "Runtime V2.3E", "cases": cases, "all_safe": all(validate_scheduled_dry_run_safe(case) for case in cases), "final_recommendation": "PROCEED_V23_SAFETY_CHECKPOINT"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.3E - Daily Evaluator Scheduled Dry-Run Trial", "", "The scheduler trial creates dry-run schedule artifacts only and registers no OS task, cron entry, or worker.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_scheduled_dry_run_report()
    print(f"Runtime V2.3E scheduler dry-run: safe={result['all_safe']} final={result['final_recommendation']}")

