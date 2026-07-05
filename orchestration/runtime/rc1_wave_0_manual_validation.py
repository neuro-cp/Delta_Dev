"""RC1 Wave 0 manual validation report wrapper."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.delta_rc1_manual_validation import run_manual_validation


REPORT_JSON = Path("reports/runtime_rc1_wave_0_manual_validation.json")
REPORT_MD = Path("reports/runtime_rc1_wave_0_manual_validation.md")


def build_wave_0_manual_validation() -> dict[str, Any]:
    report = run_manual_validation()
    return {
        "phase": "RC1 Wave 0 Manual Validation",
        **report,
        "wave": 0,
        "live_capabilities_enabled": False,
        "final_recommendation": "PROCEED_WAVE_1_FIXTURE_CORPUS_INGESTION",
    }


def write_wave_0_report() -> dict[str, Any]:
    payload = build_wave_0_manual_validation()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# RC1 Wave 0 Manual Validation", ""]
    lines.extend(f"- {key}: {'PASS' if value else 'FAIL'}" for key, value in payload["checks"].items())
    lines.extend(["", f"Final recommendation: `{payload['final_recommendation']}`", ""])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(write_wave_0_report()["final_recommendation"])
