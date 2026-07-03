from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_review_ui_export_flow import build_review_ui_exports, validate_review_ui_export_safe


REPORT_MD = Path("reports/runtime_v16h_review_ui_approval_rejection_export_flow.md")
REPORT_JSON = Path("reports/runtime_v16h_review_ui_approval_rejection_export_flow.json")


def write_review_ui_export_flow_report(candidate_id: str = "memory-candidate-60ee56fb323e53de") -> dict[str, object]:
    data = build_review_ui_exports(candidate_id)
    data["export_safe"] = validate_review_ui_export_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.6H - Review UI Approval / Rejection Export Flow",
        "",
        f"- Export safe: `{data['export_safe']}`",
        f"- Candidate ID: `{candidate_id}`",
        f"- Export count: `{len(data['exports'])}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        "- Exports are text only and are not executed.",
        "- No memory write, recall mutation, provider call, training, action execution, HYB1 promotion, or Model B change.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_review_ui_export_flow_report()
    print(f"Runtime V1.6H review UI exports: safe={report['export_safe']} exports={len(report['exports'])} final={report['final_recommendation']}")
