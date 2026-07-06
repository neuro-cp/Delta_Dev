"""Report generator for the RC1 minimal operator console."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_operator_console import (
    build_operator_snapshot,
    preview_evidence_ingest,
    validate_console_safe,
)


REPORT_MD = Path("reports/RC1_OPERATOR_CONSOLE_UI.md")
REPORT_JSON = Path("reports/RC1_OPERATOR_CONSOLE_UI.json")


def build_operator_console_report() -> dict[str, Any]:
    snapshot = build_operator_snapshot()
    preview = preview_evidence_ingest("Sample pasted evidence for RC1 console validation.")
    return {
        "phase": "DELTA Runtime v4.0 RC1 Operator Console UI",
        "ui_route": ".\\.venv311\\Scripts\\python.exe .\\DELTA.py",
        "compatibility_ui_route": ".\\.venv311\\Scripts\\python.exe .\\delta_operator_console.py",
        "snapshot": snapshot,
        "paste_preview": preview,
        "safe": validate_console_safe(snapshot),
        "features": [
            "cognitive state home screen",
            "current runtime status",
            "corpus/substrate summary",
            "text paste evidence preview",
            "deterministic proposition extraction",
            "operator-approved noncanonical substrate write",
            "cognitive state panel",
            "operator review queue inspection",
            "local ask/reasoning panel",
            "provenance/citation via existing report references",
            "contradiction and replay references through existing reports",
            "replay/rollback inspection",
            "structured local failure/observation logging",
            "operational observation notes",
        ],
        "remaining_gaps": [
            "no file upload workflow yet",
            "no live corpus ingestion",
            "no provider-assisted answers",
            "no canonical writes",
            "no autonomous review or action",
        ],
        "final_recommendation": "USE_RC1_OPERATOR_CONSOLE_FOR_CONTROLLED_OPERATIONAL_OBSERVATION",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# RC1 Operator Console UI",
        "",
        f"UI route: `{payload['ui_route']}`",
        "",
        f"Safe: `{payload['safe']}`",
        "",
        "## Features",
    ]
    lines.extend(f"- {item}" for item in payload["features"])
    lines.extend(["", "## Remaining Gaps"])
    lines.extend(f"- {item}" for item in payload["remaining_gaps"])
    lines.extend([
        "",
        "## Safety",
        "- no provider calls",
        "- no training",
        "- no canonical writes",
        "- no autonomous action",
        "- no scheduler activation",
        "- no HYB1 promotion",
        "",
        "## Recommendation",
        f"`{payload['final_recommendation']}`",
        "",
    ])
    return "\n".join(lines)


def write_operator_console_report() -> dict[str, Any]:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    payload = build_operator_console_report()
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    data = write_operator_console_report()
    print(json.dumps({
        "safe": data["safe"],
        "ui_route": data["ui_route"],
        "final_recommendation": data["final_recommendation"],
    }, indent=2, sort_keys=True))
