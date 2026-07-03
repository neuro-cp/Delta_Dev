from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v20_scheduler_activation_trial_design import design_scheduler_activation_trial, validate_scheduler_activation_trial_design_safe


REPORT_MD = Path("reports/runtime_v20g_scheduler_activation_trial_design_only.md")
REPORT_JSON = Path("reports/runtime_v20g_scheduler_activation_trial_design_only.json")


def write_scheduler_activation_trial_design_report() -> dict[str, object]:
    payload = design_scheduler_activation_trial()
    data = {**payload, "all_safe": validate_scheduler_activation_trial_design_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.0G - Scheduler Activation Trial Design Only",
        "",
        "This is a text-only scheduler activation design. It creates no OS task, cron entry, background worker, timer, or queue.",
        "",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_scheduler_activation_trial_design_report()
    print(f"Runtime V2.0G scheduler design: safe={result['all_safe']} final={result['final_recommendation']}")
