from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v18_review_ui_evidence_quality_iteration import write_quality_review_dashboard


REPORT_MD = Path("reports/runtime_v18d_local_review_ui_iteration_for_evidence_quality.md")
REPORT_JSON = Path("reports/runtime_v18d_local_review_ui_iteration_for_evidence_quality.json")


def write_quality_review_ui_report() -> dict[str, object]:
    data = write_quality_review_dashboard()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    entry = data["report_entry"]
    return "\n".join(
        [
            "# Runtime V1.8D - Local Review UI Iteration for Evidence Quality",
            "",
            f"- Dashboard: `{entry['output_path']}`",
            f"- Metrics: `{entry['metric_count']}`",
            f"- Blockers: `{entry['blocker_count']}`",
            f"- Safe: `{entry['safe']}`",
            "",
            "Static local dashboard only. No provider call, memory write, recall mutation, training, scheduler, HYB1 activation, or Model B change.",
            "",
            f"Final recommendation: `{data['final_recommendation']}`",
            "",
        ]
    )


if __name__ == "__main__":
    result = write_quality_review_ui_report()
    print(f"Runtime V1.8D quality UI: safe={result['report_entry']['safe']} final={result['final_recommendation']}")
