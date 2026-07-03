from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_external_consolidation_evaluator_api_design import (
    build_external_consolidation_evaluator_api_design_payload,
    validate_external_evaluator_api_design_safe,
)


REPORT_MD = Path("reports/runtime_v16b_daily_external_consolidation_evaluator_api_design.md")
REPORT_JSON = Path("reports/runtime_v16b_daily_external_consolidation_evaluator_api_design.json")


def write_external_evaluator_api_design_report() -> dict[str, object]:
    data = build_external_consolidation_evaluator_api_design_payload()
    data["design_safe"] = validate_external_evaluator_api_design_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    request = data["request"]
    env = data["env"]
    lines = [
        "# Runtime V1.6B - Daily External Consolidation Evaluator API Design",
        "",
        f"- Design safe: `{data['design_safe']}`",
        f"- Provider: `{request['provider']}`",
        f"- Model: `{request['model']}`",
        f"- Env live call permitted: `{env['live_call_permitted']}`",
        f"- Live call allowed in V1.6B: `{request['live_call_allowed']}`",
        f"- Provider calls performed: `{data['design_review']['provider_calls_performed']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        "- V1.6B is API design only.",
        "- No provider call is performed even if `.env.local` permits one.",
        "- Evaluator review is not authority, not canonical memory, and not training data.",
        "- No scheduler, background worker, daily automatic run, memory mutation, or canonical write is enabled.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_external_evaluator_api_design_report()
    print(
        "Runtime V1.6B evaluator API design: "
        f"safe={report['design_safe']} "
        f"live_allowed={report['request']['live_call_allowed']} "
        f"final={report['final_recommendation']}"
    )
