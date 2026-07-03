from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v20_review_ui_write_approval_bridge import generate_review_ui_write_approval_bridge, validate_review_ui_bridge_safe


REPORT_MD = Path("reports/runtime_v20d_review_ui_write_approval_bridge.md")
REPORT_JSON = Path("reports/runtime_v20d_review_ui_write_approval_bridge.json")


def write_review_ui_write_approval_bridge_report() -> dict[str, object]:
    payload = generate_review_ui_write_approval_bridge()
    data = {
        **payload,
        "all_safe": validate_review_ui_bridge_safe(payload),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.0D - Review UI Write Approval Bridge",
        "",
        "Static local review UI bridge generated exact approve/reject/defer export text. UI generation does not write memory.",
        "",
        f"UI path: `{data['ui_path']}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_review_ui_write_approval_bridge_report()
    print(f"Runtime V2.0D review UI bridge: safe={result['all_safe']} final={result['final_recommendation']}")
