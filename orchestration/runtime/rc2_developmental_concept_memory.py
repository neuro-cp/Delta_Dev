"""RC2 developmental concept memory.

This module implements the first concept-shaped, noncanonical learning loop
behind DELTA's conversational UI. It does not train models, mutate canonical
memory, call providers, start schedulers, or execute actions.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "rc2_developmental_memory"
CONVERSATION_MEMORY_LOG = DATA / "conversation_memory.jsonl"
PERSONAL_MEMORY_LOG = DATA / "personal_memory.jsonl"
KNOWLEDGE_MEMORY_LOG = DATA / "knowledge_concepts.jsonl"
CONCEPT_EDGE_LOG = DATA / "concept_edges.jsonl"
CONCEPT_REPLAY_LOG = DATA / "concept_replay_queue.jsonl"
CONCEPT_CONTRADICTION_LOG = DATA / "concept_contradictions.jsonl"

RC2_MEMORY_FLAGS = {
    "developmental_concept_memory_enabled": True,
    "conversation_memory_session_only": True,
    "personal_memory_noncanonical": True,
    "knowledge_memory_noncanonical": True,
    "canonical_write_performed": False,
    "training_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_write_performed": False,
    "scheduler_started": False,
}

STORE_BY_TYPE = {
    "conversation": CONVERSATION_MEMORY_LOG,
    "personal": PERSONAL_MEMORY_LOG,
    "knowledge": KNOWLEDGE_MEMORY_LOG,
}

_APPROVED_CONCEPT_CACHE: dict[str, Any] = {"signature": None, "records": []}
_CONCEPT_INDEX_CACHE: dict[str, Any] = {"signature": None, "index": None}
_RANK_RESULT_CACHE: dict[str, Any] = {"signature": None, "results": {}}


def _using_default_memory_store() -> bool:
    default_data = ROOT / "data" / "rc2_developmental_memory"
    default_stores = {
        "conversation": default_data / "conversation_memory.jsonl",
        "personal": default_data / "personal_memory.jsonl",
        "knowledge": default_data / "knowledge_concepts.jsonl",
    }
    return all(Path(STORE_BY_TYPE.get(key, "")) == path for key, path in default_stores.items())

DOMAIN_ALIASES = {
    "law": "law government basics",
    "legal": "law government basics",
    "government": "law government basics",
    "physics": "basic physics",
    "science": "basic physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "health": "medicine health general",
    "medicine": "medicine health general",
    "nutrition": "nutrition",
    "psychology": "psychology",
    "philosophy": "philosophy",
    "logic": "logic",
    "math": "mathematics",
    "mathematics": "mathematics",
    "programming": "programming",
    "coding": "programming",
    "software": "software architecture",
    "business": "business",
    "finance": "finance",
    "history": "history",
    "geography": "geography",
    "engineering": "engineering",
    "materials": "materials science",
    "metallurgy": "materials science",
    "energy": "energy",
    "gardening": "agriculture gardening",
    "agriculture": "agriculture gardening",
    "mechanics": "vehicles mechanics",
    "vehicles": "vehicles mechanics",
    "home repair": "home repair",
    "communication": "social communication",
    "productivity": "planning productivity",
    "planning": "planning productivity",
    "delta": "DELTA architecture itself",
}

RELATED_QUERY_HINTS = {
    "photosynthesis": ("cellular respiration", "energy storage", "carbon cycle"),
    "respiration": ("photosynthesis", "energy storage", "carbon cycle"),
    "atp": ("energy storage", "cellular respiration", "biology"),
    "energy storage": ("atp", "battery", "thermal storage", "photosynthesis"),
    "homeostasis": ("feedback loops", "biology", "regulation"),
    "gravity": ("orbital motion", "force", "motion", "basic physics"),
    "orbital motion": ("gravity", "motion", "force"),
    "pressure": ("fluid flow", "engineering", "basic physics"),
    "fluid flow": ("pressure", "engineering", "mechanics"),
    "thermodynamics": ("engines", "heat", "energy", "engineering"),
    "engines": ("thermodynamics", "energy", "mechanics"),
    "inflation": ("interest rates", "finance", "money"),
    "interest rates": ("inflation", "finance", "compound interest"),
    "risk": ("asset allocation", "finance", "risk management"),
    "asset allocation": ("risk", "finance", "investment"),
    "compound interest": ("long-term investing", "interest rates", "finance"),
    "long-term investing": ("compound interest", "asset allocation", "finance"),
    "memory": ("human memory", "delta memory", "consolidation", "noncanonical memory"),
    "human memory": ("memory consolidation", "psychology", "learning"),
    "delta memory": ("noncanonical memory", "canonical memory", "memory consolidation"),
    "noncanonical memory": ("canonical memory", "memory consolidation", "delta memory"),
    "operator approval": ("learning", "noncanonical memory", "governance"),
    "planning": ("feedback loops", "software architecture", "productivity"),
    "feedback loops": ("planning", "software architecture", "systems"),
    "software architecture": ("planning", "modularity", "feedback loops"),
    "access control": ("user permissions", "authorization", "software architecture"),
    "user permissions": ("access control", "authorization", "software architecture"),
    "adapter patterns": ("system integration", "adapter pattern", "software architecture"),
    "adapter pattern": ("system integration", "software architecture", "api boundaries"),
    "system integration": ("adapter pattern", "api boundaries", "software architecture"),
    "law": ("governance", "government", "evidence"),
    "governance": ("law", "operator approval", "decision-making"),
    "evidence": ("decision making", "law", "governance"),
    "decision-making": ("evidence", "risk", "planning"),
    "decision making": ("evidence", "risk", "planning"),
    "communication": ("conflict resolution", "active listening", "social communication"),
    "conflict resolution": ("communication", "active listening", "psychology"),
    "insulation": ("energy efficiency", "home repair", "thermal storage"),
    "energy efficiency": ("insulation", "energy", "home repair"),
    "soil quality": ("plant growth", "agriculture", "photosynthesis"),
    "plant growth": ("soil quality", "photosynthesis", "agriculture"),
    "maintenance": ("mechanical reliability", "vehicles mechanics", "planning"),
    "mechanical reliability": ("maintenance", "vehicles mechanics", "engineering"),
}


def discover_memory_store_separation() -> dict[str, Any]:
    return {
        "conversation_memory": {
            "scope": "session_level_context",
            "default_persistence": "in_memory_ui_history",
            "optional_log": str(CONVERSATION_MEMORY_LOG),
        },
        "personal_memory": {
            "scope": "user_project_preferences_and_personal_facts",
            "store": str(PERSONAL_MEMORY_LOG),
            "canonical": False,
        },
        "knowledge_memory": {
            "scope": "general_reusable_concepts_facts_explanations_relationships",
            "store": str(KNOWLEDGE_MEMORY_LOG),
            "canonical": False,
        },
        "flags": dict(RC2_MEMORY_FLAGS),
    }


def extract_candidate_concept(
    *,
    question: str,
    answer: str,
    source_model_lane: dict[str, Any],
    source_type: str = "local_model_lane",
    memory_type: str | None = None,
) -> dict[str, Any]:
    clean_question = _clean(question)
    clean_answer = _clean(answer)
    selected_memory = memory_type or infer_memory_type(clean_question)
    concept_name = infer_concept_name(clean_question, clean_answer)
    propositions = _sentence_propositions(clean_answer)
    related = infer_related_concepts(concept_name, clean_question, clean_answer)
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    source_model_id = str(source_model_lane.get("selected_model") or "not_executed")
    source_lane = str(source_model_lane.get("lane") or "general")
    raw_id = "|".join([concept_name, clean_question, clean_answer, source_lane, source_model_id])
    digest = _digest(raw_id)
    concept_id = f"rc2-concept-{digest}"
    return {
        "concept_id": concept_id,
        "concept_name": concept_name,
        "concept_type": infer_concept_type(clean_question, clean_answer),
        "short_definition": infer_short_definition(concept_name, propositions, clean_answer),
        "propositions": propositions,
        "related_concepts": related,
        "explains": [clean_question] if clean_question else [],
        "examples": infer_examples(clean_question, clean_answer),
        "misconceptions": infer_misconceptions(clean_answer),
        "uncertainty": infer_uncertainty(clean_answer, source_model_lane),
        "source_answer_id": f"rc2-answer-{digest}",
        "source_question": clean_question,
        "source_model_lane": source_lane,
        "source_model_id": source_model_id,
        "source_type": source_type,
        "approval_status": "pending_operator_approval",
        "memory_type": selected_memory,
        "rollback_handle": f"rollback-rc2-concept-{digest}",
        "created_at": created_at,
        "canonical": False,
        "training_performed": False,
        "provider_calls_performed": False,
    }


def approve_candidate_concept(candidate: dict[str, Any], *, approval_text: str = "Keep this concept") -> dict[str, Any]:
    if _normalize_approval(approval_text) not in {"keep this concept", "that was useful remember the concept", "remember the concept"}:
        return {
            "approved": False,
            "reason": "approval_text_not_accepted",
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    memory_type = str(candidate.get("memory_type") or "knowledge")
    if memory_type not in STORE_BY_TYPE:
        memory_type = "knowledge"
    store = STORE_BY_TYPE[memory_type]
    existing = _read_jsonl(store)
    duplicate = find_duplicate(candidate, existing)
    pre_contradictions = detect_concept_contradictions(candidate, existing)
    if duplicate and not pre_contradictions:
        if candidate.get("enrichment_of_concept_id") == duplicate.get("concept_id") or candidate.get("operator_edited"):
            merged = merge_concept_enrichment(duplicate, candidate)
            updated = [merged if row.get("concept_id") == duplicate.get("concept_id") else row for row in existing]
            _write_jsonl(store, updated)
            replay = {
                "replay_item_id": f"rc2-concept-replay-{_digest(merged['concept_id'] + merged.get('updated_at', ''))}",
                "concept_id": merged["concept_id"],
                "memory_type": memory_type,
                "reason": "operator_approved_developmental_concept_enrichment",
                "status": "queued_for_manual_replay_review",
                "scheduler_started": False,
            }
            _append_jsonl(CONCEPT_REPLAY_LOG, replay)
            return {
                "approved": True,
                "stored_concept": merged,
                "memory_type": memory_type,
                "duplicate": False,
                "enriched_existing": True,
                "enriched_concept_id": duplicate["concept_id"],
                "contradictions": [],
                "edges": [],
                "replay": replay,
                "canonical_write_performed": False,
                "training_performed": False,
                "provider_calls_performed": False,
                "rollback_supported": True,
            }
        return {
            "approved": False,
            "duplicate": True,
            "duplicate_concept_id": duplicate["concept_id"],
            "stored_concept": duplicate,
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    record = {
        **candidate,
        "approval_status": "approved_noncanonical",
        "approved_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "canonical": False,
    }
    contradictions = detect_concept_contradictions(record, existing)
    _append_jsonl(store, record)
    edges = concept_edges(record, existing)
    for edge in edges:
        _append_jsonl(CONCEPT_EDGE_LOG, edge)
    for contradiction in contradictions:
        _append_jsonl(CONCEPT_CONTRADICTION_LOG, contradiction)
    replay = {
        "replay_item_id": f"rc2-concept-replay-{_digest(record['concept_id'])}",
        "concept_id": record["concept_id"],
        "memory_type": memory_type,
        "reason": "new_operator_approved_developmental_concept",
        "status": "queued_for_manual_replay_review",
        "scheduler_started": False,
    }
    _append_jsonl(CONCEPT_REPLAY_LOG, replay)
    return {
        "approved": True,
        "stored_concept": record,
        "memory_type": memory_type,
        "duplicate": False,
        "contradictions": contradictions,
        "edges": edges,
        "replay": replay,
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "rollback_supported": True,
    }


def merge_concept_enrichment(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    candidate_definition = str(candidate.get("short_definition") or "").strip()
    existing_definition = str(existing.get("short_definition") or "").strip()
    if candidate_definition and candidate_definition != existing_definition:
        if existing_definition and candidate_definition.lower() not in existing_definition.lower():
            merged["short_definition"] = f"{existing_definition} {candidate_definition}".strip()
        else:
            merged["short_definition"] = candidate_definition or existing_definition

    merged["propositions"] = _merge_unique_lines(existing.get("propositions", []), candidate.get("propositions", []))
    merged["related_concepts"] = _merge_unique_lines(existing.get("related_concepts", []), candidate.get("related_concepts", []))
    merged["examples"] = _merge_unique_lines(existing.get("examples", []), candidate.get("examples", []))
    merged["misconceptions"] = _merge_unique_lines(existing.get("misconceptions", []), candidate.get("misconceptions", []))
    merged["explains"] = _merge_unique_lines(existing.get("explains", []), candidate.get("explains", []))
    merged["operator_notes"] = "\n".join(_merge_unique_lines([existing.get("operator_notes", "")], [candidate.get("operator_notes", "")])).strip()
    merged["approval_status"] = "approved_noncanonical"
    merged["canonical"] = False
    merged["training_performed"] = False
    merged["provider_calls_performed"] = False
    merged["enrichment_count"] = int(existing.get("enrichment_count") or 0) + 1
    merged["updated_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    merged["last_enrichment_source_answer_id"] = candidate.get("source_answer_id")
    return merged


def load_approved_concepts() -> list[dict[str, Any]]:
    signature = _store_signature(STORE_BY_TYPE)
    if _APPROVED_CONCEPT_CACHE["signature"] == signature:
        return [dict(row) for row in _APPROVED_CONCEPT_CACHE["records"]]
    records = []
    for memory_type, path in STORE_BY_TYPE.items():
        for row in _read_jsonl(path):
            if row.get("approval_status") == "approved_noncanonical" and row.get("canonical") is False:
                records.append({**row, "_store_memory_type": memory_type})
    _APPROVED_CONCEPT_CACHE["signature"] = signature
    _APPROVED_CONCEPT_CACHE["records"] = [dict(row) for row in records]
    return records


def clear_runtime_concept_caches() -> None:
    _APPROVED_CONCEPT_CACHE["signature"] = None
    _APPROVED_CONCEPT_CACHE["records"] = []
    _CONCEPT_INDEX_CACHE["signature"] = None
    _CONCEPT_INDEX_CACHE["index"] = None
    _RANK_RESULT_CACHE["signature"] = None
    _RANK_RESULT_CACHE["results"] = {}


def build_runtime_concept_index() -> dict[str, Any]:
    signature = _store_signature(STORE_BY_TYPE)
    if _CONCEPT_INDEX_CACHE["signature"] == signature and _CONCEPT_INDEX_CACHE["index"] is not None:
        return _CONCEPT_INDEX_CACHE["index"]
    concepts = load_approved_concepts()
    by_id = {}
    by_domain: dict[str, list[dict[str, Any]]] = {}
    token_index: dict[str, list[dict[str, Any]]] = {}
    normalized_name = {}
    for row in concepts:
        concept_id = str(row.get("concept_id") or "")
        if concept_id:
            by_id[concept_id] = row
        normalized_name[_normalize_compact(row.get("concept_name"))] = row
        domain = str(row.get("domain") or "").lower().strip()
        if domain:
            by_domain.setdefault(domain, []).append(row)
        text = " ".join([
            str(row.get("concept_name") or ""),
            str(row.get("domain") or ""),
            str(row.get("short_definition") or ""),
            " ".join(str(item) for item in row.get("propositions", [])),
            " ".join(str(item) for item in row.get("related_concepts", [])),
            " ".join(str(item) for item in row.get("keywords", [])),
            str(row.get("source_question") or ""),
        ])
        for token in _meaningful_tokens(text):
            token_index.setdefault(token, []).append(row)
    index = {
        "signature": signature,
        "concepts": concepts,
        "by_id": by_id,
        "by_domain": by_domain,
        "token_index": token_index,
        "normalized_name": normalized_name,
    }
    _CONCEPT_INDEX_CACHE["signature"] = signature
    _CONCEPT_INDEX_CACHE["index"] = index
    return index


def retrieval_query_profile(question: str) -> dict[str, Any]:
    normalized = _normalize_text(question).strip()
    tokens = _meaningful_tokens(question)
    domains = {
        domain
        for alias, domain in DOMAIN_ALIASES.items()
        if _contains_phrase(normalized, alias)
    }
    aliases = {alias for alias in DOMAIN_ALIASES if _contains_phrase(normalized, alias)}
    phrases = _query_phrases(normalized)
    for token in list(tokens):
        if token in RELATED_QUERY_HINTS:
            aliases.add(token)
            phrases.add(token)
    return {
        "raw": question,
        "normalized": normalized,
        "tokens": tokens,
        "key_tokens": _query_key_tokens(normalized),
        "domains": domains,
        "aliases": aliases,
        "phrases": phrases,
    }


def rank_approved_concepts(
    question: str,
    *,
    limit: int = 5,
    domain: str | None = None,
    exclude_concept_names: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict[str, Any]:
    profile = retrieval_query_profile(question)
    excluded = {_normalize_compact(name) for name in (exclude_concept_names or [])}
    wanted_domain = str(domain or "").lower().strip()
    blocked_domains = {str(item).lower().strip() for item in (exclude_domains or []) if str(item).strip()}
    exact_title_matches = _exact_base_title_matches(profile, wanted_domain=wanted_domain, blocked_domains=blocked_domains, excluded=excluded)
    if exact_title_matches:
        matches = []
        for row in exact_title_matches[:max(1, limit)]:
            score = score_concept_for_query(row, profile, forced_domain=domain)
            score["score"] = round(float(score.get("score") or 0.0) + 120.0, 4)
            components = dict(score.get("components") or {})
            components["exact_base_title"] = 120.0
            score["components"] = components
            reasons = set(score.get("reasons") or [])
            reasons.add("exact_base_title_match")
            score["reasons"] = sorted(reasons)
            score["relevance_gate_passed"] = True
            matches.append({**row, "_retrieval_score": score})
        return {
            "matched": True,
            "matches": matches,
            "query_profile": profile,
            "duplicate_suppression_count": 0,
            "retrieval_precision_estimate": 1.0,
            "candidate_pool_size": len(exact_title_matches),
        }
    if not blocked_domains and _using_default_memory_store():
        try:
            from orchestration.runtime.rc2_sqlite_substrate import backend_health, search_concepts_sqlite

            health = backend_health()
            if health.get("sqlite_available"):
                return search_concepts_sqlite(
                    question,
                    domain=domain,
                    limit=limit,
                    exclude_concept_names=exclude_concept_names,
                )
        except Exception:
            pass
    signature = _store_signature(STORE_BY_TYPE)
    cache_key = json.dumps({
        "question": profile["normalized"],
        "limit": limit,
        "domain": wanted_domain,
        "excluded": sorted(excluded),
        "blocked_domains": sorted(blocked_domains),
    }, sort_keys=True)
    if _RANK_RESULT_CACHE["signature"] != signature:
        _RANK_RESULT_CACHE["signature"] = signature
        _RANK_RESULT_CACHE["results"] = {}
    if cache_key in _RANK_RESULT_CACHE["results"]:
        return _copy_rank_result(_RANK_RESULT_CACHE["results"][cache_key])
    scored = []
    duplicate_suppression_count = 0
    seen_names = set()
    candidate_rows = _candidate_concepts_for_profile(
        profile,
        wanted_domain=wanted_domain,
        blocked_domains=blocked_domains,
        minimum=max(limit * 8, 25),
    )
    for row in candidate_rows:
        name_key = _normalize_compact(row.get("concept_name"))
        if name_key in excluded:
            continue
        if wanted_domain and str(row.get("domain") or "").lower().strip() != wanted_domain:
            continue
        if blocked_domains and str(row.get("domain") or "").lower().strip() in blocked_domains:
            continue
        if name_key in seen_names:
            duplicate_suppression_count += 1
            continue
        seen_names.add(name_key)
        score = score_concept_for_query(row, profile, forced_domain=domain)
        if score["score"] > 0 and score.get("relevance_gate_passed"):
            scored.append((score, row))
    scored.sort(key=lambda item: (
        -item[0]["score"],
        -float(item[1].get("quality_score") or 0.0),
        str(item[1].get("concept_name") or ""),
    ))
    matches = []
    for score, row in scored[:max(1, limit)]:
        matches.append({**row, "_retrieval_score": score})
    result = {
        "matched": bool(matches),
        "matches": matches,
        "query_profile": profile,
        "duplicate_suppression_count": duplicate_suppression_count,
        "retrieval_precision_estimate": _retrieval_precision_estimate(matches, profile),
        "candidate_pool_size": len(candidate_rows),
    }
    _RANK_RESULT_CACHE["results"][cache_key] = _copy_rank_result(result)
    return result


def _exact_base_title_matches(
    profile: dict[str, Any],
    *,
    wanted_domain: str,
    blocked_domains: set[str],
    excluded: set[str],
) -> list[dict[str, Any]]:
    query = _normalize_compact(profile.get("normalized") or profile.get("raw") or "")
    if len(_meaningful_tokens(query)) < 2 and len(query.split()) < 2:
        return []
    matches = []
    seen = set()
    for row in load_approved_concepts():
        domain = str(row.get("domain") or "").lower().strip()
        name_key = _normalize_compact(row.get("concept_name"))
        if name_key in excluded or name_key in seen:
            continue
        if wanted_domain and domain != wanted_domain:
            continue
        if blocked_domains and domain in blocked_domains:
            continue
        if _base_concept_title(row.get("concept_name")) == query:
            seen.add(name_key)
            matches.append(row)
    matches.sort(key=lambda row: (
        -float(row.get("quality_score") or 0.0),
        str(row.get("domain") or ""),
        str(row.get("concept_name") or ""),
    ))
    return matches


def _base_concept_title(name: object) -> str:
    without_parenthetical = re.sub(r"\([^)]*\)", " ", str(name or ""))
    return _normalize_compact(without_parenthetical)


def score_concept_for_query(row: dict[str, Any], profile: dict[str, Any], *, forced_domain: str | None = None) -> dict[str, Any]:
    name = str(row.get("concept_name") or "")
    domain = str(row.get("domain") or "").lower().strip()
    definition = str(row.get("short_definition") or "")
    propositions = " ".join(str(item) for item in row.get("propositions", []))
    related = " ".join(str(item) for item in row.get("related_concepts", []))
    source_question = str(row.get("source_question") or "")
    name_norm = _normalize_text(name).strip()
    domain_norm = _normalize_text(domain).strip()
    definition_norm = _normalize_text(definition).strip()
    propositions_norm = _normalize_text(propositions).strip()
    related_norm = _normalize_text(related).strip()
    source_norm = _normalize_text(source_question).strip()
    text_norm = _normalize_text(" ".join([name, domain, definition, propositions, related, source_question])).strip()
    name_tokens = _meaningful_tokens(name)
    definition_tokens = _meaningful_tokens(definition)
    proposition_tokens = _meaningful_tokens(propositions)
    related_tokens = _meaningful_tokens(related)
    source_tokens = _meaningful_tokens(source_question)
    text_tokens = name_tokens | definition_tokens | proposition_tokens | related_tokens | source_tokens | _meaningful_tokens(domain)
    tokens = set(profile["tokens"])
    query_key_tokens = set(profile.get("key_tokens") or tokens)
    score = 0.0
    reasons = []
    components = {
        "concept_name": 0.0,
        "propositions": 0.0,
        "related_concepts": 0.0,
        "domain": 0.0,
        "source_question": 0.0,
        "definition": 0.0,
        "quality": 0.0,
    }
    if forced_domain and domain == str(forced_domain).lower().strip():
        components["domain"] += 9.0
        reasons.append("forced_domain_match")
    if domain and domain in profile["domains"]:
        components["domain"] += 8.0
        reasons.append("domain_alias_match")
    for phrase in profile["phrases"] | profile["aliases"]:
        if not phrase:
            continue
        if _contains_phrase(name_norm, phrase):
            components["concept_name"] += 40.0 if " " in phrase else 12.0
            reasons.append(f"name_phrase:{phrase}")
        elif _contains_phrase(domain_norm, phrase):
            components["domain"] += 10.0
            reasons.append(f"domain_phrase:{phrase}")
        elif _contains_phrase(propositions_norm, phrase):
            components["propositions"] += 25.0 if " " in phrase else 5.0
            reasons.append(f"proposition_phrase:{phrase}")
        elif _contains_phrase(related_norm, phrase):
            components["related_concepts"] += 15.0 if " " in phrase else 4.0
            reasons.append(f"related_phrase:{phrase}")
        elif _contains_phrase(definition_norm, phrase):
            components["definition"] += 8.0 if " " in phrase else 2.0
            reasons.append(f"definition_phrase:{phrase}")
        elif _contains_phrase(source_norm, phrase):
            components["source_question"] += 5.0
            reasons.append(f"source_phrase:{phrase}")
    overlap = tokens & text_tokens
    name_overlap = tokens & name_tokens
    proposition_overlap = tokens & proposition_tokens
    related_overlap = tokens & related_tokens
    definition_overlap = tokens & definition_tokens
    source_overlap = tokens & source_tokens
    if name_overlap:
        components["concept_name"] += 6.0 * len(name_overlap)
        reasons.append("name_token_overlap")
    if proposition_overlap:
        components["propositions"] += 3.0 * len(proposition_overlap)
        reasons.append("proposition_token_overlap")
    if related_overlap:
        components["related_concepts"] += 2.5 * len(related_overlap)
        reasons.append("related_token_overlap")
    if definition_overlap:
        components["definition"] += 1.5 * len(definition_overlap)
        reasons.append("definition_token_overlap")
    if source_overlap:
        components["source_question"] += 1.0 * len(source_overlap)
        reasons.append("source_token_overlap")
    gate_passed = _relevance_gate_passed(
        query_key_tokens=query_key_tokens,
        name_overlap=name_overlap,
        overlap=overlap,
        reasons=reasons,
        phrase_count=len(profile["phrases"] | profile["aliases"]),
    )
    score = sum(components.values())
    if score > 0:
        components["quality"] = min(float(row.get("quality_score") or 0.0), 1.0)
        score += components["quality"]
    return {
        "score": round(score, 4),
        "components": {key: round(value, 4) for key, value in components.items() if value},
        "reasons": sorted(set(reasons)),
        "overlap": sorted(overlap),
        "key_token_overlap": sorted(query_key_tokens & text_tokens),
        "domain": domain,
        "relevance_gate_passed": gate_passed,
    }


def _candidate_concepts_for_profile(
    profile: dict[str, Any],
    *,
    wanted_domain: str,
    blocked_domains: set[str],
    minimum: int,
) -> list[dict[str, Any]]:
    index = build_runtime_concept_index()
    candidates_by_id: dict[str, dict[str, Any]] = {}
    if wanted_domain:
        for row in index["by_domain"].get(wanted_domain, []):
            candidates_by_id[str(row.get("concept_id"))] = row
    for domain in profile.get("domains", set()):
        for row in index["by_domain"].get(str(domain).lower().strip(), []):
            candidates_by_id[str(row.get("concept_id"))] = row
    query_terms = set(profile.get("tokens") or set()) | set(profile.get("key_tokens") or set())
    for phrase in set(profile.get("phrases") or set()) | set(profile.get("aliases") or set()):
        query_terms.update(_meaningful_tokens(phrase))
    for token in query_terms:
        for row in index["token_index"].get(token, []):
            candidates_by_id[str(row.get("concept_id"))] = row
    candidates = [
        row
        for row in candidates_by_id.values()
        if not blocked_domains or str(row.get("domain") or "").lower().strip() not in blocked_domains
    ]
    if len(candidates) < minimum:
        fallback = []
        for row in index["concepts"]:
            domain = str(row.get("domain") or "").lower().strip()
            if wanted_domain and domain != wanted_domain:
                continue
            if blocked_domains and domain in blocked_domains:
                continue
            fallback.append(row)
        return fallback
    return candidates


def _copy_rank_result(result: dict[str, Any]) -> dict[str, Any]:
    copied = dict(result)
    copied["matches"] = [dict(row) for row in result.get("matches", [])]
    copied["query_profile"] = dict(result.get("query_profile", {}))
    copied["scores"] = [dict(row) for row in result.get("scores", [])] if "scores" in result else copied.get("scores", [])
    return copied


def _recall_search_query(question: str) -> str:
    normalized = _normalize_text(question).strip()
    patterns = [
        r"^what\s+(?:is|are)\s+the\s+key\s+points\s+about\s+(.+?)$",
        r"^what\s+(?:is|are)\s+(.+?)(?:\s+use\s+your\s+local\s+substrate\s+if\s+available)?$",
        r"^explain\s+(.+?)\s+in\s+one\s+useful\s+paragraph(?:\s+from\s+local\s+memory)?$",
        r"^explain\s+(.+?)\s+from\s+local\s+memory$",
        r"^tell\s+me\s+about\s+(.+?)$",
        r"^tell\s+me\s+(.+?)$",
        r"^what\s+do\s+you\s+know\s+about\s+(.+?)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        candidate = match.group(1)
        candidate = re.sub(r"\b(use|using|only|approved|local|substrate|memory|concepts?)\b", " ", candidate)
        candidate = " ".join(candidate.strip(" ?.!\\/").split())
        if candidate:
            return candidate
    return question


def query_approved_concepts(question: str) -> dict[str, Any]:
    search_query = _recall_search_query(question)
    ranked = rank_approved_concepts(search_query, limit=5)
    if not ranked["matched"]:
        return {"matched": False, "answer": "", "matches": [], "scores": []}
    matches = ranked["matches"]
    first = matches[0]
    lines = [
        f"I know about `{first['concept_name']}` from noncanonical reviewed memory.",
        first["short_definition"],
    ]
    propositions = first.get("propositions", [])[:3]
    if propositions:
        lines.append("")
        lines.append("Key points:")
        lines.extend(f"- {item}" for item in propositions)
    contradictions = [
        item for item in _read_jsonl(CONCEPT_CONTRADICTION_LOG)
        if first["concept_id"] in {item.get("concept_a_id"), item.get("concept_b_id")}
    ]
    if contradictions:
        lines.append("")
        lines.append(f"Note: {len(contradictions)} possible contradiction(s) are linked to this concept.")
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "matches": matches,
        "scores": [item.get("_retrieval_score", {}) for item in matches],
        "retrieval_precision_estimate": ranked["retrieval_precision_estimate"],
        "duplicate_suppression_count": ranked["duplicate_suppression_count"],
        "search_query": search_query,
    }


def parse_multi_concept_query(question: str) -> list[str]:
    normalized = _normalize_text(question).strip()
    patterns = [
        r"how (?:does|do|are|is)\s+(.+?)\s+(?:relate to|related to|connected to|connect to|compare to|different from)\s+(.+)",
        r"compare\s+(.+?)\s+(?:and|with|to)\s+(.+)",
        r"what connects\s+(.+)",
        r"relationship between\s+(.+?)\s+and\s+(.+)",
    ]
    parts: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        if len(match.groups()) == 1:
            parts = re.split(r"\s*(?:,| and | with | plus )\s*", match.group(1))
        else:
            parts = [match.group(1), match.group(2)]
        break
    if not parts and any(term in normalized for term in ["relate", "connected", "compare", "connects"]):
        parts = [item for item in re.split(r"\s*(?:,| and | with | to )\s*", normalized) if item]
    cleaned = []
    for part in parts:
        item = re.sub(r"\b(how|does|do|are|is|what|the|a|an|concepts?|related|relate|connected|compare|between)\b", " ", part)
        item = " ".join(item.strip(" ?.!").split())
        if item and item not in cleaned and len(item) > 2:
            cleaned.append(item)
    return cleaned[:5]


def retrieve_multi_concept_set(question: str, *, limit: int = 5) -> dict[str, Any]:
    seeds = parse_multi_concept_query(question)
    expanded: list[str] = []
    seen_terms = set()
    for seed in seeds:
        for term in (seed, *RELATED_QUERY_HINTS.get(seed.lower(), ())):
            key = _normalize_text(term)
            if key in seen_terms:
                continue
            seen_terms.add(key)
            expanded.append(term)
    if len(seeds) < 2:
        return {
            "matched": False,
            "seeds": seeds,
            "matches": [],
            "retrieval_set_quality": 0.0,
            "synthesis_readiness": False,
        }
    matches = []
    seen = set()
    duplicate_suppression_count = 0
    for term in expanded:
        ranked = rank_approved_concepts(term, limit=2)
        for row in ranked.get("matches", []):
            key = _normalize_compact(row.get("concept_name"))
            if key in seen:
                duplicate_suppression_count += 1
                continue
            seen.add(key)
            matches.append(row)
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break
    quality = _multi_retrieval_quality(matches, seeds)
    lines = []
    if matches:
        lines.append("I found these relevant concepts:")
        for index, row in enumerate(matches, start=1):
            lines.append(f"{index}. {row.get('concept_name')}")
        lines.extend([
            "",
            "Synthesis is not enabled yet.",
            "This retrieval set is ready for review.",
        ])
    return {
        "matched": len(matches) >= 2,
        "answer": "\n".join(lines),
        "seeds": seeds,
        "matches": matches,
        "retrieval_set_quality": quality,
        "duplicate_suppression_count": duplicate_suppression_count,
        "synthesis_readiness": False,
    }


def build_read_only_synthesis_trial(question: str, *, limit: int = 5) -> dict[str, Any]:
    retrieval = retrieve_multi_concept_set(question, limit=max(limit * 3, 12))
    if not retrieval["matched"]:
        return {
            "matched": False,
            "answer": "",
            "stored_concepts": [],
            "tentative_inference": "",
            "uncertainty": "insufficient_retrieval_set",
            "synthesis_trial_only": True,
            "synthesis_enabled": False,
            "memory_write_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "provider_calls_performed": False,
        }
    selected_rows = _select_substantive_synthesis_rows(retrieval["matches"], limit=limit)
    concepts = [_compact_concept_for_synthesis(item) for item in selected_rows]
    inference = _tentative_bridge(question, concepts)
    uncertainty = _synthesis_uncertainty(concepts, retrieval["retrieval_set_quality"])
    lines = [
        "Stored concepts used:",
    ]
    for index, concept in enumerate(concepts, start=1):
        lines.append(f"{index}. {concept['concept_name']}")
        lines.append(f"   - Stored knowledge: {concept['short_definition']}")
    lines.extend([
        "",
        "Tentative inference:",
        inference,
        "",
        "Uncertainty:",
        uncertainty,
        "",
        "No memory was written. Synthesis remains trial-only.",
    ])
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "stored_concepts": concepts,
        "tentative_inference": inference,
        "uncertainty": uncertainty,
        "retrieval_set_quality": retrieval["retrieval_set_quality"],
        "source_retrieval": retrieval,
        "synthesis_trial_only": True,
        "synthesis_enabled": False,
        "memory_write_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "provider_calls_performed": False,
    }


def _select_substantive_synthesis_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda item: (-_synthesis_substance_score(item[1]), item[0]))
    strong = [(index, row) for index, row in indexed if _synthesis_substance_score(row) >= 0.7]
    if len(strong) >= 2:
        return [row for _, row in strong[:limit]]
    return [row for _, row in indexed[:limit]]


def _synthesis_substance_score(row: dict[str, Any]) -> float:
    definition = str(row.get("short_definition") or "")
    propositions = [item for item in row.get("propositions", []) if str(item).strip()]
    examples = [item for item in row.get("examples", []) if str(item).strip()]
    misconceptions = [item for item in row.get("misconceptions", []) if str(item).strip()]
    related = [item for item in row.get("related_concepts", []) if str(item).strip()]
    score = 0.0
    if definition and not _is_generic_synthesis_definition(definition):
        score += 0.35
    score += min(len(propositions), 3) * 0.12
    score += min(len(examples), 2) * 0.08
    score += min(len(misconceptions), 1) * 0.08
    score += min(len([item for item in related if not _is_generic_synthesis_related(str(item))]), 4) * 0.05
    if _is_generic_synthesis_definition(definition):
        score -= 0.25
    return max(0.0, score)


def _is_generic_synthesis_definition(text: str) -> bool:
    lower = " ".join(text.lower().split())
    return any(marker in lower for marker in [
        "is a reusable",
        "helps explain causes, constraints, tradeoffs",
        "practical decisions in the",
        "connects observable situations to underlying",
    ])


def _is_generic_synthesis_related(text: str) -> bool:
    lower = " ".join(text.lower().split())
    return lower.endswith(("reasoning", "evidence", "tradeoffs", "constraints")) or lower in {"causes", "effects", "decisions"}


def _compact_concept_for_synthesis(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_id": row.get("concept_id"),
        "concept_name": row.get("concept_name"),
        "domain": row.get("domain"),
        "short_definition": str(row.get("short_definition") or "").strip(),
        "propositions": [str(item) for item in row.get("propositions", [])[:3]],
        "related_concepts": [str(item) for item in row.get("related_concepts", [])[:5]],
        "examples": [str(item) for item in row.get("examples", [])[:3]],
        "misconceptions": [str(item) for item in row.get("misconceptions", [])[:3]],
        "source_type": row.get("source_type"),
        "source_model_id": row.get("source_model_id"),
        "canonical": bool(row.get("canonical")),
    }


def _tentative_bridge(question: str, concepts: list[dict[str, Any]]) -> str:
    names = [str(item.get("concept_name") or "").lower() for item in concepts]
    joined = " ".join(names)
    if "photosynthesis" in joined and "respiration" in joined:
        return "These stored concepts may connect through energy transformation: photosynthesis stores energy in chemical form, while cellular respiration releases usable energy from that stored material."
    if "inflation" in joined and "interest" in joined:
        return "These stored concepts may connect through monetary conditions: inflation changes purchasing power, while interest rates influence borrowing, saving, and policy responses."
    if "memory" in joined and ("delta" in joined or "noncanonical" in joined or "canonical" in joined):
        return "These stored concepts may connect through governed retention: DELTA memory separates reversible substrate knowledge from longer-term records, while human memory concepts describe consolidation and recall."
    if "feedback" in joined and ("planning" in joined or "software" in joined):
        return "These stored concepts may connect through control loops: planning sets intended direction, feedback reveals deviation, and software architecture can encode the structures that respond to that feedback."
    primary = [str(item.get("concept_name") or "unnamed concept") for item in concepts[:3]]
    return f"These stored concepts may be connected, but the bridge is tentative: {', '.join(primary)} appear to share context, constraints, or mechanisms that need operator review before synthesis is trusted."


def _synthesis_uncertainty(concepts: list[dict[str, Any]], quality: float) -> str:
    if quality >= 0.9 and len(concepts) >= 3:
        return "moderate: the retrieval set is strong, but the bridge is inferred and has not been approved as knowledge."
    if quality >= 0.7:
        return "moderate_to_high: the retrieval set is usable, but more concept detail or operator review is needed."
    return "high: the retrieved concept set is thin or weak, so the bridge should be treated as exploratory only."


def browse_approved_concepts(
    *,
    limit: int = 3,
    domain: str | None = None,
    exclude_concept_names: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict[str, Any]:
    excluded = {str(name).lower() for name in (exclude_concept_names or [])}
    wanted_domain = str(domain or "").lower().strip()
    blocked_domains = {str(item).lower().strip() for item in (exclude_domains or []) if str(item).strip()}
    records = []
    duplicate_suppression_count = 0
    seen_source_names = set()
    for row in load_approved_concepts():
        name = str(row.get("concept_name") or "").lower()
        if name in seen_source_names:
            duplicate_suppression_count += 1
            continue
        seen_source_names.add(name)
        if excluded and name in excluded:
            continue
        if wanted_domain and str(row.get("domain") or "").lower() != wanted_domain:
            continue
        if blocked_domains and str(row.get("domain") or "").lower() in blocked_domains:
            continue
        records.append(row)
    if not records:
        return {"matched": False, "answer": "", "matches": []}
    records.sort(key=lambda row: (
        -float(row.get("quality_score") or 0.0),
        str(row.get("domain") or "zz_operator_existing"),
        str(row.get("concept_name") or ""),
    ))
    matches = []
    seen_names = set()
    for row in records:
        name = str(row.get("concept_name") or "").lower()
        if name in seen_names:
            continue
        seen_names.add(name)
        matches.append(row)
        if len(matches) >= max(1, limit):
            break
    first = matches[0]
    lines = [
        f"I know about `{first['concept_name']}` from local noncanonical memory.",
        str(first.get("short_definition") or "").strip(),
    ]
    related = [str(item) for item in first.get("related_concepts", [])[:5] if str(item).strip()]
    if related:
        lines.extend(["", "Related ideas:", *[f"- {item}" for item in related]])
    if len(matches) > 1:
        lines.extend(["", "A couple of nearby concepts I can also discuss:"])
        lines.extend(f"- {item.get('concept_name')}" for item in matches[1:])
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "matches": matches,
        "duplicate_suppression_count": duplicate_suppression_count,
    }


def build_compact_support_packet(question: str, history: list[dict[str, str]] | None = None, *, max_turns: int = 6) -> dict[str, Any]:
    clean_history = []
    for item in (history or [])[-max_turns:]:
        role = str(item.get("role") or item.get("speaker") or "user")[:24]
        text = _clean(str(item.get("content") or item.get("text") or ""))[:500]
        if text:
            clean_history.append({"role": role, "content": text})
    concepts = query_approved_concepts(question)
    concept_summaries = [
        {
            "concept_name": item.get("concept_name"),
            "short_definition": item.get("short_definition"),
            "memory_type": item.get("memory_type"),
        }
        for item in concepts.get("matches", [])[:3]
    ]
    return {
        "packet_type": "rc2_supporting_information_request",
        "question": _clean(question)[:700],
        "relevant_chat_history": clean_history,
        "relevant_approved_concepts": concept_summaries,
        "routing_reason": "local_or_substrate_confidence_was_insufficient",
        "desired_answer_format": "brief_direct_answer_with_uncertainty_if_needed",
        "instructions": "Return a concise answer only. Do not include hashes, internal reports, or unrelated diagnostics.",
        "provider_call_performed": False,
        "web_search_performed": False,
    }


def build_developmental_memory_state() -> dict[str, Any]:
    contradictions = _read_jsonl(CONCEPT_CONTRADICTION_LOG)
    return {
        "conversation_memory_records": len(_read_jsonl(CONVERSATION_MEMORY_LOG)),
        "personal_memory_records": len(_read_jsonl(PERSONAL_MEMORY_LOG)),
        "knowledge_memory_records": len(_read_jsonl(KNOWLEDGE_MEMORY_LOG)),
        "concept_edges": len(_read_jsonl(CONCEPT_EDGE_LOG)),
        "concept_contradictions": len(contradictions),
        "concept_replay_queue": len(_read_jsonl(CONCEPT_REPLAY_LOG)),
        "canonical_records": 0,
        "training_records": 0,
        "flags": dict(RC2_MEMORY_FLAGS),
    }


def clear_developmental_memory_store(confirm_text: str) -> dict[str, Any]:
    required = "DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE"
    if str(confirm_text).strip() != required:
        return {
            "cleared": False,
            "required_confirmation": required,
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    deleted = []
    for path in (*STORE_BY_TYPE.values(), CONCEPT_EDGE_LOG, CONCEPT_REPLAY_LOG, CONCEPT_CONTRADICTION_LOG):
        if path.exists():
            path.unlink()
            deleted.append(str(path))
    return {
        "cleared": True,
        "deleted": deleted,
        "state": build_developmental_memory_state(),
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
    }


def concept_edges(record: dict[str, Any], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges = []
    related = set(str(item).lower() for item in record.get("related_concepts", []))
    for other in existing:
        other_terms = {str(other.get("concept_name", "")).lower(), *(str(item).lower() for item in other.get("related_concepts", []))}
        if related & other_terms:
            edge_id = f"rc2-concept-edge-{_digest(record['concept_id'] + other['concept_id'])}"
            edges.append({
                "edge_id": edge_id,
                "from_concept_id": record["concept_id"],
                "to_concept_id": other["concept_id"],
                "relation": "related_concept_overlap",
                "canonical": False,
            })
    return edges


def find_duplicate(candidate: dict[str, Any], existing: list[dict[str, Any]]) -> dict[str, Any] | None:
    name = _normalize_text(candidate.get("concept_name", ""))
    definition = _normalize_text(candidate.get("short_definition", ""))
    for row in existing:
        if _normalize_text(row.get("concept_name", "")) == name:
            return row
        if definition and _normalize_text(row.get("short_definition", "")) == definition:
            return row
    return None


def detect_concept_contradictions(record: dict[str, Any], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contradictions = []
    new_claims = [record.get("short_definition", ""), *record.get("propositions", [])]
    for other in existing:
        old_claims = [other.get("short_definition", ""), *other.get("propositions", [])]
        for new_claim in new_claims:
            for old_claim in old_claims:
                if claims_contradict(str(old_claim), str(new_claim)):
                    contradiction_id = f"rc2-concept-contradiction-{_digest(other['concept_id'] + record['concept_id'] + old_claim + new_claim)}"
                    contradictions.append({
                        "contradiction_id": contradiction_id,
                        "concept_a_id": other["concept_id"],
                        "concept_b_id": record["concept_id"],
                        "claim_a": old_claim,
                        "claim_b": new_claim,
                        "status": "operator_review_recommended",
                        "canonical": False,
                    })
    return contradictions


def claims_contradict(a: str, b: str) -> bool:
    left = normalize_contradiction_claim(a)
    right = normalize_contradiction_claim(b)
    return bool(left["key"] and left["key"] == right["key"] and left["polarity"] != right["polarity"])


def normalize_contradiction_claim(text: str) -> dict[str, str]:
    normalized = _normalize_text(text)
    polarity = "positive"
    replacements = {
        " should not ": " should ",
        " must not ": " must ",
        " cannot ": " can ",
        " can not ": " can ",
        " is not ": " is ",
        " are not ": " are ",
        " does not ": " does ",
        " do not ": " do ",
        " not always ": " always ",
        " requires manual review ": " automatic ",
        " requires operator approval ": " automatic ",
        " requires approval ": " automatic ",
    }
    negative_markers = (" should not ", " must not ", " cannot ", " can not ", " is not ", " are not ", " does not ", " do not ", " not always ", " requires manual review ", " requires operator approval ", " requires approval ")
    if any(marker in normalized for marker in negative_markers):
        polarity = "negative"
    key = normalized
    for old, new in replacements.items():
        key = key.replace(old, new)
    key = key.replace(" automatically ", " automatic ")
    return {"key": " ".join(key.split()), "polarity": polarity}


def infer_memory_type(question: str) -> str:
    lower = question.lower()
    if any(term in lower for term in ["my ", "i prefer", "i like", "my project", "about me"]):
        return "personal"
    return "knowledge"


def infer_concept_name(question: str, answer: str) -> str:
    lower = question.lower()
    combined = f"{question} {answer}".lower()
    if "fire" in lower:
        return "Fire"
    if "water" in lower and "color" in lower:
        return "Water Color"
    if "moon" in lower and "color" in lower:
        return "Moon Color Appearance"
    if "sky" in lower and "color" in lower:
        return "Daytime Sky Color"
    if "meaning of life" in lower or "meaning of life" in combined:
        return "Meaning of Life Perspectives"
    if "workflow" in lower and "coding" in combined:
        return "Coding Learning Workflow"
    if "people" in lower and "fun" in lower:
        return "Common Leisure Activities"
    if "most people" in lower and any(term in combined for term in ["hobbies", "activities", "entertainment", "relax"]):
        return "Common Leisure Activities"
    if "avogadro" in lower:
        return "Avogadro's Number Relationship"
    if "python" in lower or "function" in lower or "code" in lower:
        return "Coding Assistance"
    words = [word.strip(".,:;!?()[]{}").capitalize() for word in question.split() if len(word.strip(".,:;!?()[]{}")) > 3]
    return " ".join(words[:4]) or "Learned Concept"


def infer_concept_type(question: str, answer: str) -> str:
    lower = f"{question} {answer}".lower()
    if any(term in lower for term in ["should", "must", "approval", "policy"]):
        return "principle_or_policy"
    if any(term in lower for term in ["because", "causes", "combustion", "scattering", "absorbs"]):
        return "causal_explanation"
    if any(term in lower for term in ["python", "function", "code", "debug"]):
        return "technical_procedure"
    return "general_concept"


def infer_short_definition(concept_name: str, propositions: list[str], answer: str) -> str:
    if propositions:
        first = propositions[0]
        return first if len(first) <= 260 else first[:257] + "..."
    clean = _clean(answer)
    return clean[:257] + "..." if len(clean) > 260 else clean


def infer_related_concepts(concept_name: str, question: str, answer: str) -> list[str]:
    text = f"{concept_name} {question} {answer}".lower()
    candidates: list[str] = []

    semantic_rules = [
        (
            ("calorie", "diet", "meal", "breakfast", "lunch", "dinner", "snack", "nutrition", "protein", "carb", "fat"),
            [
                "meal planning",
                "calorie budgeting",
                "nutrition planning",
                "portion control",
                "dietary constraints",
                "macronutrient balance",
                "weekly meal structure",
                "food variety",
                "diet sustainability",
            ],
        ),
        (
            ("meaning of life", "purpose", "happiness", "relationships", "self-reflection", "existential"),
            [
                "life philosophy",
                "subjective meaning",
                "personal growth",
                "self-reflection",
                "relationships",
                "individual purpose",
                "pursuit of happiness",
                "meaning-making",
                "existential questions",
                "social contribution",
            ],
        ),
        (
            ("coding", "programming", "debug", "python", "algorithm", "data structure", "software"),
            [
                "programming fundamentals",
                "debugging practice",
                "algorithmic thinking",
                "data structures",
                "software projects",
                "code review",
                "learning workflow",
            ],
        ),
        (
            ("sky", "moon", "color", "light", "bright", "sunlight", "scattering", "wavelength", "reflect"),
            [
                "light scattering",
                "surface reflection",
                "visible light",
                "atmospheric optics",
                "apparent color",
                "illumination",
            ],
        ),
        (
            ("plan", "workflow", "schedule", "steps", "strategy", "review"),
            [
                "workflow planning",
                "task sequencing",
                "review process",
                "operational planning",
                "success criteria",
            ],
        ),
    ]

    for triggers, related in semantic_rules:
        if any(_contains_semantic_trigger(text, trigger) for trigger in triggers):
            for item in related:
                _append_related_candidate(candidates, item)

    phrase_patterns = [
        "pursuit of happiness",
        "personal growth",
        "self-reflection",
        "sense of belonging",
        "search for answers",
        "learning and adaptation",
        "pressure cooking",
        "phase transition",
        "heat transfer",
        "crystal structure",
        "operator review",
        "approval workflow",
    ]
    for phrase in phrase_patterns:
        if phrase in text:
            _append_related_candidate(candidates, phrase)

    if not candidates:
        for phrase in _extract_reusable_noun_phrases(text):
            _append_related_candidate(candidates, phrase)
    return candidates[:10]


def _append_related_candidate(candidates: list[str], item: str) -> None:
    clean = _normalize_related_concept(item)
    if clean and clean not in candidates:
        candidates.append(clean)


def _contains_semantic_trigger(text: str, trigger: str) -> bool:
    trigger = str(trigger or "").strip().lower()
    if not trigger:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(trigger).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _normalize_related_concept(item: str) -> str:
    clean = " ".join(str(item or "").lower().replace("/", " ").split())
    clean = clean.strip(".,:;!?()[]{}'\"")
    if not clean or clean.startswith("rc2"):
        return ""
    blocked = {
        "what", "that", "this", "with", "from", "because", "about", "there", "their", "would", "could", "should",
        "please", "expand", "previous", "answer", "question", "original", "deeper", "useful", "nuance",
        "conversational", "store", "memory", "user", "asked", "reply", "assistant", "model", "meaning",
        "perspectives", "complex", "multifaceted", "concept", "approached", "various", "including",
        "angles", "standpoint", "finding", "significance", "one's", "ones", "view", "views", "contrast",
        "example", "ultimately", "deeply", "personal", "individual", "greatly", "person", "every",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "breakfast",
        "lunch", "dinner", "snack", "greek", "yogurt", "apple", "chicken", "salad", "shrimp",
        "beans", "cottage", "cheese", "peaches", "raspberries", "sweet", "potato",
    }
    if clean in blocked:
        return ""
    words = clean.split()
    if len(words) == 1 and (len(clean) < 7 or clean in blocked):
        return ""
    if len(words) == 1 and clean.endswith(("ing", "ed")):
        return ""
    return clean


def _extract_reusable_noun_phrases(text: str) -> list[str]:
    phrases = []
    patterns = [
        r"\b([a-z]+(?:\s+[a-z]+){1,2})\s+(?:planning|workflow|process|strategy|structure|balance|review|control|constraints)\b",
        r"\b(?:planning|workflow|process|strategy|structure|balance|review|control|constraints)\s+([a-z]+(?:\s+[a-z]+){0,2})\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            phrase = match.group(0)
            normalized = _normalize_related_concept(phrase)
            if normalized:
                phrases.append(normalized)
    return phrases


def infer_examples(question: str, answer: str) -> list[str]:
    examples = []
    if "for example" in answer.lower():
        examples.append(answer)
    if question:
        examples.append(question)
    return examples[:3]


def infer_misconceptions(answer: str) -> list[str]:
    lower = answer.lower()
    misconceptions = []
    if "not always" in lower:
        misconceptions.append("The relationship is not universal; context matters.")
    if "not exactly" in lower or "nearly" in lower:
        misconceptions.append("The simplified answer may be misleading without context.")
    return misconceptions


def infer_uncertainty(answer: str, lane: dict[str, Any]) -> str:
    if not lane.get("available"):
        return "local_model_lane_unavailable"
    if any(term in answer.lower() for term in ["not enough", "not confident", "uncertain", "may"]):
        return "moderate"
    return "low_to_moderate_operator_reviewed"


def _sentence_propositions(answer: str) -> list[str]:
    clean = _clean(answer)
    parts = []
    normalized = re.sub(r"(?m)^\s*\d+\s*[\.)]\s*$", " ", clean)
    normalized = re.sub(r"(?m)^\s*\d+\s*[\.)]\s*", "", normalized)
    normalized = re.sub(r"\s+\d+\s*[\.)]\s*", " ", normalized)
    for raw in normalized.replace("\r\n", " ").replace("\n", " ").split("."):
        item = raw.strip()
        if item and not re.fullmatch(r"\d+", item):
            parts.append(item + ".")
    return parts[:6]


def _query_phrases(normalized: str) -> set[str]:
    stop_phrases = {
        "what",
        "what is",
        "what are",
        "what do",
        "tell me",
        "explain",
        "how does",
        "how do",
        "how are",
        "relate to",
        "connected to",
        "compare",
        "people",
        "usually",
        "for fun",
    }
    words = [
        word for word in normalized.split()
        if word not in {"the", "a", "an", "and", "or", "to", "of", "in", "what", "do", "does", "usually", "people", "tell", "me", "about", "show", "explain"}
    ]
    phrases = set()
    for size in (3, 2):
        for index in range(0, max(0, len(words) - size + 1)):
            phrase = " ".join(words[index:index + size]).strip()
            if phrase and phrase not in stop_phrases and len(phrase) > 4:
                phrases.add(phrase)
    phrases.update(word for word in words if len(word) > 3)
    return phrases


def _query_key_tokens(normalized: str) -> set[str]:
    return {
        word for word in _meaningful_tokens(normalized)
        if word not in {"example", "examples", "pretend", "favorite", "conversation"}
    }


def _relevance_gate_passed(
    *,
    query_key_tokens: set[str],
    name_overlap: set[str],
    overlap: set[str],
    reasons: list[str],
    phrase_count: int,
) -> bool:
    if any(reason in {"forced_domain_match", "domain_alias_match"} for reason in reasons):
        return True
    if any(reason.startswith("name_phrase:") and " " in reason.split(":", 1)[1] for reason in reasons):
        return True
    if len(query_key_tokens) <= 1:
        return bool(name_overlap or overlap or any(reason.startswith(("name_phrase:", "source_phrase:", "related_phrase:")) for reason in reasons))
    if len(name_overlap) >= 2:
        return True
    if len(query_key_tokens & overlap) >= min(2, len(query_key_tokens)):
        return True
    if phrase_count and any(reason.startswith(("proposition_phrase:", "related_phrase:", "source_phrase:")) and " " in reason.split(":", 1)[1] for reason in reasons):
        return True
    return False


def _contains_phrase(text: str, phrase: str) -> bool:
    phrase = _normalize_text(phrase).strip()
    if not phrase:
        return False
    return f" {phrase} " in f" {text} "


def _normalize_compact(text: object) -> str:
    return " ".join(_normalize_text(text).split())


def _retrieval_precision_estimate(matches: list[dict[str, Any]], profile: dict[str, Any]) -> float:
    if not matches:
        return 0.0
    relevant = 0
    for row in matches:
        score = row.get("_retrieval_score") or {}
        reasons = set(score.get("reasons", []))
        if score.get("relevance_gate_passed") and (
            score.get("score", 0) >= 8
            or "domain_alias_match" in reasons
            or any(str(reason).startswith("name_phrase:") for reason in reasons)
        ):
            relevant += 1
            continue
        if score.get("overlap"):
            relevant += 1
    return round(relevant / len(matches), 4)


def _multi_retrieval_quality(matches: list[dict[str, Any]], seeds: list[str]) -> float:
    if not seeds or not matches:
        return 0.0
    covered = 0
    for seed in seeds:
        seed_profile = retrieval_query_profile(seed)
        if any(score_concept_for_query(row, seed_profile)["score"] >= 6 for row in matches):
            covered += 1
    coverage = covered / len(seeds)
    breadth = min(len(matches), 5) / 5
    return round((coverage * 0.75) + (breadth * 0.25), 4)


def _meaningful_tokens(text: str) -> set[str]:
    stop = {
        "what",
        "about",
        "that",
        "this",
        "from",
        "with",
        "does",
        "tell",
        "know",
        "your",
        "have",
        "were",
        "been",
        "will",
        "should",
        "usually",
        "often",
        "generally",
        "something",
        "another",
        "different",
        "concept",
        "concepts",
        "people",
    }
    short_keep = {"law", "ai", "ui", "ux", "api", "atp", "fun"}
    return {word for word in _normalize_text(text).split() if (len(word) > 3 or word in short_keep) and word not in stop}


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
    clear_runtime_concept_caches()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    clear_runtime_concept_caches()


def _merge_unique_lines(*groups: object) -> list[str]:
    merged = []
    seen = set()
    for group in groups:
        items = group if isinstance(group, list) else [group]
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            key = _normalize_text(text)
            if key not in seen:
                seen.add(key)
                merged.append(text)
    return merged


def _normalize_approval(text: str) -> str:
    return " ".join(str(text).strip().lower().replace(".", " ").split())


def _normalize_text(text: object) -> str:
    normalized = str(text).lower()
    for char in ["'", "-", "?", "/", "\\", ".", ",", ":", ";", "!", "(", ")", "[", "]", "{", "}"]:
        normalized = normalized.replace(char, " ")
    return " " + " ".join(normalized.split()) + " "


def _clean(text: str) -> str:
    return " ".join(str(text).replace("\r\n", "\n").replace("\r", "\n").split())


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _store_signature(paths: dict[str, Path]) -> tuple[tuple[str, str, int, int], ...]:
    signature = []
    for name, path in sorted(paths.items()):
        if path.exists():
            stat = path.stat()
            signature.append((name, str(path), stat.st_mtime_ns, stat.st_size))
        else:
            signature.append((name, str(path), 0, 0))
    return tuple(signature)
