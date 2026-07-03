from __future__ import annotations

import hashlib
import json
from pathlib import Path


DEFAULT_SOURCES = (
    Path("data/runtime_v15i/canonical_memory_trial_records.jsonl"),
    Path("data/runtime_v20c/controlled_general_memory_records.jsonl"),
)

RUNTIME_V20E_FLAGS = {
    "controlled_general_recall_trial_enabled": True,
    "candidate_context_only": True,
    "authoritative_recall_enabled": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def run_controlled_general_recall(query: str, *, max_candidates: int = 5, sources: tuple[Path, ...] = DEFAULT_SOURCES) -> dict[str, object]:
    candidates = _load_candidates(sources)
    scored = sorted((_score(query, item), index, item) for index, item in enumerate(candidates))
    selected = [item for score, index, item in scored if score[0] < 999][:max_candidates]
    for rank, item in enumerate(selected, start=1):
        item["rank"] = rank
        item["candidate_context_only"] = True
        item["authoritative"] = False
        item["truth_claim"] = False
    return {
        "phase": "Runtime V2.0E",
        "query": query,
        "candidates": selected,
        "candidate_count": len(selected),
        "max_candidates": max_candidates,
        "invariant_flags": dict(RUNTIME_V20E_FLAGS),
        "final_recommendation": "PROCEED_PROVIDER_EVIDENCE_LIVE_TRIAL_REVIEW_BRIDGE",
    }


def validate_controlled_general_recall_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["candidate_count"] <= payload["max_candidates"]
        and all(item["candidate_context_only"] is True and item["authoritative"] is False and item["truth_claim"] is False for item in payload["candidates"])
        and flags["controlled_general_recall_trial_enabled"] is True
        and flags["candidate_context_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"controlled_general_recall_trial_enabled", "candidate_context_only"})
    )


def _load_candidates(sources: tuple[Path, ...]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for source in sources:
        if not source.exists():
            continue
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if raw.get("rolled_back") or raw.get("rejected") or raw.get("deferred") or raw.get("rollback_executed"):
                continue
            text = str(raw.get("record_text") or raw.get("proposed_memory_text") or "")
            if not text:
                continue
            results.append({
                "candidate_id": str(raw.get("canonical_record_id") or raw.get("candidate_id") or raw.get("memory_candidate_id") or _stable_id("v20e-candidate", text)),
                "text": text,
                "source_path": str(source),
                "provenance": raw.get("provenance_reference_ids", []),
            })
    return results


def _score(query: str, item: dict[str, object]) -> tuple[int, str]:
    query_terms = {part.lower() for part in query.split() if len(part) > 2}
    text_terms = {part.lower().strip(".,;:!?") for part in str(item["text"]).split()}
    overlap = len(query_terms & text_terms)
    if not query_terms:
        return (0, str(item["candidate_id"]))
    return (999 - overlap if overlap else 999, str(item["candidate_id"]))


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
