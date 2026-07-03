from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import (
    run_external_evaluator_api_trial,
    validate_external_evaluator_api_trial_safe,
)


REPORT_MD = Path("reports/runtime_v16c_daily_external_consolidation_evaluator_api_trial.md")
REPORT_JSON = Path("reports/runtime_v16c_daily_external_consolidation_evaluator_api_trial.json")


def write_external_evaluator_api_trial_report(*, live: bool = False) -> dict[str, object]:
    data = run_external_evaluator_api_trial(live=live)
    data["trial_safe"] = validate_external_evaluator_api_trial_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    result = data["trial_result"]
    lines = [
        "# Runtime V1.6C - Daily External Consolidation Evaluator API Trial",
        "",
        f"- Trial safe: `{data['trial_safe']}`",
        f"- Status: `{result['status']}`",
        f"- Provider: `{result['provider']}`",
        f"- Model: `{result['model']}`",
        f"- API key present: `{result['api_key_present']}`",
        f"- API key redacted: `{result['api_key_redacted']}`",
        f"- Live requested: `{result['live_requested']}`",
        f"- Live call attempted: `{result['live_call_attempted']}`",
        f"- Provider call performed: `{result['provider_call_performed']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Evaluator Output",
        "",
        "```text",
        str(result.get("evaluator_text") or result.get("error_summary") or data["advisory_review"]["rationale"]),
        "```",
        "",
        "## Safety",
        "",
        "- This is a manual one-shot evaluator trial only; dry-run is the default.",
        "- The evaluator result is not authoritative, not canonical memory, and not training data.",
        "- No scheduler, automatic daily run, memory mutation, canonical write, recall mutation, action execution, or HYB1 promotion occurred.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_external_evaluator_api_trial_report(live=False)
    result = report["trial_result"]
    print(
        "Runtime V1.6C evaluator API trial: "
        f"safe={report['trial_safe']} "
        f"status={result['status']} "
        f"provider_call_performed={result['provider_call_performed']} "
        f"final={report['final_recommendation']}"
    )
