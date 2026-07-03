from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v18_evidence_quality_evaluation import run_evidence_quality_evaluation, validate_evidence_quality_evaluation_safe


REPORT_MD = Path("reports/runtime_v18a_evidence_quality_evaluation_harness.md")
REPORT_JSON = Path("reports/runtime_v18a_evidence_quality_evaluation_harness.json")


def write_evidence_quality_evaluation_report() -> dict[str, object]:
    data = run_evidence_quality_evaluation()
    data["all_safe"] = validate_evidence_quality_evaluation_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    entry = data["report_entry"]
    lines = [
        "# Runtime V1.8A - Evidence Quality Evaluation Harness",
        "",
        f"- Cases: `{entry['case_count']}`",
        f"- Average score: `{entry['average_score']}`",
        f"- Safe: `{entry['safe']}`",
        f"- All safe: `{data['all_safe']}`",
        "",
        "The harness evaluates provenance, uncertainty, source role correctness, candidate/truth distinction, conflict handling, unsupported fallback behavior, and mutation safety. It does not promote anything.",
        "",
        "## Scorecards",
        "",
    ]
    for scorecard in data["evaluation_run"]["scorecards"]:
        lines.append(f"- `{scorecard['case_id']}` -> `{scorecard['score']}`")
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_evidence_quality_evaluation_report()
    print(f"Runtime V1.8A evidence quality: avg={result['report_entry']['average_score']} final={result['final_recommendation']}")
