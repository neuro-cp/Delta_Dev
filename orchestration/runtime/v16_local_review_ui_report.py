from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_local_review_ui import (
    DASHBOARD_HTML,
    build_local_review_dashboard_data,
    render_local_review_dashboard_html,
    validate_local_review_ui_safe,
    write_local_review_dashboard,
)


REPORT_MD = Path("reports/runtime_v16d_local_review_ui.md")
REPORT_JSON = Path("reports/runtime_v16d_local_review_ui.json")


def write_local_review_ui_report() -> dict[str, object]:
    data = write_local_review_dashboard(DASHBOARD_HTML)
    rendered = Path(data["dashboard_path"]).read_text(encoding="utf-8")
    data["ui_safe"] = validate_local_review_ui_safe(data, rendered)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.6D - Local Review UI",
        "",
        f"- UI safe: `{data['ui_safe']}`",
        f"- Dashboard path: `{data['dashboard_path']}`",
        f"- Review items: `{len(data['items'])}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        "- Static HTML only; no server, network calls, provider calls, action execution, training, memory writes, canonical writes, or recall mutation.",
        "- Approval text is displayed as structured text only and is not executed by the dashboard.",
        "- Evaluator output remains advisory only.",
        "- Model B remains default and HYB1 remains dormant/env-gated.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_local_review_ui_report()
    print(
        "Runtime V1.6D local review UI: "
        f"safe={report['ui_safe']} "
        f"items={len(report['items'])} "
        f"path={report['dashboard_path']} "
        f"final={report['final_recommendation']}"
    )
