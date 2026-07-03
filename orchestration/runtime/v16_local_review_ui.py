from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v16_env import load_delta_evaluator_env


DASHBOARD_HTML = Path("reports/delta_review_dashboard.html")

RUNTIME_V16D_LOCAL_REVIEW_UI_FLAGS: dict[str, bool] = {
    "static_review_ui_enabled": True,
    "server_enabled": False,
    "network_calls_enabled": False,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "memory_write_enabled": False,
    "canonical_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "scheduler_enabled": False,
    "background_worker_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


APPROVAL_TEMPLATE = "\n".join(
    (
        "APPROVE_CANONICAL_MEMORY_WRITE",
        "candidate_id=<candidate_id>",
        "approved_by=user",
        "approval_scope=single_memory_candidate_only",
    )
)


class ReviewItemKind(str, Enum):
    MEMORY_CANDIDATE = "memory_candidate"
    CANONICAL_TRIAL_RECORD = "canonical_trial_record"
    RECALL_CONTEXT = "recall_context"
    EVALUATOR_REVIEW = "evaluator_review"


@dataclass(frozen=True)
class LocalReviewItem:
    item_id: str
    kind: ReviewItemKind
    title: str
    body: str
    source_path: str
    candidate_id: str = ""
    approval_text: str = ""
    not_authority: bool = True
    candidate_only: bool = True
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "kind": self.kind.value,
            "title": self.title,
            "body": self.body,
            "source_path": self.source_path,
            "candidate_id": self.candidate_id,
            "approval_text": self.approval_text,
            "not_authority": self.not_authority,
            "candidate_only": self.candidate_only,
            "mutating": self.mutating,
        }


def build_local_review_dashboard_data() -> dict[str, object]:
    items = [
        *_memory_candidate_items(),
        *_canonical_trial_record_items(),
        *_recall_context_items(),
        *_evaluator_review_items(),
    ]
    env = load_delta_evaluator_env().to_report_dict()
    return {
        "phase": "Runtime V1.6D",
        "title": "Local Review UI",
        "checkpoint_summary": "V1.6 local review dashboard over candidate-only records and advisory reports.",
        "model_b_status": "Model B remains the default runtime baseline.",
        "hyb1_status": "HYB1 remains dormant/env-gated and is not promoted.",
        "items": [item.as_dict() for item in items],
        "approval_template": APPROVAL_TEMPLATE,
        "safety_flags": dict(RUNTIME_V16D_LOCAL_REVIEW_UI_FLAGS),
        "env_summary": {
            "provider": env["provider"],
            "model": env["model"],
            "api_key_present": env["api_key_present"],
            "api_key_redacted": True,
            "live_call_permitted": env["live_call_permitted"],
        },
        "dashboard_path": str(DASHBOARD_HTML),
        "final_recommendation": "PROCEED_SCHEDULED_DAILY_EVALUATOR_DESIGN",
    }


def render_local_review_dashboard_html(data: dict[str, object]) -> str:
    item_sections = "\n".join(_render_item(item) for item in data["items"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DELTA Local Review Dashboard</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; line-height: 1.45; color: #202124; background: #f7f8fa; }}
    header, section {{ background: #fff; border: 1px solid #d9dde3; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
    h1, h2, h3 {{ margin-top: 0; }}
    code, pre {{ background: #f1f3f4; padding: 2px 4px; border-radius: 4px; }}
    pre {{ padding: 12px; overflow: auto; }}
    .badge {{ display: inline-block; border: 1px solid #c9ced6; border-radius: 999px; padding: 2px 8px; margin-right: 6px; font-size: 12px; }}
    .item {{ border-top: 1px solid #eceff3; padding-top: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>DELTA Local Review Dashboard</h1>
    <p>{html.escape(str(data["checkpoint_summary"]))}</p>
    <span class="badge">{html.escape(str(data["model_b_status"]))}</span>
    <span class="badge">{html.escape(str(data["hyb1_status"]))}</span>
  </header>
  <section>
    <h2>Safety Boundaries</h2>
    <p>This static file does not run a server, call providers, write memory, mutate recall, train, execute actions, or promote HYB1.</p>
    <p>API key present: <code>{html.escape(str(data["env_summary"]["api_key_present"]))}</code>; key is redacted and never rendered.</p>
  </section>
  <section>
    <h2>Approval Format</h2>
    <p>Copy this exact structure into the explicit write path only after review. Casual approval must not count.</p>
    <pre>{html.escape(str(data["approval_template"]))}</pre>
  </section>
  <section>
    <h2>Review Items</h2>
    {item_sections}
  </section>
</body>
</html>
"""


def write_local_review_dashboard(path: str | Path = DASHBOARD_HTML) -> dict[str, object]:
    data = build_local_review_dashboard_data()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_local_review_dashboard_html(data), encoding="utf-8")
    data["dashboard_path"] = str(output)
    return data


def validate_local_review_ui_safe(data: dict[str, object], rendered_html: str | None = None) -> bool:
    flags = data["safety_flags"]
    html_text = rendered_html or ""
    return (
        data["env_summary"]["api_key_redacted"] is True
        and "sk-" not in html_text
        and all(item["mutating"] is False for item in data["items"])
        and flags["static_review_ui_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "static_review_ui_enabled")
    )


def _render_item(item: dict[str, object]) -> str:
    approval = item.get("approval_text") or "No approval text generated for this item."
    return f"""
<div class="item">
  <h3>{html.escape(str(item["title"]))}</h3>
  <p><strong>Kind:</strong> <code>{html.escape(str(item["kind"]))}</code></p>
  <p><strong>Source:</strong> <code>{html.escape(str(item["source_path"]))}</code></p>
  <p>{html.escape(str(item["body"]))}</p>
  <p><span class="badge">Not authority</span><span class="badge">Candidate only</span><span class="badge">No mutation</span></p>
  <pre>{html.escape(str(approval))}</pre>
</div>
"""


def _memory_candidate_items() -> tuple[LocalReviewItem, ...]:
    report = _load_json(Path("reports/runtime_v16a_validated_experience_learning_loop.json"))
    candidate = (report.get("valid_payload") or {}).get("memory_candidate") if isinstance(report.get("valid_payload"), dict) else None
    if not isinstance(candidate, dict):
        return ()
    candidate_id = str(candidate.get("memory_candidate_id", ""))
    return (
        LocalReviewItem(
            item_id=_stable_id("v16d-review-item", "memory", candidate_id),
            kind=ReviewItemKind.MEMORY_CANDIDATE,
            title="Pending Memory Candidate",
            body=str(candidate.get("proposed_memory_text", "")),
            source_path="reports/runtime_v16a_validated_experience_learning_loop.json",
            candidate_id=candidate_id,
            approval_text=_approval_for_candidate(candidate_id),
        ),
    )


def _canonical_trial_record_items() -> tuple[LocalReviewItem, ...]:
    path = Path("data/runtime_v15i/canonical_memory_trial_records.jsonl")
    if not path.exists():
        return ()
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate_id = str(record.get("memory_candidate_id", ""))
        items.append(
            LocalReviewItem(
                item_id=_stable_id("v16d-review-item", "canonical", record.get("canonical_record_id", "")),
                kind=ReviewItemKind.CANONICAL_TRIAL_RECORD,
                title="Existing Canonical Trial Record",
                body=str(record.get("record_text", "")),
                source_path=str(path),
                candidate_id=candidate_id,
                approval_text=_approval_for_candidate(candidate_id),
            )
        )
    return tuple(items)


def _recall_context_items() -> tuple[LocalReviewItem, ...]:
    report = _load_json(Path("reports/runtime_v15j_recall_bridge_limited_trial.json"))
    context = (report.get("candidate_payload") or {}).get("candidate_context") if isinstance(report.get("candidate_payload"), dict) else None
    if not isinstance(context, dict):
        return ()
    return (
        LocalReviewItem(
            item_id=_stable_id("v16d-review-item", "recall", context.get("context_id", "")),
            kind=ReviewItemKind.RECALL_CONTEXT,
            title="Recall Candidate Context",
            body=str(context.get("record_text", "")),
            source_path="reports/runtime_v15j_recall_bridge_limited_trial.json",
            candidate_id=str(context.get("memory_candidate_id", "")),
            approval_text="Recall context is candidate-only and should not be approved from this dashboard.",
        ),
    )


def _evaluator_review_items() -> tuple[LocalReviewItem, ...]:
    report = _load_json(Path("reports/runtime_v16c_daily_external_consolidation_evaluator_api_trial.json"))
    review = report.get("advisory_review")
    if not isinstance(review, dict):
        return ()
    return (
        LocalReviewItem(
            item_id=_stable_id("v16d-review-item", "evaluator", review.get("review_id", "")),
            kind=ReviewItemKind.EVALUATOR_REVIEW,
            title="Evaluator Advisory Review",
            body=f"Disposition: {review.get('disposition', '')}; risk: {review.get('risk', '')}; rationale: {review.get('rationale', '')}",
            source_path="reports/runtime_v16c_daily_external_consolidation_evaluator_api_trial.json",
            approval_text="Evaluator review is advisory only and cannot approve canonical memory.",
        ),
    )


def _approval_for_candidate(candidate_id: str) -> str:
    return APPROVAL_TEMPLATE.replace("<candidate_id>", candidate_id or "<candidate_id>")


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
