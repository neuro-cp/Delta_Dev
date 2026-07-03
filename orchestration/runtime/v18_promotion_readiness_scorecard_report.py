from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v18_promotion_readiness_scorecard import run_promotion_readiness_scorecard, validate_promotion_readiness_scorecard_safe


REPORT_MD = Path("reports/runtime_v18b_promotion_readiness_scorecard.md")
REPORT_JSON = Path("reports/runtime_v18b_promotion_readiness_scorecard.json")


def write_promotion_readiness_scorecard_report() -> dict[str, object]:
    data = run_promotion_readiness_scorecard()
    data["all_safe"] = validate_promotion_readiness_scorecard_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    entry = data["report_entry"]
    lines = [
        "# Runtime V1.8B - Promotion Readiness Scorecard",
        "",
        f"- Ready for human review: `{entry['ready_for_human_review_count']}`",
        f"- Blocked: `{entry['blocked_count']}`",
        f"- Design-only: `{entry['design_only_count']}`",
        f"- Promotions performed: `{data['audit_record']['promotions_performed']}`",
        f"- All safe: `{data['all_safe']}`",
        "",
        "This scorecard does not promote anything. It only reports whether future capability gates might be eligible for human review.",
        "",
        "## Targets",
        "",
    ]
    for card in data["scorecards"]:
        lines.append(f"- `{card['target']['name']}` -> `{card['decision']['outcome']}`")
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_promotion_readiness_scorecard_report()
    print(f"Runtime V1.8B readiness: ready={result['report_entry']['ready_for_human_review_count']} final={result['final_recommendation']}")
