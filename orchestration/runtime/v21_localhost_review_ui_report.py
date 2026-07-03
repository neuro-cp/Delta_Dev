from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v21_localhost_review_ui import render_static_localhost_review_ui, validate_localhost_review_ui_safe


REPORT_MD = Path("reports/runtime_v21a_web_localhost_review_ui_prototype.md")
REPORT_JSON = Path("reports/runtime_v21a_web_localhost_review_ui_prototype.json")


def write_localhost_review_ui_report() -> dict[str, object]:
    payload = render_static_localhost_review_ui()
    data = {**payload, "all_safe": validate_localhost_review_ui_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.1A - Web / Localhost Review UI Prototype",
        "",
        "Localhost-only review UI prototype using Python standard library rendering. Automated tests do not start a persistent server.",
        "",
        f"Static path: `{data['static_path']}`",
        f"Host: `{data['config']['host']}`",
        f"Port: `{data['config']['port']}`",
        f"All safe: `{data['all_safe']}`",
        "",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_localhost_review_ui_report()
    print(f"Runtime V2.1A localhost review UI: safe={result['all_safe']} final={result['final_recommendation']}")
