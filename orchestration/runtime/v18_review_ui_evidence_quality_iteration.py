from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from pathlib import Path


QUALITY_REVIEW_UI_PATH = Path("ui/delta_quality_review_dashboard.html")

RUNTIME_V18D_FLAGS: dict[str, bool] = {
    "quality_review_ui_enabled": True,
    "static_ui_only": True,
    "provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "scheduler_enabled": False,
    "background_worker_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class QualityReviewMetricDisplay:
    metric_id: str
    label: str
    value: str
    source: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class QualityReviewBlockerDisplay:
    blocker_id: str
    target: str
    blocker: str
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class QualityReviewDashboardSection:
    section_id: str
    title: str
    body: str
    labels: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"section_id": self.section_id, "title": self.title, "body": self.body, "labels": list(self.labels)}


@dataclass(frozen=True)
class QualityReviewSafetyStatus:
    safety_status_id: str
    key_redacted: bool
    no_provider_call: bool
    no_memory_write: bool
    no_recall_mutation: bool
    no_training: bool
    no_scheduler: bool
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class QualityReviewUIInput:
    input_id: str
    metrics: tuple[QualityReviewMetricDisplay, ...]
    blockers: tuple[QualityReviewBlockerDisplay, ...]
    sections: tuple[QualityReviewDashboardSection, ...]
    safety_status: QualityReviewSafetyStatus

    def as_dict(self) -> dict[str, object]:
        return {
            "input_id": self.input_id,
            "metrics": [metric.as_dict() for metric in self.metrics],
            "blockers": [blocker.as_dict() for blocker in self.blockers],
            "sections": [section.as_dict() for section in self.sections],
            "safety_status": self.safety_status.as_dict(),
        }


@dataclass(frozen=True)
class QualityReviewUIReportEntry:
    report_entry_id: str
    output_path: str
    metric_count: int
    blocker_count: int
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_quality_review_ui_input() -> QualityReviewUIInput:
    evidence = _load_json(Path("reports/runtime_v18a_evidence_quality_evaluation_harness.json"))
    readiness = _load_json(Path("reports/runtime_v18b_promotion_readiness_scorecard.json"))
    synthesis = _load_json(Path("reports/runtime_v17g_controlled_answer_synthesis.json"))
    metrics = _quality_metrics(evidence, readiness, synthesis)
    blockers = _readiness_blockers(readiness)
    sections = (
        QualityReviewDashboardSection(_stable_id("v18d-section", "summary"), "Evidence Quality Summary", "Scorecards summarize provenance, uncertainty, source-role correctness, candidate/truth distinction, conflict handling, unsupported fallback, and mutation safety.", ("candidate != truth", "evidence score != promotion")),
        QualityReviewDashboardSection(_stable_id("v18d-section", "readiness"), "Promotion Readiness Summary", "Readiness states are review signals only. They do not promote capabilities or artifacts.", ("promotion readiness != promotion",)),
        QualityReviewDashboardSection(_stable_id("v18d-section", "synthesis"), "Synthesis Safety Status", "Synthesis drafts keep local, recall, provider, specialist, and evaluator sources labeled with uncertainty and provenance.", ("provider answer != truth", "specialist answer != authority")),
        QualityReviewDashboardSection(_stable_id("v18d-section", "next"), "Next Manual Step", "Review blockers and evidence quality before any optional live provider trial. Live calls require explicit gates and a CLI live flag.", ("manual review required",)),
    )
    safety = QualityReviewSafetyStatus(_stable_id("v18d-safety"), True, True, True, True, True, True, True)
    return QualityReviewUIInput(_stable_id("v18d-input", len(metrics), len(blockers)), tuple(metrics), tuple(blockers), sections, safety)


def render_quality_review_dashboard(ui_input: QualityReviewUIInput) -> str:
    metrics = "\n".join(f"<li><strong>{html.escape(m.label)}:</strong> {html.escape(m.value)} <code>{html.escape(m.source)}</code></li>" for m in ui_input.metrics)
    blockers = "\n".join(f"<li><strong>{html.escape(b.target)}:</strong> {html.escape(b.blocker)} - {html.escape(b.rationale)}</li>" for b in ui_input.blockers) or "<li>No blockers reported.</li>"
    sections = "\n".join(_section_html(section) for section in ui_input.sections)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DELTA Quality Review Dashboard</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f7f8fa; color: #202124; line-height: 1.45; }}
    header, section {{ background: white; border: 1px solid #d9dde3; border-radius: 8px; padding: 16px; margin-bottom: 14px; }}
    .badge {{ display: inline-block; border: 1px solid #c9ced6; border-radius: 999px; padding: 2px 8px; margin: 2px 4px 2px 0; font-size: 12px; }}
    code {{ background: #f1f3f4; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>DELTA Quality Review Dashboard</h1>
    <p>Static local dashboard. Evidence, readiness, provider, specialist, evaluator, and recall items remain non-authoritative.</p>
    <span class="badge">key redacted</span><span class="badge">no provider call</span><span class="badge">no memory write</span><span class="badge">no scheduler</span>
  </header>
  <section><h2>Metrics</h2><ul>{metrics}</ul></section>
  <section><h2>Blockers</h2><ul>{blockers}</ul></section>
  {sections}
</body>
</html>
"""


def write_quality_review_dashboard(path: str | Path = QUALITY_REVIEW_UI_PATH) -> dict[str, object]:
    ui_input = build_quality_review_ui_input()
    rendered = render_quality_review_dashboard(ui_input)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    entry = QualityReviewUIReportEntry(_stable_id("v18d-entry", output), str(output), len(ui_input.metrics), len(ui_input.blockers), validate_quality_review_ui_safe(ui_input.as_dict(), rendered))
    return {
        "phase": "Runtime V1.8D",
        "ui_input": ui_input.as_dict(),
        "report_entry": entry.as_dict(),
        "safety_flags": dict(RUNTIME_V18D_FLAGS),
        "final_recommendation": "PROCEED_MANUAL_PROVIDER_LIVE_TRIAL_GATE",
    }


def validate_quality_review_ui_safe(data: dict[str, object], rendered_html: str = "") -> bool:
    flags = data.get("safety_flags", RUNTIME_V18D_FLAGS)
    safety = (data.get("ui_input") or data).get("safety_status", {})
    return (
        "sk-" not in rendered_html
        and safety.get("key_redacted") is True
        and flags["quality_review_ui_enabled"] is True
        and flags["static_ui_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"quality_review_ui_enabled", "static_ui_only"})
    )


def _quality_metrics(evidence: dict[str, object], readiness: dict[str, object], synthesis: dict[str, object]) -> list[QualityReviewMetricDisplay]:
    return [
        QualityReviewMetricDisplay(_stable_id("v18d-metric", "average"), "Evidence quality average", str((evidence.get("report_entry") or {}).get("average_score", "unknown")), "runtime_v18a"),
        QualityReviewMetricDisplay(_stable_id("v18d-metric", "ready"), "Ready for human review", str((readiness.get("report_entry") or {}).get("ready_for_human_review_count", "unknown")), "runtime_v18b"),
        QualityReviewMetricDisplay(_stable_id("v18d-metric", "blocked"), "Promotion blockers", str((readiness.get("report_entry") or {}).get("blocked_count", "unknown")), "runtime_v18b"),
        QualityReviewMetricDisplay(_stable_id("v18d-metric", "synthesis"), "Synthesis cases", str(len(synthesis.get("cases", []))), "runtime_v17g"),
        QualityReviewMetricDisplay(_stable_id("v18d-metric", "secret"), "Secret redaction", "key_redacted=true", "local_ui"),
    ]


def _readiness_blockers(readiness: dict[str, object]) -> list[QualityReviewBlockerDisplay]:
    displays: list[QualityReviewBlockerDisplay] = []
    for card in readiness.get("scorecards", []):
        for blocker in card.get("blockers", []):
            displays.append(QualityReviewBlockerDisplay(_stable_id("v18d-blocker", card["target"]["name"], blocker["kind"]), card["target"]["name"], blocker["kind"], blocker["rationale"]))
    return displays


def _section_html(section: QualityReviewDashboardSection) -> str:
    labels = "".join(f'<span class="badge">{html.escape(label)}</span>' for label in section.labels)
    return f"<section><h2>{html.escape(section.title)}</h2>{labels}<p>{html.escape(section.body)}</p></section>"


def _load_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
