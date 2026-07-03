from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v17_limited_general_recall_router import route_limited_general_recall
from orchestration.runtime.v17_provider_assisted_unknown_answer import answer_unknown_with_controlled_provider
from orchestration.runtime.v17_specialist_evidence_acquisition_trial import run_specialist_evidence_trial


EVIDENCE_REVIEW_UI_PATH = Path("ui/delta_evidence_review_dashboard.html")

RUNTIME_V17E_FLAGS: dict[str, bool] = {
    "provider_evidence_review_ui_enabled": True,
    "static_ui_only": True,
    "provider_call_performed": False,
    "specialist_call_performed": False,
    "evaluator_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "scheduler_enabled": False,
    "background_worker_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class EvidenceReviewSourceLabel(str, Enum):
    LOCAL_ANSWER = "local_answer"
    RECALL_CANDIDATE = "recall_candidate_context"
    PROVIDER_EVIDENCE = "provider_evidence_packet"
    SPECIALIST_EVIDENCE = "specialist_evidence_packet"
    EVALUATOR_ADVISORY = "evaluator_advisory_review"


class EvidenceReviewSafetyStatus(str, Enum):
    LOCAL_NON_MUTATING = "local_non_mutating"
    CANDIDATE_CONTEXT_ONLY = "candidate_context_only"
    EVIDENCE_ONLY = "evidence_only_not_authority"
    ADVISORY_ONLY = "advisory_only_not_authority"


@dataclass(frozen=True)
class EvidenceReviewItem:
    item_id: str
    title: str
    source_label: EvidenceReviewSourceLabel
    body: str
    provenance: str
    confidence_label: str
    safety_status: EvidenceReviewSafetyStatus
    live_call_occurred: bool = False
    key_redacted: bool = True
    recommended_next_action: str = "inspect_only"
    authoritative: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "source_label": self.source_label.value,
            "body": self.body,
            "provenance": self.provenance,
            "confidence_label": self.confidence_label,
            "safety_status": self.safety_status.value,
            "live_call_occurred": self.live_call_occurred,
            "key_redacted": self.key_redacted,
            "recommended_next_action": self.recommended_next_action,
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class EvidenceReviewUIInput:
    title: str
    items: tuple[EvidenceReviewItem, ...]

    def as_dict(self) -> dict[str, object]:
        return {"title": self.title, "items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class EvidenceReviewExport:
    export_id: str
    path: str
    html_preview_safe: bool
    item_count: int

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class EvidenceReviewUIReportEntry:
    report_entry_id: str
    item_count: int
    output_path: str
    all_items_non_authoritative: bool
    no_live_calls: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_evidence_review_ui_input() -> EvidenceReviewUIInput:
    items = [
        _local_answer_item(),
        *_recall_candidate_items(),
        _provider_evidence_item(),
        _specialist_evidence_item(),
        *_evaluator_advisory_items(),
    ]
    return EvidenceReviewUIInput("DELTA Evidence Review Dashboard", tuple(items))


def render_evidence_review_html(ui_input: EvidenceReviewUIInput) -> str:
    sections = "\n".join(_render_item(item) for item in ui_input.items)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(ui_input.title)}</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f7f8fa; color: #202124; line-height: 1.45; }}
    header, section {{ background: white; border: 1px solid #d9dde3; border-radius: 8px; padding: 16px; margin-bottom: 14px; }}
    .badge {{ display: inline-block; border: 1px solid #c9ced6; border-radius: 999px; padding: 2px 8px; margin: 2px 4px 2px 0; font-size: 12px; }}
    code {{ background: #f1f3f4; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(ui_input.title)}</h1>
    <p>Static evidence review only. Provider, specialist, evaluator, and recall entries are not authority and do not write memory.</p>
  </header>
  {sections}
</body>
</html>
"""


def write_evidence_review_ui(path: str | Path = EVIDENCE_REVIEW_UI_PATH) -> dict[str, object]:
    ui_input = build_evidence_review_ui_input()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_evidence_review_html(ui_input)
    output.write_text(rendered, encoding="utf-8")
    report_entry = EvidenceReviewUIReportEntry(
        report_entry_id=_stable_id("v17e-report", output, len(ui_input.items)),
        item_count=len(ui_input.items),
        output_path=str(output),
        all_items_non_authoritative=all(item.authoritative is False for item in ui_input.items),
        no_live_calls=all(item.live_call_occurred is False for item in ui_input.items),
    )
    return {
        "phase": "Runtime V1.7E",
        "ui_input": ui_input.as_dict(),
        "export": EvidenceReviewExport(_stable_id("v17e-export", output), str(output), validate_evidence_review_ui_safe(ui_input.as_dict(), rendered), len(ui_input.items)).as_dict(),
        "report_entry": report_entry.as_dict(),
        "safety_flags": dict(RUNTIME_V17E_FLAGS),
        "final_recommendation": "PROCEED_LIMITED_GENERAL_RECALL_TRIAL",
    }


def validate_evidence_review_ui_safe(data: dict[str, object], rendered_html: str = "") -> bool:
    items = data.get("items") or data.get("ui_input", {}).get("items", [])
    flags = data.get("safety_flags", RUNTIME_V17E_FLAGS)
    return (
        "sk-" not in rendered_html
        and all(item["authoritative"] is False for item in items)
        and all(item["key_redacted"] is True for item in items)
        and all(item["live_call_occurred"] is False for item in items)
        and flags["provider_evidence_review_ui_enabled"] is True
        and flags["static_ui_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"provider_evidence_review_ui_enabled", "static_ui_only"})
    )


def _local_answer_item() -> EvidenceReviewItem:
    route = route_local_knowledge_answer("What is Model B?")
    text = route.answer.answer_text if route.answer else route.unsupported_reason
    return EvidenceReviewItem(
        item_id=_stable_id("v17e-local", route.route_id),
        title="Local Answer Evidence",
        source_label=EvidenceReviewSourceLabel.LOCAL_ANSWER,
        body=text,
        provenance="orchestration.runtime.v15_local_knowledge_router",
        confidence_label="repo-local deterministic",
        safety_status=EvidenceReviewSafetyStatus.LOCAL_NON_MUTATING,
        recommended_next_action="usable_as_local_scaffold_answer",
    )


def _recall_candidate_items() -> tuple[EvidenceReviewItem, ...]:
    payload = route_limited_general_recall("What does DELTA know about HYB1?")
    items = []
    for candidate in payload["candidates"]:
        items.append(
            EvidenceReviewItem(
                item_id=_stable_id("v17e-recall", candidate["candidate_id"]),
                title="Recall Candidate Evidence",
                source_label=EvidenceReviewSourceLabel.RECALL_CANDIDATE,
                body=str(candidate["text"]),
                provenance=str(candidate["source_reference"]),
                confidence_label="candidate-context only",
                safety_status=EvidenceReviewSafetyStatus.CANDIDATE_CONTEXT_ONLY,
                recommended_next_action="inspect_as_candidate_context",
            )
        )
    if not items:
        report_path = Path("reports/runtime_v17a_limited_general_recall_router_design.json")
        try:
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            report_payload = {}
        for candidate in report_payload.get("candidates", []):
            items.append(
                EvidenceReviewItem(
                    item_id=_stable_id("v17e-recall-report", candidate.get("candidate_id", "")),
                    title="Recall Candidate Evidence",
                    source_label=EvidenceReviewSourceLabel.RECALL_CANDIDATE,
                    body=str(candidate.get("text", "")),
                    provenance=str(candidate.get("source_reference", report_path)),
                    confidence_label="candidate-context only",
                    safety_status=EvidenceReviewSafetyStatus.CANDIDATE_CONTEXT_ONLY,
                    recommended_next_action="inspect_as_candidate_context",
                )
            )
    return tuple(items)


def _provider_evidence_item() -> EvidenceReviewItem:
    payload = answer_unknown_with_controlled_provider("What recent fact is outside local DELTA knowledge?")
    request = payload["route_or_provider_request"]
    return EvidenceReviewItem(
        item_id=_stable_id("v17e-provider", payload["decision"]["decision_id"]),
        title="Provider-Assisted Unknown Evidence Packet",
        source_label=EvidenceReviewSourceLabel.PROVIDER_EVIDENCE,
        body=f"Dry-run provider request for model {request.get('model', '')}; no provider response was treated as truth.",
        provenance="Runtime V1.7C dry-run provider request",
        confidence_label="evidence-only dry-run",
        safety_status=EvidenceReviewSafetyStatus.EVIDENCE_ONLY,
        live_call_occurred=bool(payload["decision"]["provider_call_performed"]),
        key_redacted=bool(request.get("api_key_redacted", True)),
        recommended_next_action="manual_review_before_any_live_call",
    )


def _specialist_evidence_item() -> EvidenceReviewItem:
    payload = run_specialist_evidence_trial("Specialized unknown", specialist_domain="general")
    request = payload["route_or_provider_contract"]
    return EvidenceReviewItem(
        item_id=_stable_id("v17e-specialist", payload["decision"]["decision_id"]),
        title="Specialist Evidence Packet",
        source_label=EvidenceReviewSourceLabel.SPECIALIST_EVIDENCE,
        body=f"Dry-run specialist request for domain {request.get('specialist_domain', '')}; specialist output is evidence only.",
        provenance="Runtime V1.7D dry-run specialist request",
        confidence_label="specialist evidence only",
        safety_status=EvidenceReviewSafetyStatus.EVIDENCE_ONLY,
        live_call_occurred=bool(payload["decision"]["provider_call_performed"]),
        key_redacted=bool(request.get("api_key_redacted", True)),
        recommended_next_action="manual_review_before_specialist_merge",
    )


def _evaluator_advisory_items() -> tuple[EvidenceReviewItem, ...]:
    path = Path("reports/runtime_v16c_daily_external_consolidation_evaluator_api_trial.json")
    if not path.exists():
        return ()
    try:
        review = json.loads(path.read_text(encoding="utf-8")).get("advisory_review", {})
    except json.JSONDecodeError:
        return ()
    if not isinstance(review, dict):
        return ()
    return (
        EvidenceReviewItem(
            item_id=_stable_id("v17e-evaluator", review.get("review_id", "")),
            title="Evaluator Advisory Review",
            source_label=EvidenceReviewSourceLabel.EVALUATOR_ADVISORY,
            body=f"Disposition: {review.get('disposition', '')}; risk: {review.get('risk', '')}; rationale: {review.get('rationale', '')}",
            provenance=str(path),
            confidence_label="advisory only",
            safety_status=EvidenceReviewSafetyStatus.ADVISORY_ONLY,
            recommended_next_action="advisory_review_only",
        ),
    )


def _render_item(item: EvidenceReviewItem) -> str:
    return f"""<section>
  <h2>{html.escape(item.title)}</h2>
  <span class="badge">{html.escape(item.source_label.value)}</span>
  <span class="badge">{html.escape(item.safety_status.value)}</span>
  <span class="badge">Evidence only / not authority</span>
  <p>{html.escape(item.body)}</p>
  <p><strong>Provenance:</strong> <code>{html.escape(item.provenance)}</code></p>
  <p><strong>Confidence:</strong> {html.escape(item.confidence_label)}</p>
  <p><strong>Live call occurred:</strong> <code>{str(item.live_call_occurred).lower()}</code>; <strong>key redacted:</strong> <code>{str(item.key_redacted).lower()}</code></p>
  <p><strong>Next action:</strong> <code>{html.escape(item.recommended_next_action)}</code></p>
</section>"""


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
