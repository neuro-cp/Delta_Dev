from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v24_localhost_full_review_console import build_full_console_snapshot, validate_full_console_safe, write_static_full_console_snapshot


REPORT_MD = Path("reports/runtime_v24a_localhost_full_review_console_ux.md")
REPORT_JSON = Path("reports/runtime_v24a_localhost_full_review_console_ux.json")


def write_full_console_report() -> dict[str, object]:
    cases = [build_full_console_snapshot(), build_full_console_snapshot(host="0.0.0.0"), write_static_full_console_snapshot()]
    data = {"phase": "Runtime V2.4A", "cases": cases, "all_safe": all(validate_full_console_safe(case) for case in cases), "final_recommendation": "PROCEED_CONTROLLED_MEMORY_WRITE_UX_TRIAL"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.4A - Localhost Full Review Console UX", "", "The full console is a localhost-only, static-renderable UX surface for current safe DELTA workflows.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_full_console_report()
    print(f"Runtime V2.4A full console: safe={result['all_safe']} final={result['final_recommendation']}")

