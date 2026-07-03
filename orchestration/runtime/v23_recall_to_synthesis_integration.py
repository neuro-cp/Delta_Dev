from __future__ import annotations

import hashlib
from dataclasses import dataclass

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v22_controlled_general_recall_expansion import run_controlled_general_recall_expansion


RUNTIME_V23C_FLAGS = {
    "recall_to_synthesis_integration_enabled": True,
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


@dataclass(frozen=True)
class RecallSynthesisRequest:
    request_id: str
    query: str
    use_recall: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def run_recall_to_synthesis(query: str, *, use_recall: bool = False, max_candidates: int = 5) -> dict[str, object]:
    local = route_local_knowledge_answer(query)
    recall = run_controlled_general_recall_expansion(query, max_candidates=max_candidates) if use_recall else None
    evidence = []
    if recall:
        for item in recall["candidates"]:
            evidence.append({
                "candidate_id": item["candidate_id"],
                "text": item["text"],
                "provenance": item.get("provenance", []),
                "candidate_context_only": True,
                "authoritative": False,
            })
    conflicts = [item for item in evidence if any(term in str(item["text"]).lower() for term in ("conflict", "contradict", "uncertain"))]
    if local.matched and local.answer:
        answer = local.answer.answer_text
    elif evidence:
        answer = "Candidate context suggests: " + "; ".join(str(item["text"]) for item in evidence[:2])
    else:
        answer = "I do not have sufficient governed local evidence to answer directly."
    return {
        "phase": "Runtime V2.3C",
        "request": RecallSynthesisRequest(_stable_id("v23c-request", query, use_recall), query, use_recall).as_dict(),
        "local_answer": local.as_dict(),
        "recall_context": recall,
        "evidence_items": evidence,
        "draft": {
            "draft_id": _stable_id("v23c-draft", query, answer),
            "answer_text": answer,
            "uses_candidate_context": bool(evidence),
            "grounded": True,
            "provider_required": False,
        },
        "conflict_note": {
            "has_conflict": bool(conflicts),
            "note": "Candidate context contains conflict or uncertainty; answer should remain bounded." if conflicts else "",
        },
        "decision": {
            "memory_write_performed": False,
            "recall_mutated": False,
            "provider_call_performed": False,
            "training_triggered": False,
            "action_execution_performed": False,
        },
        "invariant_flags": dict(RUNTIME_V23C_FLAGS),
        "final_recommendation": "PROCEED_PROVIDER_EVIDENCE_LIVE_TO_CANDIDATE_TRIAL",
    }


def validate_recall_to_synthesis_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        all(item["candidate_context_only"] is True and item["authoritative"] is False for item in payload["evidence_items"])
        and payload["decision"]["memory_write_performed"] is False
        and payload["decision"]["recall_mutated"] is False
        and flags["recall_to_synthesis_integration_enabled"] is True
        and flags["candidate_context_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"recall_to_synthesis_integration_enabled", "candidate_context_only"})
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

