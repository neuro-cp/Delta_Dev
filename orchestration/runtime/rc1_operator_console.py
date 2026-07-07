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
PROPOSITION_LOG = DATA / "noncanonical_propositions.jsonl"
EVIDENCE_LOG = DATA / "evidence_links.jsonl"
REPLAY_LOG = DATA / "replay_queue.jsonl"
CONTRADICTION_LOG = DATA / "contradictions.jsonl"
LOCAL_STORE_LOGS = (PROPOSITION_LOG, EVIDENCE_LOG, REPLAY_LOG, CONTRADICTION_LOG)

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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _stable_id(prefix: str, text: str) -> str:
    return f"{prefix}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def normalize_claim(claim: str) -> dict[str, Any]:
    """Normalize a narrow RC1 proposition into subject/predicate/polarity.

    This is deterministic and intentionally conservative. It is built for the
    first operator-console contradiction class: affirmative claims versus
    negated/forbidden claims over the same subject and predicate.
    """
    text = claim.strip().rstrip(".")
    lower = text.lower()
    subject = "unknown"
    predicate = lower
    if lower.startswith("project frontier "):
        subject = "project frontier"
        predicate = lower.removeprefix("project frontier ").strip()

    polarity = "positive"
    negative_markers = [
        "should not ",
        "must not ",
        "does not ",
        "do not ",
        "cannot ",
        "can not ",
        "never ",
        "requires operator review before ",
    ]
    for marker in negative_markers:
        if marker in predicate:
            polarity = "negative"
            predicate = predicate.replace(marker, "", 1).strip()
            break

    replacements = {
        "approve ": "approves ",
        "approval": "approve",
    }
    for old, new in replacements.items():
        predicate = predicate.replace(old, new)
    predicate = " ".join(predicate.split())
    return {
        "subject": subject,
        "predicate": predicate,
        "polarity": polarity,
        "normalized_key": f"{subject}|{predicate}",
    }


def detect_contradictions_for_record(record: dict[str, Any], existing_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = record["normalized"]
    contradictions = []
    for existing in existing_records:
        other = existing.get("normalized", normalize_claim(existing.get("claim", "")))
        if (
            other["normalized_key"] == normalized["normalized_key"]
            and other["polarity"] != normalized["polarity"]
        ):
            contradiction_id = _stable_id("rc1-contradiction", record["proposition_id"] + existing["proposition_id"])
            contradictions.append({
                "contradiction_id": contradiction_id,
                "subject": normalized["subject"],
                "predicate": normalized["predicate"],
                "claim_a": existing["claim"],
                "claim_a_id": existing["proposition_id"],
                "claim_a_polarity": other["polarity"],
                "claim_b": record["claim"],
                "claim_b_id": record["proposition_id"],
                "claim_b_polarity": normalized["polarity"],
                "status": "operator_review_recommended",
                "canonical": False,
            })
    return contradictions


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
        "rc1_noncanonical_state": build_cognitive_state(),
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
        "cognitive_state": build_cognitive_state(),
        "console_flags": CONSOLE_FLAGS,
    }


def answer_operator_question(question: str) -> dict[str, Any]:
    from orchestration.runtime.rc1_release_candidate_freeze import answer_rc1_question, is_rc1_question
    from orchestration.runtime.tp16_tp30_master_marathon import answer_tp16_tp30_question, is_tp16_tp30_question
    from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer

    substrate = query_noncanonical_substrate(question)
    if substrate["matched"]:
        route = "rc1_noncanonical_substrate"
        answer = substrate["answer"]
    elif is_rc1_question(question):
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


def extract_propositions(pasted_text: str) -> dict[str, Any]:
    """Create reviewable proposition candidates from pasted operator text.

    Extraction is intentionally simple and deterministic for RC1. It creates
    candidates only; it does not persist anything until the operator approves.
    """
    text = pasted_text.strip()
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in text.replace("\r\n", "\n").replace(";", ".").split("\n"):
        for part in raw.split("."):
            claim = part.strip()
            if not claim:
                continue
            if claim[-1:] not in {".", "!", "?"}:
                claim = claim + "."
            key = claim.lower()
            if key in seen:
                continue
            seen.add(key)
            proposition_id = _stable_id("rc1-proposition", claim)
            candidates.append({
                "proposition_id": proposition_id,
                "claim": claim,
                "source": "operator_paste",
                "confidence": "operator_asserted_unverified",
                "status": "pending_operator_review",
                "canonical": False,
                "selected_by_default": True,
            })
    return {
        "candidate_count": len(candidates),
        "candidates": candidates,
        "persisted": False,
        "canonical_write_performed": False,
        "provider_calls_performed": False,
        "training_performed": False,
    }


def approve_propositions(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Append approved candidates to the RC1 local noncanonical substrate."""
    existing_records = _read_jsonl(PROPOSITION_LOG)
    existing_ids = {row["proposition_id"] for row in existing_records}
    approved = []
    duplicates = []
    contradictions = []
    for candidate in candidates:
        proposition_id = candidate["proposition_id"]
        if proposition_id in existing_ids:
            duplicates.append(proposition_id)
            continue
        claim = candidate["claim"]
        evidence_id = _stable_id("rc1-evidence", proposition_id + claim)
        record = {
            "proposition_id": proposition_id,
            "claim": claim,
            "normalized": normalize_claim(claim),
            "source": candidate.get("source", "operator_paste"),
            "confidence": candidate.get("confidence", "operator_asserted_unverified"),
            "status": "approved_noncanonical",
            "canonical": False,
            "evidence_id": evidence_id,
            "rollback_supported": True,
            "provider_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
        evidence = {
            "evidence_id": evidence_id,
            "proposition_id": proposition_id,
            "source": "operator_paste",
            "provenance": "local_rc1_operator_console",
            "canonical": False,
        }
        replay = {
            "replay_item_id": _stable_id("rc1-replay", proposition_id),
            "proposition_id": proposition_id,
            "reason": "new_operator_approved_noncanonical_proposition",
            "status": "queued_for_manual_replay_review",
            "scheduler_started": False,
        }
        _append_jsonl(PROPOSITION_LOG, record)
        _append_jsonl(EVIDENCE_LOG, evidence)
        _append_jsonl(REPLAY_LOG, replay)
        approved.append(record)
        new_contradictions = detect_contradictions_for_record(record, existing_records)
        for contradiction in new_contradictions:
            _append_jsonl(CONTRADICTION_LOG, contradiction)
        contradictions.extend(new_contradictions)
        existing_records.append(record)
        existing_ids.add(proposition_id)
    return {
        "approved_count": len(approved),
        "duplicate_count": len(duplicates),
        "contradiction_count": len(contradictions),
        "approved": approved,
        "duplicates": duplicates,
        "contradictions": contradictions,
        "state": build_cognitive_state(),
        "canonical_write_performed": False,
        "provider_calls_performed": False,
        "training_performed": False,
        "scheduler_started": False,
    }


def clear_local_noncanonical_store(confirm_text: str) -> dict[str, Any]:
    """Delete only the RC1 local noncanonical experiment store.

    This is intentionally narrow. It never touches reports, canonical memory,
    training artifacts, provider configuration, or repo source files.
    """
    required = "DELETE_RC1_LOCAL_NONCANONICAL_STORE"
    if str(confirm_text).strip() != required:
        return {
            "cleared": False,
            "required_confirmation": required,
            "reason": "confirmation_phrase_missing_or_incorrect",
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    deleted: list[str] = []
    for path in LOCAL_STORE_LOGS:
        if path.exists():
            path.unlink()
            deleted.append(str(path))
    return {
        "cleared": True,
        "deleted": deleted,
        "state": build_cognitive_state(),
        "local_noncanonical_only": True,
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "recall_mutation_performed": False,
    }


def build_cognitive_state() -> dict[str, Any]:
    propositions = _read_jsonl(PROPOSITION_LOG)
    evidence = _read_jsonl(EVIDENCE_LOG)
    replay = _read_jsonl(REPLAY_LOG)
    contradictions = _read_jsonl(CONTRADICTION_LOG)
    return {
        "corpus_documents": 0,
        "noncanonical_propositions": len(propositions),
        "evidence_links": len(evidence),
        "concepts": len({token.strip(".,:;!?").lower() for row in propositions for token in row.get("claim", "").split() if len(token.strip(".,:;!?")) > 3}),
        "contradictions": len(contradictions),
        "pending_review": 0,
        "replay_queue": len(replay),
        "knowledge_available": bool(propositions),
        "canonical_records": 0,
        "training_records": 0,
    }


def query_noncanonical_substrate(question: str) -> dict[str, Any]:
    tokens = {
        token.strip(".,:;!?").lower()
        for token in question.split()
        if len(token.strip(".,:;!?")) > 3 and token.lower() not in {"what", "know", "about", "does", "tell", "current", "currently"}
    }
    propositions = _read_jsonl(PROPOSITION_LOG)
    contradictions = _read_jsonl(CONTRADICTION_LOG)
    if "contradiction" in question.lower() or "conflict" in question.lower():
        if not contradictions:
            return {
                "matched": True,
                "answer": "No contradictory evidence is currently recorded in the RC1 local substrate.",
                "matches": [],
            }
        lines = ["Contradictions detected in the RC1 local substrate:"]
        for item in contradictions:
            lines.append(f"- Topic: {item['subject']} / {item['predicate']}")
            lines.append(f"  Claim A ({item['claim_a_polarity']}): {item['claim_a']}")
            lines.append(f"  Claim B ({item['claim_b_polarity']}): {item['claim_b']}")
            lines.append("  Operator review recommended.")
        return {
            "matched": True,
            "answer": "\n".join(lines),
            "matches": contradictions,
        }
    matches = []
    for row in propositions:
        claim_tokens = {token.strip(".,:;!?").lower() for token in row.get("claim", "").split()}
        if tokens & claim_tokens:
            matches.append(row)
    if not matches:
        return {
            "matched": False,
            "answer": "No RC1 noncanonical substrate evidence matched this question.",
            "matches": [],
        }
    lines = ["I found approved noncanonical RC1 substrate evidence:"]
    for row in matches:
        lines.append(f"- {row['claim']} (source: {row['source']}; confidence: {row['confidence']}; canonical: {row['canonical']})")
    lines.append("")
    if contradictions:
        lines.append(f"{len(contradictions)} contradiction(s) are currently recorded; ask about contradictions to inspect them.")
    else:
        lines.append("No contradictory evidence is currently recorded in the RC1 local substrate.")
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "matches": matches,
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
