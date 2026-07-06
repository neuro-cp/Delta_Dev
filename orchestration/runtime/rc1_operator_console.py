"""RC1 minimal local operator console support.

The console is a local operator surface over existing RC1/runtime artifacts. It
does not enable providers, training, autonomous actions, canonical writes,
recall mutation, or production routing. The only optional write is an explicit
operator observation/failure log entry under `data/rc1_operator_console/`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_release_candidate_freeze import (
    SAFETY as RC1_SAFETY,
    failure_classification,
    observation_framework,
    release_manifest,
    validation_summary,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DATA = ROOT / "data" / "rc1_operator_console"
OBSERVATION_LOG = DATA / "observations.jsonl"

CONSOLE_FLAGS = {
    "rc1_operator_console_enabled": True,
    "local_desktop_only": True,
    "paste_text_only": True,
    "provider_calls_enabled": False,
    "training_enabled": False,
    "canonical_writes_enabled": False,
    "autonomous_actions_enabled": False,
    "scheduler_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "recall_mutation_enabled": False,
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def report_summary() -> dict[str, Any]:
    rc1_reports = sorted(path.name for path in REPORTS.glob("RC1_*.json"))
    tp_reports = sorted(path.name for path in REPORTS.glob("TP*.json"))
    return {
        "rc1_report_count": len(rc1_reports),
        "tp_report_count": len(tp_reports),
        "latest_rc1_reports": rc1_reports,
        "latest_tp_report": tp_reports[-1] if tp_reports else None,
    }


def build_runtime_status() -> dict[str, Any]:
    validation = validation_summary()
    manifest = release_manifest()
    return {
        "version": manifest["version"],
        "status": manifest["status"],
        "operational_baseline": manifest["operational_baseline"],
        "latest_tp_phase": validation["latest_tp_phase"],
        "latest_tp_recommendation": validation["latest_tp_recommendation"],
        "safety": {**RC1_SAFETY, **CONSOLE_FLAGS},
        "reports": report_summary(),
    }


def build_corpus_substrate_summary() -> dict[str, Any]:
    candidates = [
        "TP11_BASE_CORPUS_MANIFEST.json",
        "TP14_SUBSTRATE_IMPROVEMENTS.json",
        "TP15_INTEGRATION_MAPPING.json",
        "TP20_TRAINING_NECESSITY_REASSESSMENT.json",
        "TP30_FINAL_ROADMAP_REVIEW.json",
    ]
    available = {name: (REPORTS / name).exists() for name in candidates}
    tp14 = _load_json(REPORTS / "TP14_SUBSTRATE_IMPROVEMENTS.json")
    improvements = tp14.get("improvements", [])
    return {
        "available_artifacts": available,
        "substrate_improvement_count": len(improvements),
        "substrate_improvements": [item.get("improvement_id") for item in improvements],
        "canonical_write_enabled": False,
        "training_enabled": False,
    }


def build_review_queue() -> list[dict[str, Any]]:
    mapping = _load_json(REPORTS / "TP15_INTEGRATION_MAPPING.json")
    items = []
    for item in mapping.get("mapped_improvements", []):
        items.append({
            "item_id": item.get("improvement_id"),
            "status": "rc1_review_reference",
            "active": item.get("active", False),
            "expected_runtime_effect": item.get("expected_runtime_effect"),
            "operator_review_required": True,
        })
    return items


def build_replay_rollback_inspection() -> dict[str, Any]:
    rollback = _load_json(REPORTS / "TP15_ROLLBACK_DESIGN.json")
    replay = _load_json(REPORTS / "TP22_REPLAY_OPTIMIZATION.json")
    return {
        "rollback_records": len(rollback.get("rollback_records", [])),
        "rollback_available": bool(rollback),
        "replay_report_available": bool(replay),
        "rollback_execution_enabled": False,
        "replay_scheduler_enabled": False,
    }


def build_operator_snapshot() -> dict[str, Any]:
    return {
        "runtime_status": build_runtime_status(),
        "corpus_substrate": build_corpus_substrate_summary(),
        "operator_review_queue": build_review_queue(),
        "replay_rollback": build_replay_rollback_inspection(),
        "observation_framework": observation_framework(),
        "failure_classification": failure_classification(),
        "console_flags": CONSOLE_FLAGS,
    }


def answer_operator_question(question: str) -> dict[str, Any]:
    from orchestration.runtime.rc1_release_candidate_freeze import answer_rc1_question, is_rc1_question
    from orchestration.runtime.tp16_tp30_master_marathon import answer_tp16_tp30_question, is_tp16_tp30_question
    from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer

    if is_rc1_question(question):
        route = "rc1_release_candidate"
        data = answer_rc1_question(question)
        answer = data["answer_text"]
    elif is_tp16_tp30_question(question):
        route = "tp16_tp30"
        data = answer_tp16_tp30_question(question)
        answer = data["answer_text"]
    else:
        route = "v29_local_answer"
        data = run_v29_local_answer(question, use_recall=False)
        answer = data.get("answer") or data.get("answer_text") or "No local deterministic answer was available."
    return {
        "route": route,
        "question": question,
        "answer": answer,
        "provider_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def preview_evidence_ingest(pasted_text: str) -> dict[str, Any]:
    text = pasted_text.strip()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
    lines = [line for line in text.splitlines() if line.strip()]
    return {
        "preview_id": f"rc1-evidence-preview-{digest[:16]}" if digest else "rc1-evidence-preview-empty",
        "characters": len(text),
        "nonempty_lines": len(lines),
        "sha256": digest,
        "persisted": False,
        "canonical_write_performed": False,
        "provider_calls_performed": False,
        "note": "Paste preview only. No upload, provider call, training, canonical write, or substrate mutation occurred.",
    }


def build_observation_entry(category: str, note: str, severity: str = "P3") -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    raw = f"{now}|{category}|{severity}|{note}"
    observation_id = "rc1-observation-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return {
        "observation_id": observation_id,
        "timestamp": now,
        "operator": "local_operator",
        "workflow": "rc1_operator_console",
        "category": category,
        "severity": severity,
        "expected_behavior": "",
        "observed_behavior": note,
        "evidence_path": "",
        "reproduction_steps": "",
        "impact": "",
        "candidate_fix": "",
        "triage_decision": "untriaged",
        "canonical_write_performed": False,
        "memory_mutation_performed": False,
    }


def append_observation(entry: dict[str, Any], path: Path = OBSERVATION_LOG) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return {
        "written": True,
        "path": str(path),
        "observation_id": entry["observation_id"],
        "local_operational_log_only": True,
        "canonical_write_performed": False,
        "memory_mutation_performed": False,
    }


def validate_console_safe(snapshot: dict[str, Any]) -> bool:
    flags = snapshot["console_flags"]
    return (
        flags["rc1_operator_console_enabled"] is True
        and flags["local_desktop_only"] is True
        and flags["paste_text_only"] is True
        and all(
            value is False
            for key, value in flags.items()
            if key not in {"rc1_operator_console_enabled", "local_desktop_only", "paste_text_only"}
        )
    )

