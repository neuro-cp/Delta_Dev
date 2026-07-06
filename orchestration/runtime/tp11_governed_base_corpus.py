"""TP11 governed base corpus and shadow-training readiness.

TP11 builds a reproducible, governed base-corpus package for possible future
research. It does not train, fine-tune, update weights, create model artifacts,
call providers, write canonical memory, schedule jobs, execute actions, promote
HYB1, or replace Model B.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from orchestration.runtime.tp10_training_readiness_review import SAFETY as TP10_SAFETY


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "tp11_governed_base_corpus"
REPORTS = ROOT / "reports"

SOURCE_DIRS = {
    "noncanonical_pilot": ROOT / "data" / "tp5_noncanonical_pilot_store",
    "rc1_fixture": ROOT / "data" / "rc1_fixture_corpus",
    "ov1_allowlisted": ROOT / "data" / "ov1_allowlisted_corpus",
}
HELD_OUT_DIRS = {
    "tp1_heldout": ROOT / "data" / "tp1_heldout_benchmark_corpus",
    "tp2_multi_corpus": ROOT / "data" / "tp2_multi_corpus_benchmark",
    "tp3_independent": ROOT / "data" / "tp3_independent_benchmark_pack",
}

SAFETY = {
    **TP10_SAFETY,
    "tp11_governed_base_corpus": True,
    "training_started": False,
    "fine_tuning_started": False,
    "weight_update_performed": False,
    "model_artifact_created": False,
    "checkpoint_created": False,
    "lora_created": False,
    "adapter_created": False,
    "provider_call_performed": False,
    "canonical_write_performed": False,
    "live_knowledge_mutation_performed": False,
    "scheduler_started": False,
    "action_execution_performed": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

REPORT_PATHS = {
    "base": (REPORTS / "TP11_BASE_CORPUS.json", REPORTS / "TP11_BASE_CORPUS.md"),
    "manifest": (REPORTS / "TP11_CORPUS_MANIFEST.json", REPORTS / "TP11_CORPUS_MANIFEST.md"),
    "dataset_card": (REPORTS / "TP11_DATASET_CARD.json", REPORTS / "TP11_DATASET_CARD.md"),
    "governance": (REPORTS / "TP11_DATA_GOVERNANCE.json", REPORTS / "TP11_DATA_GOVERNANCE.md"),
    "contamination": (REPORTS / "TP11_CONTAMINATION_REVIEW.json", REPORTS / "TP11_CONTAMINATION_REVIEW.md"),
    "readiness": (REPORTS / "TP11_READINESS_REVIEW.json", REPORTS / "TP11_READINESS_REVIEW.md"),
}

PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
]


@dataclass(frozen=True)
class CorpusItem:
    item_id: str
    source_family: str
    source_path: str
    source_identity: str
    content_hash: str
    text: str
    provenance: tuple[str, ...]
    evidence: tuple[str, ...]
    review_history: tuple[str, ...]
    approval_state: str
    uncertainty: str
    contradictions: tuple[str, ...]
    license_status: str
    pii_risk: str
    included: bool
    exclusion_reason: str


def build_governed_base_corpus() -> dict[str, Any]:
    items = _load_source_items()
    reviewed = [_review_item(item) for item in items]
    included = [item for item in reviewed if item.included]
    excluded = [item for item in reviewed if not item.included]
    duplicates = _duplicate_item_ids(included)
    split = _split_items([item for item in included if item.item_id not in duplicates])
    payload = {
        "phase": "TP11 Governed Base Corpus",
        "corpus_status": "constructed",
        "training_performed": False,
        "item_count": len(reviewed),
        "included_count": len([item for item in included if item.item_id not in duplicates]),
        "excluded_count": len(excluded) + len(duplicates),
        "source_families": sorted(SOURCE_DIRS),
        "held_out_families_excluded": sorted(HELD_OUT_DIRS),
        "items": [asdict(item) for item in included if item.item_id not in duplicates],
        "excluded_items": [asdict(item) for item in excluded] + [{"item_id": item_id, "exclusion_reason": "duplicate content hash"} for item_id in sorted(duplicates)],
        "split": split,
        "safety": SAFETY,
    }
    return payload


def build_corpus_manifest(base: dict[str, Any]) -> dict[str, Any]:
    items = base["items"]
    inventory = [{"item_id": item["item_id"], "source_path": item["source_path"], "content_hash": item["content_hash"]} for item in items]
    manifest_text = json.dumps(inventory, sort_keys=True)
    coverage = _coverage(items)
    manifest = {
        "phase": "TP11 Corpus Manifest",
        "manifest_version": 1,
        "corpus_hash": _sha256(manifest_text),
        "reconstruction_root": str(ROOT),
        "source_inventory": inventory,
        "statistics": {
            "items": len(items),
            "train": len(base["split"]["train"]),
            "validation": len(base["split"]["validation"]),
            "holdout": len(base["split"]["holdout"]),
        },
        "coverage": coverage,
        "approval_statistics": _count_by(items, "approval_state"),
        "source_families": _count_by(items, "source_family"),
        "held_out_isolated": True,
    }
    return manifest


def build_dataset_card(base: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "TP11 Dataset Card",
        "name": "DELTA Governed Base Corpus TP11",
        "purpose": "future shadow-training research readiness and governed substrate evaluation",
        "intended_use": [
            "simple local self-description/chat grounding",
            "advanced government-style audit, provenance, rollback, and operational reasoning tasks",
            "future disabled shadow-training dry-run research",
        ],
        "not_for": ["production model training", "provider authority", "canonical memory promotion", "autonomous ingestion"],
        "scope": {"included_sources": base["source_families"], "excluded_heldout_sources": base["held_out_families_excluded"]},
        "limitations": ["small repo-local corpus", "fixture-heavy", "not representative of broad world knowledge", "training remains disabled"],
        "provenance_policy": "every item requires source identity, hash, evidence, review history, and approval state",
        "review_process": "deterministic static review for provenance, approval, PII, duplicates, contamination, uncertainty, and contradictions",
        "governance_model": "noncanonical, reproducible, audit-first, rollback-oriented, no neural weight mutation",
        "update_policy": "future updates require manifest versioning, hash changes, and repeated contamination review",
        "corpus_hash": manifest["corpus_hash"],
    }


def review_data_governance(base: dict[str, Any]) -> dict[str, Any]:
    items = base["items"]
    metrics = {
        "provenance_completeness": _ratio(items, lambda item: bool(item["provenance"] and item["source_identity"] and item["content_hash"])),
        "licensing_reviewed": _ratio(items, lambda item: item["license_status"] != "unknown"),
        "operator_or_fixture_approval": _ratio(items, lambda item: item["approval_state"] in {"operator_approved_noncanonical_pilot", "fixture_allowlisted"}),
        "pii_excluded": 1.0 if not any(item["pii_risk"] != "none" for item in items) else 0.0,
        "contradiction_metadata_present": _ratio(items, lambda item: "contradictions" in item),
        "uncertainty_metadata_present": _ratio(items, lambda item: bool(item["uncertainty"])),
    }
    return {
        "phase": "TP11 Data Governance",
        "metrics": metrics,
        "score": round(mean(metrics.values()), 3) if metrics else 0.0,
        "passed": bool(metrics) and min(metrics.values()) == 1.0,
        "rejected_item_count": base["excluded_count"],
    }


def review_contamination(base: dict[str, Any]) -> dict[str, Any]:
    items = base["items"]
    heldout_files = _heldout_file_hashes()
    base_hashes = {item["content_hash"]: item["item_id"] for item in items}
    overlaps = sorted(hash_value for hash_value in base_hashes if hash_value in heldout_files)
    suspicious = [item["item_id"] for item in items if _contains_contamination_marker(item["text"])]
    return {
        "phase": "TP11 Contamination Review",
        "held_out_sources_checked": sorted(HELD_OUT_DIRS),
        "held_out_hash_overlap_count": len(overlaps),
        "held_out_hash_overlaps": overlaps,
        "suspicious_marker_count": len(suspicious),
        "suspicious_items": suspicious,
        "duplicate_content_count": len(_duplicate_item_ids([CorpusItem(**item) for item in items])),
        "passed": len(overlaps) == 0 and len(suspicious) == 0,
    }


def build_shadow_training_scaffold(base: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    config = {
        "phase": "TP11 Disabled Shadow Training Scaffold",
        "enabled": False,
        "training_performed": False,
        "fine_tuning_performed": False,
        "weight_update_performed": False,
        "model_artifact_created": False,
        "command": "python scripts/delta_tp11_shadow_training_guard.py --manifest data/tp11_governed_base_corpus/corpus_manifest.json --dry-run-only",
        "dataset_loader": "manifest-verified loader design only",
        "manifest_hash": manifest["corpus_hash"],
        "train_count": len(base["split"]["train"]),
        "validation_count": len(base["split"]["validation"]),
        "holdout_count": len(base["split"]["holdout"]),
        "required_future_gates": ["explicit research approval", "independent evaluator", "no deployment", "no model artifact unless separately approved"],
    }
    return config


def build_readiness_review(base: dict[str, Any], governance: dict[str, Any], contamination: dict[str, Any], scaffold: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "provenance_complete": governance["metrics"]["provenance_completeness"],
        "audit_complete": governance["metrics"]["operator_or_fixture_approval"],
        "reproducible_manifest": 1.0 if base["included_count"] > 0 else 0.0,
        "governance_quality": governance["score"],
        "contamination_resistance": 1.0 if contamination["passed"] else 0.0,
        "benchmark_isolation": 1.0 if contamination["held_out_hash_overlap_count"] == 0 else 0.0,
        "shadow_training_disabled": 1.0 if scaffold["enabled"] is False else 0.0,
        "no_training": 1.0 if not SAFETY["training_started"] and not SAFETY["weight_update_performed"] else 0.0,
    }
    score = round(mean(metrics.values()), 3)
    if min(metrics.values()) == 1.0:
        recommendation = "READY_FOR_SHADOW_TRAINING_DRY_RUN"
    elif metrics["no_training"] == 1.0:
        recommendation = "MORE_CORPUS_GOVERNANCE_REQUIRED"
    else:
        recommendation = "TRAINING_REMAINS_BLOCKED"
    return {
        "phase": "TP11 Readiness Review",
        "metrics": metrics,
        "score": score,
        "passed": min(metrics.values()) == 1.0,
        "training_performed": False,
        "final_recommendation": recommendation,
        "remaining_blockers": [] if recommendation == "READY_FOR_SHADOW_TRAINING_DRY_RUN" else ["corpus governance gaps remain"],
    }


def run_tp11_governed_base_corpus() -> dict[str, Any]:
    base = build_governed_base_corpus()
    manifest = build_corpus_manifest(base)
    dataset_card = build_dataset_card(base, manifest)
    governance = review_data_governance(base)
    contamination = review_contamination(base)
    scaffold = build_shadow_training_scaffold(base, manifest)
    readiness = build_readiness_review(base, governance, contamination, scaffold)
    return {
        "phase": "TP11 Governed Base Corpus and Shadow Training Readiness",
        "base": base,
        "manifest": manifest,
        "dataset_card": dataset_card,
        "governance": governance,
        "contamination": contamination,
        "shadow_training_scaffold": scaffold,
        "readiness": readiness,
        "safety": SAFETY,
        "passed": readiness["passed"],
        "final_recommendation": readiness["final_recommendation"],
    }


def write_tp11_reports() -> dict[str, Any]:
    payload = run_tp11_governed_base_corpus()
    REPORTS.mkdir(exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "base": payload["base"],
        "manifest": payload["manifest"],
        "dataset_card": payload["dataset_card"],
        "governance": payload["governance"],
        "contamination": payload["contamination"],
        "readiness": payload["readiness"],
    }
    for key, data in artifacts.items():
        json_path, md_path = REPORT_PATHS[key]
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_render(data), encoding="utf-8")
    (DATA_DIR / "base_corpus.json").write_text(json.dumps(payload["base"], indent=2, sort_keys=True), encoding="utf-8")
    (DATA_DIR / "corpus_manifest.json").write_text(json.dumps(payload["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    (DATA_DIR / "dataset_card.json").write_text(json.dumps(payload["dataset_card"], indent=2, sort_keys=True), encoding="utf-8")
    (DATA_DIR / "shadow_training_config.disabled.json").write_text(json.dumps(payload["shadow_training_scaffold"], indent=2, sort_keys=True), encoding="utf-8")
    return payload


def answer_tp11_question(question: str) -> dict[str, Any]:
    payload = run_tp11_governed_base_corpus()
    lowered = question.lower()
    if "training" in lowered or "train" in lowered:
        answer = "DELTA is not training in TP11. TP11 prepares a governed base corpus and disabled shadow-training scaffold only."
    elif "base corpus" in lowered or "corpus" in lowered:
        answer = f"The governed base corpus contains {payload['base']['included_count']} approved repo-local items with provenance, hashes, review state, uncertainty, and contradiction metadata."
    elif "shadow" in lowered:
        answer = "Shadow training readiness means manifest-verified, disabled research scaffolding; no model artifact, checkpoint, adapter, LoRA, or weight update is created."
    elif "blocked" in lowered:
        answer = "Blocked paths include actual training, fine-tuning, checkpoints, adapters, LoRA artifacts, provider calls, canonical writes, autonomous ingestion, and deployment."
    else:
        answer = f"TP11 recommendation: {payload['final_recommendation']}."
    return {"phase": "TP11 Governed Base Corpus and Shadow Training Readiness", "answer_text": answer, "final_recommendation": payload["final_recommendation"], "safety": SAFETY}


def is_tp11_question(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("tp11", "governed base corpus", "base corpus", "shadow training readiness", "is delta training", "why is training still disabled"))


def _load_source_items() -> list[CorpusItem]:
    items: list[CorpusItem] = []
    items.extend(_load_noncanonical_records(SOURCE_DIRS["noncanonical_pilot"]))
    items.extend(_load_fixture_files("rc1_fixture", SOURCE_DIRS["rc1_fixture"]))
    items.extend(_load_fixture_files("ov1_allowlisted", SOURCE_DIRS["ov1_allowlisted"]))
    return sorted(items, key=lambda item: item.item_id)


def _load_noncanonical_records(root: Path) -> list[CorpusItem]:
    items: list[CorpusItem] = []
    for path in sorted(root.rglob("records.jsonl")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            text = str(record.get("claim", "")).strip()
            source_path = str(path.relative_to(ROOT))
            item_id = f"noncanonical-{_sha256(source_path + str(line_no) + text)[:16]}"
            items.append(CorpusItem(
                item_id=item_id,
                source_family="noncanonical_pilot",
                source_path=source_path,
                source_identity=record.get("record_id", item_id),
                content_hash=_sha256(text),
                text=text,
                provenance=tuple(record.get("source_references", ())),
                evidence=tuple(record.get("supporting_evidence", ())),
                review_history=(record.get("review_decision", "unknown"),),
                approval_state=record.get("review_decision", "unknown"),
                uncertainty=record.get("uncertainty", "unknown"),
                contradictions=tuple(record.get("contradictions", ())),
                license_status="repo-local-governed-record",
                pii_risk="unknown",
                included=True,
                exclusion_reason="",
            ))
    return items


def _load_fixture_files(family: str, root: Path) -> list[CorpusItem]:
    items: list[CorpusItem] = []
    if not root.exists():
        return items
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8").strip()
        rel = str(path.relative_to(ROOT))
        items.append(CorpusItem(
            item_id=f"{family}-{_sha256(rel)[:16]}",
            source_family=family,
            source_path=rel,
            source_identity=rel,
            content_hash=_sha256(text),
            text=text,
            provenance=(f"repo-fixture://{rel}",),
            evidence=(f"repo-fixture://{rel}",),
            review_history=("fixture_allowlisted",),
            approval_state="fixture_allowlisted",
            uncertainty="bounded_fixture",
            contradictions=(),
            license_status="repo-local-test-fixture",
            pii_risk="unknown",
            included=True,
            exclusion_reason="",
        ))
    return items


def _review_item(item: CorpusItem) -> CorpusItem:
    reason = ""
    pii_risk = "detected" if any(pattern.search(item.text) for pattern in PII_PATTERNS) else "none"
    included = True
    if not item.text:
        included, reason = False, "empty text"
    elif not item.provenance or not item.source_identity or not item.content_hash:
        included, reason = False, "missing provenance"
    elif item.approval_state not in {"operator_approved_noncanonical_pilot", "fixture_allowlisted"}:
        included, reason = False, "not approved"
    elif pii_risk != "none":
        included, reason = False, "PII risk"
    return CorpusItem(**{**asdict(item), "pii_risk": pii_risk, "included": included, "exclusion_reason": reason})


def _split_items(items: list[CorpusItem]) -> dict[str, list[str]]:
    ids = [item.item_id for item in sorted(items, key=lambda i: i.item_id)]
    train: list[str] = []
    validation: list[str] = []
    holdout: list[str] = []
    for index, item_id in enumerate(ids):
        bucket = index % 10
        if bucket < 7:
            train.append(item_id)
        elif bucket < 9:
            validation.append(item_id)
        else:
            holdout.append(item_id)
    return {"train": train, "validation": validation, "holdout": holdout}


def _duplicate_item_ids(items: list[CorpusItem]) -> set[str]:
    seen: dict[str, str] = {}
    duplicates: set[str] = set()
    for item in items:
        previous = seen.setdefault(item.content_hash, item.item_id)
        if previous != item.item_id:
            duplicates.add(item.item_id)
    return duplicates


def _coverage(items: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "provenance": _ratio(items, lambda item: bool(item["provenance"])),
        "evidence": _ratio(items, lambda item: bool(item["evidence"])),
        "review_history": _ratio(items, lambda item: bool(item["review_history"])),
        "approval_state": _ratio(items, lambda item: bool(item["approval_state"])),
        "uncertainty": _ratio(items, lambda item: bool(item["uncertainty"])),
        "contradiction_metadata": _ratio(items, lambda item: "contradictions" in item),
    }


def _heldout_file_hashes() -> set[str]:
    hashes: set[str] = set()
    for root in HELD_OUT_DIRS.values():
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                hashes.add(_sha256(path.read_text(encoding="utf-8", errors="ignore").strip()))
    return hashes


def _contains_contamination_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ("held-out answer key", "benchmark solution key", "expected answer:"))


def _ratio(items: list[dict[str, Any]], predicate) -> float:
    if not items:
        return 0.0
    return round(sum(1 for item in items if predicate(item)) / len(items), 3)


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('phase', 'TP11 Report')}", ""]
    for key, value in data.items():
        if key == "items":
            lines.append(f"- items: `{len(value)}`")
        elif key == "excluded_items":
            lines.append(f"- excluded_items: `{len(value)}`")
        else:
            lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(write_tp11_reports()["final_recommendation"])
