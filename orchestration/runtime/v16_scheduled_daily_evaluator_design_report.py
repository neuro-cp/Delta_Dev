from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_scheduled_daily_evaluator_design import (
    RUNTIME_V16E_SCHEDULED_EVALUATOR_FLAGS,
    build_scheduled_daily_evaluator_plan,
    validate_scheduled_daily_evaluator_plan_safe,
)


REPORT_MD = Path("reports/runtime_v16e_scheduled_daily_evaluator_design.md")
REPORT_JSON = Path("reports/runtime_v16e_scheduled_daily_evaluator_design.json")


def write_scheduled_daily_evaluator_design_report() -> dict[str, object]:
    plan = build_scheduled_daily_evaluator_plan()
    data = {
        "phase": "Runtime V1.6E",
        "title": "Scheduled Daily Evaluator Design",
        "status": "schedule_design_only_no_scheduler",
        "plan": plan.as_dict(),
        "plan_safe": validate_scheduled_daily_evaluator_plan_safe(plan),
        "invariant_flags": dict(RUNTIME_V16E_SCHEDULED_EVALUATOR_FLAGS),
        "final_recommendation": "PROCEED_EXPLICIT_SCHEDULER_ACTIVATION_OR_LOCAL_REVIEW_UI_ITERATION",
    }
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.6E - Scheduled Daily Evaluator Design",
        "",
        f"- Status: `{data['status']}`",
        f"- Plan safe: `{data['plan_safe']}`",
        f"- Decision: `{data['plan']['decision']['decision']}`",
        f"- Manual run command: `{data['plan']['manual_run_command']['command_text']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        "- No scheduler, Windows scheduled task, cron entry, background worker, timer, queue, or lockfile is created.",
        "- No evaluator API call is made during schedule design.",
        "- No memory write, canonical write, recall mutation, action execution, training, or HYB1 promotion occurs.",
        "- Manual run command is text only.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_scheduled_daily_evaluator_design_report()
    print(
        "Runtime V1.6E scheduled evaluator design: "
        f"safe={report['plan_safe']} "
        f"decision={report['plan']['decision']['decision']} "
        f"final={report['final_recommendation']}"
    )
