from __future__ import annotations

import hashlib
import json
from pathlib import Path

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer


DEFAULT_SOURCES = (
    Path("data/runtime_v15i/canonical_memory_trial_records.jsonl"),
    Path("data/runtime_v20c/controlled_general_memory_records.jsonl"),
    Path("data/runtime_v21b/expanded_controlled_memory_records.jsonl"),
)

RUNTIME_V22B_FLAGS = {
    "controlled_general_recall_expansion_enabled": True,
    "candidate_context_only": True,
    "authoritative_recall_enabled": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def run_controlled_general_recall_expansion(
    query: str,
    *,
    max_candidates: int = 5,
    sources: tuple[Path, ...] = DEFAULT_SOURCES,
    explain_ranking: bool = False,
    include_local_static: bool | None = None,
) -> dict[str, object]:
    candidates = _load_record_candidates(sources)
    if include_local_static is None:
        include_local_static = sources == DEFAULT_SOURCES
    if include_local_static:
        local = route_local_knowledge_answer(query)
    else:
        local = None
    if local and local.matched and local.answer:
        candidates.append({
            "candidate_id": _stable_id("v22b-local", local.topic_id),
            "text": local.answer.answer_text,
            "source_kind": "local_static_knowledge",
            "source_path": "orchestration.runtime.v15_local_knowledge_router",
            "provenance": [local.answer.source_summary],
            "advisory_only": True,
        })
    ranked = _rank(query, candidates)
    selected = ranked[:max_candidates]
    for index, item in enumerate(selected, start=1):
        item["rank"] = index
        item["candidate_context_only"] = True
        item["authoritative"] = False
        item["truth_claim"] = False
    return {
        "phase": "Runtime V2.2B",
        "query": query,
        "source_policy": {
            "allowed_sources": [str(source) for source in sources] + (["local_static_knowledge"] if include_local_static else []),
            "disallowed": ["rejected", "deferred", "rolled_back", "raw_provider_output", "raw_session_text"],
        },
        "candidates": selected,
        "candidate_count": len(selected),
        "max_candidates": max_candidates,
        "ranking_explanation": selected if explain_ranking else [],
        "invariant_flags": dict(RUNTIME_V22B_FLAGS),
        "final_recommendation": "PROCEED_PROVIDER_EVIDENCE_TO_MEMORY_CANDIDATE_CONVERSION",
    }


def validate_recall_expansion_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["candidate_count"] <= payload["max_candidates"]
        and all(item["candidate_context_only"] is True and item["authoritative"] is False and item["truth_claim"] is False for item in payload["candidates"])
        and flags["controlled_general_recall_expansion_enabled"] is True
        and flags["candidate_context_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"controlled_general_recall_expansion_enabled", "candidate_context_only"})
    )


def _load_record_candidates(sources: tuple[Path, ...]) -> list[dict[str, object]]:
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
                "candidate_id": str(raw.get("canonical_record_id") or raw.get("candidate_id") or _stable_id("v22b-record", text)),
                "text": text,
                "source_kind": "controlled_memory_record",
                "source_path": str(source),
                "provenance": raw.get("provenance_reference_ids", []),
                "advisory_only": False,
            })
    return results


def _rank(query: str, candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    query_terms = {part.lower().strip(".,;:!?") for part in query.split() if len(part) > 2}
    ranked: list[tuple[int, str, dict[str, object]]] = []
    for candidate in candidates:
        text_terms = {part.lower().strip(".,;:!?") for part in str(candidate["text"]).split()}
        overlap = len(query_terms & text_terms)
        item = dict(candidate)
        item["ranking_score"] = overlap
        ranked.append((-overlap, str(candidate["candidate_id"]), item))
    return [item for score, candidate_id, item in sorted(ranked) if item["ranking_score"] > 0]


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
