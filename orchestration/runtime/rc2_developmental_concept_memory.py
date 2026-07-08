"""RC2 developmental concept memory.

This module implements the first concept-shaped, noncanonical learning loop
behind DELTA's conversational UI. It does not train models, mutate canonical
memory, call providers, start schedulers, or execute actions.
"""

from __future__ import annotations

import hashlib
import json
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


def query_approved_concepts(question: str) -> dict[str, Any]:
    tokens = _meaningful_tokens(question)
    if not tokens:
        return {"matched": False, "answer": "", "matches": []}
    records = []
    for memory_type, path in STORE_BY_TYPE.items():
        for row in _read_jsonl(path):
            if row.get("approval_status") == "approved_noncanonical":
                records.append({**row, "_store_memory_type": memory_type})
    scored = []
    for row in records:
        haystack = " ".join([
            str(row.get("concept_name", "")),
            str(row.get("short_definition", "")),
            " ".join(str(item) for item in row.get("propositions", [])),
            " ".join(str(item) for item in row.get("related_concepts", [])),
        ])
        overlap = tokens & _meaningful_tokens(haystack)
        minimum_overlap = 1 if len(tokens) == 1 else 2
        if len(overlap) >= minimum_overlap:
            scored.append((len(overlap), row))
    if not scored:
        return {"matched": False, "answer": "", "matches": []}
    scored.sort(key=lambda item: (-item[0], item[1]["concept_name"]))
    matches = [row for _, row in scored[:5]]
    first = matches[0]
    lines = [
        f"You taught me the concept `{first['concept_name']}` earlier. Based on that:",
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
    return {"matched": True, "answer": "\n".join(lines), "matches": matches}


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
    stop = {"what", "that", "this", "with", "from", "because", "about", "there", "their", "would", "could", "should"}
    candidates = []
    for word in f"{concept_name} {question} {answer}".replace("/", " ").split():
        clean = word.strip(".,:;!?()[]{}'\"").lower()
        if len(clean) > 4 and clean not in stop and clean not in candidates:
            candidates.append(clean)
    return candidates[:10]


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
    for raw in clean.replace("\r\n", " ").replace("\n", " ").split("."):
        item = raw.strip()
        if item:
            parts.append(item + ".")
    return parts[:6]


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
    }
    return {word for word in _normalize_text(text).split() if len(word) > 3 and word not in stop}


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


def _normalize_approval(text: str) -> str:
    return " ".join(str(text).strip().lower().replace(".", " ").split())


def _normalize_text(text: object) -> str:
    return " " + " ".join(str(text).lower().replace("'", "").replace("-", " ").replace("?", " ").split()) + " "


def _clean(text: str) -> str:
    return " ".join(str(text).replace("\r\n", "\n").replace("\r", "\n").split())


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
