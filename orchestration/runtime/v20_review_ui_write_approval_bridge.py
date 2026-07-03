from __future__ import annotations

import html
import json
from pathlib import Path

from orchestration.runtime.v20_controlled_general_memory_trial import APPROVAL_HEADER


APPROVAL_TEMPLATE = f"{APPROVAL_HEADER}\ncandidate_id={{candidate_id}}\napproved_by=user\napproval_scope=single_memory_candidate_only"
REJECT_TEMPLATE = "REJECT_MEMORY_CANDIDATE\ncandidate_id={candidate_id}\nrejected_by=user\nrejection_scope=single_memory_candidate_only"
DEFER_TEMPLATE = "DEFER_MEMORY_CANDIDATE\ncandidate_id={candidate_id}\ndeferred_by=user\ndefer_scope=single_memory_candidate_only"
EXPORT_DIR = Path("data/runtime_v20d/approval_exports")
UI_PATH = Path("ui/delta_memory_review_dashboard.html")


RUNTIME_V20D_FLAGS = {
    "review_ui_bridge_enabled": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def build_review_ui_exports(candidate_id: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "approve": APPROVAL_TEMPLATE.format(candidate_id=candidate_id),
        "reject": REJECT_TEMPLATE.format(candidate_id=candidate_id),
        "defer": DEFER_TEMPLATE.format(candidate_id=candidate_id),
    }


def generate_review_ui_write_approval_bridge(candidate_id: str = "memory-candidate-demo") -> dict[str, object]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    UI_PATH.parent.mkdir(parents=True, exist_ok=True)
    exports = build_review_ui_exports(candidate_id)
    for name in ("approve", "reject", "defer"):
        (EXPORT_DIR / f"{candidate_id}.{name}.txt").write_text(exports[name], encoding="utf-8")
    UI_PATH.write_text(_render_html(exports), encoding="utf-8")
    return {
        "phase": "Runtime V2.0D",
        "candidate_id": candidate_id,
        "ui_path": str(UI_PATH),
        "export_dir": str(EXPORT_DIR),
        "exports": exports,
        "invariant_flags": dict(RUNTIME_V20D_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_RECALL_TRIAL",
    }


def validate_review_ui_bridge_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return flags["review_ui_bridge_enabled"] is True and all(value is False for key, value in flags.items() if key != "review_ui_bridge_enabled")


def _render_html(exports: dict[str, object]) -> str:
    return f"""<!doctype html>
<html><head><meta charset=\"utf-8\"><title>DELTA Memory Review</title></head>
<body>
<h1>DELTA Memory Review Bridge</h1>
<p>Static export only. This page does not write memory.</p>
<h2>Candidate</h2><code>{html.escape(str(exports['candidate_id']))}</code>
<h2>Approve</h2><pre>{html.escape(str(exports['approve']))}</pre>
<h2>Reject</h2><pre>{html.escape(str(exports['reject']))}</pre>
<h2>Defer</h2><pre>{html.escape(str(exports['defer']))}</pre>
</body></html>
"""


def export_bridge_summary_json(path: str | Path, payload: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
