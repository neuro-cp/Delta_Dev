"""Runtime V2.6A training dataset review UI scaffold.

This module creates static review artifacts only. It does not export training
data, start training, call providers, or mutate memory.
"""

from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v26a_training_dataset_review_ui.md")
REPORT_JSON = Path("reports/runtime_v26a_training_dataset_review_ui.json")
UI_PATH = Path("ui/delta_training_dataset_review.html")


def build_training_dataset_review_ui() -> dict[str, object]:
    return {
        "phase": "Runtime V2.6A",
        "mode": "static_review_ui_design_only",
        "ui_path": str(UI_PATH),
        "review_fields": ["candidate_id", "input", "output", "provenance", "redaction_status", "review_decision"],
        "controls": ["approve_for_export", "reject", "needs_redaction", "defer"],
        "safety_invariants": _safe_flags(),
        "final_recommendation": "PROCEED_DATASET_REDACTION_PII_SCRUB_TRIAL",
    }


def write_training_dataset_review_ui_report() -> dict[str, object]:
    data = build_training_dataset_review_ui()
    UI_PATH.parent.mkdir(parents=True, exist_ok=True)
    UI_PATH.write_text(_render_ui(data), encoding="utf-8")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(_render_report(data), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def validate_training_dataset_review_ui_safe(data: dict[str, object]) -> bool:
    return data["mode"].endswith("design_only") and all(value is False for value in data["safety_invariants"].values())


def _safe_flags() -> dict[str, bool]:
    return {
        "training_performed": False,
        "dataset_exported": False,
        "provider_call_performed": False,
        "memory_write_performed": False,
        "recall_mutated": False,
        "model_artifact_created": False,
        "scheduler_started": False,
    }


def _render_ui(data: dict[str, object]) -> str:
    return """<!doctype html>
<html lang=\"en\">
<meta charset=\"utf-8\">
<title>DELTA Dataset Review</title>
<body>
<main>
  <h1>DELTA Dataset Review</h1>
  <p>Static scaffold only. No training, export, provider calls, or memory mutation.</p>
  <textarea aria-label=\"candidate review\" rows=\"10\" cols=\"80\"></textarea>
  <div>
    <button type=\"button\">Approve for export</button>
    <button type=\"button\">Reject</button>
    <button type=\"button\">Needs redaction</button>
    <button type=\"button\">Defer</button>
  </div>
</main>
</body>
</html>
"""


def _render_report(data: dict[str, object]) -> str:
    return f"# {data['phase']} Training Dataset Review UI\n\nMode: {data['mode']}\n\nFinal recommendation: {data['final_recommendation']}\n"


if __name__ == "__main__":
    result = write_training_dataset_review_ui_report()
    print(result["final_recommendation"])
