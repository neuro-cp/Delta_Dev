"""RC2 conversational shell and DELTA mode router scaffold.

RC2 makes the RC1 substrate one selectable mode behind a conversational front
door. It does not enable provider calls, web search, training, canonical
writes, autonomous actions, or production routing. External provider routes
are consent-gated. Local model lanes may execute when the caller explicitly
asks for local inference.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable
import json
import re

from integration.model_runtime.model_registry import list_available_models
from integration.model_runtime.provider_manager import ProviderManager
from orchestration.runtime.rc1_operator_console import (
    answer_operator_question,
    approve_propositions,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    query_noncanonical_substrate,
)
from orchestration.runtime.rc2_developmental_concept_memory import (
    approve_candidate_concept,
    build_compact_support_packet,
    build_developmental_memory_state,
    discover_memory_store_separation,
    extract_candidate_concept,
    query_approved_concepts,
)
from orchestration.runtime.v17_provider_assisted_unknown_answer import answer_unknown_with_controlled_provider
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

DISPLAY_MODES = [
    "Conversation",
    "Memory Mode",
    "Research",
    "Evidence Review",
    "Investigation",
    "Replay",
    "Developer",
    "Diagnostics",
]

MODES = DISPLAY_MODES + [
    "Ask Substrate",
    "Review Mode",
    "Contradiction Check",
    "Failure Log",
    "Research Analyst",
    "Frontier App Assistant",
]

ROUTER_FLAGS = {
    "rc2_conversational_shell_enabled": True,
    "mode_router_enabled": True,
    "provider_calls_enabled": False,
    "web_search_enabled": False,
    "training_enabled": False,
    "canonical_writes_enabled": False,
    "autonomous_actions_enabled": False,
    "production_routing_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

MODEL_LANE_ORDER = {
    "everyday_conversation": ("phi4", "qwen", "llama", "mistral", "phi3"),
    "coding_technical": ("qwen", "phi4", "llama", "mistral", "phi3"),
    "reasoning_analysis": ("qwen", "llama", "mistral", "phi4", "phi3"),
    "planning": ("phi4", "qwen", "mistral", "llama", "phi3"),
    "vision": ("qwen", "llama", "phi4", "mistral", "phi3"),
    "concept_extraction": ("qwen", "phi4", "llama", "mistral", "phi3"),
    "contradiction_detection": ("phi4", "qwen", "llama", "mistral", "phi3"),
}

LANE_METADATA = {
    "everyday_conversation": {
        "display_name": "Everyday Conversation Lane",
        "expected_strength": "casual chat, common explanations, companionship, low-stakes brainstorming",
        "expected_weakness": "specialized factual lookup and high-stakes reasoning require support",
        "cost_latency_class": "low_to_medium_local",
        "preferred_task_lanes": ["conversation", "question", "self_description"],
        "fallback_priority": 1,
    },
    "coding_technical": {
        "display_name": "Coding / Technical Lane",
        "expected_strength": "programming, debugging, architecture, CLI, repo reasoning",
        "expected_weakness": "may need repo file context or tests for correctness",
        "cost_latency_class": "medium_local",
        "preferred_task_lanes": ["coding", "technical_explanation"],
        "fallback_priority": 2,
    },
    "reasoning_analysis": {
        "display_name": "Reasoning / Analysis Lane",
        "expected_strength": "multi-step reasoning, comparison, science, synthesis, uncertainty",
        "expected_weakness": "external facts need gated supporting information",
        "cost_latency_class": "medium_to_high_local",
        "preferred_task_lanes": ["analysis", "research", "investigation", "external_knowledge_request"],
        "fallback_priority": 3,
    },
    "planning": {
        "display_name": "Planning Lane",
        "expected_strength": "strategy, schedules, staged workflows",
        "expected_weakness": "cannot execute actions from RC2",
        "cost_latency_class": "medium_local",
        "preferred_task_lanes": ["planning"],
        "fallback_priority": 4,
    },
    "vision": {
        "display_name": "Vision Lane",
        "expected_strength": "image-capable model selection when a vision GGUF is available",
        "expected_weakness": "RC2 UI does not execute vision inference",
        "cost_latency_class": "high_local_if_enabled",
        "preferred_task_lanes": ["image"],
        "fallback_priority": 5,
    },
    "concept_extraction": {
        "display_name": "Concept Extraction Lane",
        "expected_strength": "turn useful answers into reusable concepts",
        "expected_weakness": "first pass is deterministic and operator-reviewed",
        "cost_latency_class": "low_local_scaffold",
        "preferred_task_lanes": ["memory_request"],
        "fallback_priority": 6,
    },
    "contradiction_detection": {
        "display_name": "Contradiction Detection Lane",
        "expected_strength": "first-pass deterministic contradiction checks",
        "expected_weakness": "semantic contradiction detection remains conservative",
        "cost_latency_class": "low_local_scaffold",
        "preferred_task_lanes": ["contradiction_check"],
        "fallback_priority": 7,
    },
}

DIRECT_LOCAL_ANSWERS = {
    "sky_color": {
        "triggers": (("sky", "color"),),
        "answer": "The sky usually looks blue during the day because air molecules scatter shorter blue wavelengths of sunlight more strongly than longer red wavelengths.",
        "confidence": 0.88,
    },
    "water_color": {
        "triggers": (("water", "color"), ("color", "water")),
        "answer": "Pure water is nearly colorless in a small glass, but large amounts can look faintly blue because water absorbs a little more red light than blue light. In everyday life, water also reflects the sky and surrounding surfaces, so it can look blue, gray, green, or brown depending on context.",
        "confidence": 0.82,
    },
    "fire_definition": {
        "triggers": (("what", "fire"), ("fire",), ("define", "fire")),
        "answer": "Fire is the visible, hot part of combustion. A fuel reacts with oxygen, releasing heat and light, and the flame contains hot gases plus glowing particles or excited molecules.",
        "confidence": 0.82,
    },
}

VAGUE_CONCEPT_NAMES = {
    "What Most People",
    "What Color",
    "What Is",
    "General Question",
    "User Asked",
    "Learned Concept",
}

LOW_CONFIDENCE_MARKERS = (
    "not enough",
    "not confident",
    "supporting information",
    "look for sources",
    "ask gpt",
    "cannot answer",
    "do not have enough",
)
def classify_intent(message: str) -> dict[str, Any]:
    lower = message.lower()
    if any(term in lower for term in ["diagnostic", "show diagnostics", "runtime status", "system health", "health check"]):
        intent = "diagnostics"
    elif any(term in lower for term in ["remember", "store", "save this"]):
        intent = "memory_request"
    elif any(term in lower for term in ["contradiction", "conflict", "incompatible"]):
        intent = "contradiction_check"
    elif any(term in lower for term in ["code", "coding", "python", "bug", "function"]):
        intent = "coding"
    elif any(term in lower for term in ["plan", "schedule", "strategy"]):
        intent = "planning"
    elif any(term in lower for term in ["analyze", "compare", "why", "because"]):
        intent = "analysis"
    elif any(term in lower for term in ["document", "pdf", "invoice", "evidence"]):
        intent = "document"
    elif any(term in lower for term in ["image", "picture", "photo"]):
        intent = "image"
    elif any(term in lower for term in ["investigate", "case", "research", "latest status"]):
        intent = "investigation"
    elif any(term in lower for term in ["how do you work", "what are you", "delta"]):
        intent = "self_description"
    elif any(term in lower for term in ["avogadro", "quantum field", "beluga", "whale"]):
        intent = "external_knowledge_request"
    elif any(term in lower for term in ["what do you know", "frontier", "substrate"]):
        intent = "substrate_question"
    else:
        intent = "question" if lower.endswith("?") else "conversation"
    return {"intent": intent, "message": message, "confidence": confidence_for_intent(intent)}


def select_model_lane(message: str, intent: str | None = None) -> dict[str, Any]:
    """Choose the best already-wired local model lane without executing it."""
    intent = intent or classify_intent(message)["intent"]
    if intent == "coding":
        lane = "coding_technical"
    elif intent in {"external_knowledge_request", "investigation", "document", "analysis"}:
        lane = "reasoning_analysis"
    elif intent == "planning":
        lane = "planning"
    elif intent == "image":
        lane = "vision"
    elif intent == "memory_request":
        lane = "concept_extraction"
    elif intent == "contradiction_check":
        lane = "contradiction_detection"
    else:
        lane = "everyday_conversation"

    available = list_available_models()
    selected = None
    for alias in MODEL_LANE_ORDER[lane]:
        if alias in available and _model_is_usable(available[alias]):
            selected = alias
            break
    if selected is None and available:
        usable = [key for key, spec in sorted(available.items()) if _model_is_usable(spec)]
        selected = usable[0] if usable else None
    spec = available.get(selected) if selected else None
    meta = LANE_METADATA[lane]
    return {
        "lane": lane,
        "support_identifier": _model_support_identifier(lane, selected, spec),
        "display_name": meta["display_name"],
        "selected_model": selected,
        "selected_model_id": spec.name if spec else None,
        "selected_model_path": str(Path(spec.path)) if spec else None,
        "available": bool(selected),
        "executed": False,
        "execution_gate": "not_executed_by_default",
        "provider_calls_performed": False,
        "model_family": spec.family if spec else "unavailable",
        "capabilities": list(spec.capabilities) if spec else [],
        "context_size": spec.context_length if spec else None,
        "expected_strength": meta["expected_strength"],
        "expected_weakness": meta["expected_weakness"],
        "cost_latency_class": meta["cost_latency_class"],
        "preferred_task_lanes": meta["preferred_task_lanes"],
        "fallback_priority": meta["fallback_priority"],
    }


def _model_is_usable(spec: Any) -> bool:
    path = Path(str(getattr(spec, "path", "")))
    parts = {part.lower() for part in path.parts}
    return bool(path.exists() and "fail" not in parts)


def _model_support_identifier(lane: str, selected: str | None, spec: Any | None) -> str:
    if spec is None or not selected:
        return f"rc2-local-lane:{lane}:unavailable"
    capabilities = ",".join(sorted(str(item) for item in getattr(spec, "capabilities", ()))) or "none"
    family = str(getattr(spec, "family", "unknown"))
    model_id = str(getattr(spec, "name", selected))
    return f"rc2-local-lane:{lane}:model:{model_id}:family:{family}:capabilities:{capabilities}"


def discover_local_model_lanes() -> dict[str, Any]:
    models = list_available_models()
    return {
        "available_model_count": len(models),
        "models": [
            {
                "model_id": key,
                "display_name": spec.name,
                "context_size": spec.context_length,
                "family": spec.family,
                "provider": spec.provider,
                "capabilities": list(spec.capabilities),
                "tier": spec.tier,
                "cost_latency_class": "local_gguf_tier_" + str(spec.tier),
            }
            for key, spec in sorted(models.items())
        ],
        "lanes": LANE_METADATA,
        "lane_order": MODEL_LANE_ORDER,
        "model_execution_enabled_by_default": False,
    }


def confidence_for_intent(intent: str) -> float:
    table = {
        "diagnostics": 0.92,
        "memory_request": 0.88,
        "contradiction_check": 0.9,
        "coding": 0.68,
        "planning": 0.72,
        "analysis": 0.66,
        "document": 0.78,
        "image": 0.62,
        "investigation": 0.76,
        "substrate_question": 0.9,
        "external_knowledge_request": 0.86,
        "self_description": 0.94,
        "question": 0.7,
        "conversation": 0.65,
    }
    return table.get(intent, 0.5)


def _direct_answer(message: str) -> dict[str, Any] | None:
    lower = " " + " ".join(message.lower().replace("?", " ").split()) + " "
    for answer_id, item in DIRECT_LOCAL_ANSWERS.items():
        for trigger in item["triggers"]:
            if all(f" {word} " in lower for word in trigger):
                return {
                    "answer_id": answer_id,
                    "answer": item["answer"],
                    "confidence_score": item["confidence"],
                    "confidence": "local_general_knowledge",
                }
    return None


def _support_offer(message: str, reason: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    dry_run = answer_unknown_with_controlled_provider(message, live_provider=False)
    packet = build_compact_support_packet(message, history)
    return {
        "offered": True,
        "reason": reason,
        "prompt": "I'm not confident enough locally. Would you like me to ask GPT or look for sources?",
        "options": [
            "yes_ask_gpt_or_sources",
            "not_now",
        ],
        "dry_run_provider_request": dry_run["route_or_provider_request"],
        "compact_support_packet": packet,
        "provider_calls_performed": False,
        "web_search_performed": False,
    }


def _local_model_offer(message: str, reason: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    packet = build_compact_support_packet(message, history)
    return {
        "offered": True,
        "reason": reason,
        "prompt": "I don't think I know enough from my learned local knowledge yet. Would you like me to ask a local reasoning model?",
        "options": ["yes_ask_local_model", "not_now"],
        "compact_local_model_packet": packet,
        "local_model_call_performed": False,
        "provider_calls_performed": False,
        "web_search_performed": False,
    }


def _compact_model_prompt(message: str, history: list[dict[str, str]] | None = None) -> str:
    packet = build_compact_support_packet(message, history)
    turns = packet.get("relevant_chat_history", [])
    concepts = packet.get("relevant_approved_concepts", [])
    lines = [
        "Answer like a friendly, concise assistant.",
        "Use the short conversation context when it matters.",
        "Do not mention routing, model names, hashes, JSON, or safety flags.",
        "",
        "Current user message:",
        str(packet["question"]),
    ]
    if turns:
        lines.extend(["", "Relevant recent turns:"])
        for turn in turns:
            lines.append(f"- {turn['role']}: {turn['content']}")
    if concepts:
        lines.extend(["", "Relevant approved local concepts:"])
        for concept in concepts:
            lines.append(f"- {concept.get('concept_name')}: {concept.get('short_definition')}")
    lines.extend(["", "Return only the answer text."])
    return "\n".join(lines)


def execute_local_model_answer(
    message: str,
    model_lane: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Execute one selected local model lane when explicitly requested.

    This is a local inference path only. It does not grant provider authority,
    call GPT/API, train, write memory, or perform actions.
    """
    model_name = model_lane.get("selected_model")
    prompt = _compact_model_prompt(message, history)
    if not model_name:
        return {
            "executed": False,
            "available": False,
            "answer": "",
            "reason": "no_local_model_available",
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }
    try:
        result = ProviderManager().infer(
            model_name=str(model_name),
            prompt=prompt,
            task_type="rc2_conversation",
            metadata={"route": "rc2_local_model_lane", "lane": model_lane.get("lane")},
        )
        answer = result.answer
        confidence = float(result.confidence or 0.72)
        clean_answer = _naturalize_model_answer(answer)
        return {
            "executed": bool(clean_answer),
            "available": True,
            "answer": clean_answer,
            "confidence_score": max(0.0, min(1.0, confidence)),
            "model_id": model_name,
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }
    except Exception as exc:  # pragma: no cover - defensive for local model runtime availability
        return {
            "executed": False,
            "available": True,
            "answer": "",
            "reason": f"local_model_execution_failed:{type(exc).__name__}",
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }


def _naturalize_model_answer(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and isinstance(parsed.get("answer"), str):
            return " ".join(parsed["answer"].split())
    except Exception:
        pass
    match = re.search(r'"answer"\s*:\s*"(?P<answer>.*?)(?:"\s*,\s*"confidence"|"\s*[,}])', raw, flags=re.DOTALL)
    if match:
        value = match.group("answer")
        try:
            value = json.loads(f'"{value}"')
        except Exception:
            value = value.replace(r"\"", '"').replace(r"\n", " ")
        return " ".join(str(value).split())
    if raw.startswith("{") and '"answer"' in raw:
        start = raw.find('"answer"')
        colon = raw.find(":", start)
        quote = raw.find('"', colon)
        if quote >= 0:
            value = raw[quote + 1 :]
            value = value.rsplit('"', 1)[0] if '"' in value else value
            value = value.replace(r"\"", '"').replace(r"\n", " ")
            return " ".join(value.split())
    return " ".join(raw.split())


def execute_gpt_support_request(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    transport: Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]] | None = None,
) -> dict[str, Any]:
    compact_packet = build_compact_support_packet(message, history)
    provider = answer_unknown_with_controlled_provider(message, live_provider=True, transport=transport)
    evidence_packet = provider.get("evidence_packet")
    if evidence_packet and evidence_packet.get("provider_text"):
        answer = str(evidence_packet["provider_text"]).strip()
        route = "provider_support_after_user_consent"
        provider_call = True
        confidence = "provider_assisted_non_authoritative"
        confidence_score = 0.72
    else:
        decision = ((provider.get("decision") or {}).get("decision") or "live_refused")
        answer = (
            "I couldn't ask GPT from this session because the provider gate is not enabled or the API key is unavailable. "
            "No provider call was made."
            if decision == "live_refused"
            else "I did not need GPT because local DELTA knowledge already matched this question."
        )
        route = "provider_support_refused_or_local_known"
        provider_call = False
        confidence = "provider_path_not_available"
        confidence_score = 0.2
    return {
        "mode": "Conversation",
        "route": route,
        "answer": answer,
        "compact_support_packet": compact_packet,
        "provider_result": provider,
        "selected_model_lane": select_model_lane(message),
        "confidence": confidence,
        "confidence_score": confidence_score,
        "supporting_information_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": provider_call,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "mode_router_flags": ROUTER_FLAGS,
    }


def build_gpt_approval_preview(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    packet = build_compact_support_packet(message, history)
    return {
        "mode": "Conversation",
        "route": "gpt_support_approval_preview",
        "answer": (
            "I'm not confident enough locally. Would you like me to ask GPT or look for sources?"
        ),
        "compact_support_packet": packet,
        "selected_model_lane": select_model_lane(message),
        "confidence": "requires_explicit_provider_approval",
        "confidence_score": 0.0,
        "supporting_information_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def build_memory_candidate_from_answer(message: str, payload: dict[str, Any]) -> dict[str, Any]:
    return extract_candidate_concept(
        question=message,
        answer=str(payload.get("answer", "")),
        source_model_lane=dict(payload.get("selected_model_lane") or select_model_lane(message)),
        source_type="substrate" if payload.get("route") == "developmental_concept_memory" else "local_model_lane",
    )


def candidate_is_memory_worthy(candidate: dict[str, Any], payload: dict[str, Any] | None = None) -> bool:
    name = " ".join(str(candidate.get("concept_name", "")).split())
    if not name or name in VAGUE_CONCEPT_NAMES:
        return False
    if name.lower().startswith(("what ", "how ", "why ", "tell ", "general ", "user ")):
        return False
    answer = str((payload or {}).get("answer") or " ".join(candidate.get("propositions", []))).lower()
    if any(marker in answer for marker in LOW_CONFIDENCE_MARKERS):
        return False
    score = float((payload or {}).get("confidence_score") or 0.0)
    if score and score < 0.72:
        return False
    propositions = [str(item).strip() for item in candidate.get("propositions", []) if str(item).strip()]
    if not propositions:
        return False
    if all(len(item.split()) < 5 for item in propositions):
        return False
    return True


def maybe_build_memory_candidate(message: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("route") in {"gpt_support_approval_preview", "provider_support_refused_or_local_known"}:
        return None
    if payload.get("supporting_information_offer"):
        return None
    candidate = build_memory_candidate_from_answer(message, payload)
    return candidate if candidate_is_memory_worthy(candidate, payload) else None


def remember_useful_answer(message: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = payload.get("memory_candidate")
    candidate = existing if isinstance(existing, dict) else maybe_build_memory_candidate(message, payload)
    if not candidate:
        return {
            "candidate": None,
            "result": {
                "approved": False,
                "reason": "no_coherent_memory_candidate",
                "canonical_write_performed": False,
                "training_performed": False,
                "provider_calls_performed": False,
            },
            "memory_write_performed": False,
            "memory_scope": "none",
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
            "rollback_supported": False,
        }
    result = approve_candidate_concept(candidate, approval_text="Keep this concept")
    return {
        "candidate": candidate,
        "result": result,
        "memory_write_performed": result.get("approved") is True,
        "memory_scope": "local_noncanonical_rc2_developmental_concept_store",
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "rollback_supported": True,
    }


def _history_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    lower = message.lower()
    if not history:
        return None
    user_turns = [item.get("content", "") for item in history if item.get("role") == "user" and item.get("content")]
    if ("what did i just ask" in lower or "last thing i asked" in lower) and user_turns:
        last = user_turns[-1]
        return {
            "route": "conversation_short_term_memory",
            "answer": f"You just asked: \"{last}\"",
            "confidence": "session_memory",
            "confidence_score": 0.95,
            "selected_model_lane": select_model_lane(message),
            "supporting_information_offer": None,
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
    return None


def local_conversation_answer(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    execute_local_model: bool = False,
) -> dict[str, Any]:
    lower = message.lower()
    intent = classify_intent(message)["intent"]
    model_lane = select_model_lane(message, intent)
    local = run_v29_local_answer(message, use_recall=False)
    if memory := _history_answer(message, history):
        return memory
    local_model_result = None
    if "ask gpt automatically" in lower or "call gpt automatically" in lower or "provider automatically" in lower:
        return {
            "route": "provider_policy_answer",
            "answer": "No. I should not ask GPT or any provider automatically. If local knowledge is not enough, I should ask your permission first and send only a compact request after you approve.",
            "confidence": "local_provider_policy",
            "confidence_score": 0.9,
            "selected_model_lane": model_lane,
            "local_model_result": None,
            "supporting_information_offer": None,
            "local_model_offer": None,
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
    if execute_local_model and intent not in {"external_knowledge_request", "image"}:
        local_model_result = execute_local_model_answer(message, model_lane, history)
        model_lane = {**model_lane, "executed": bool(local_model_result.get("executed"))}
        if local_model_result.get("executed"):
            return {
                "route": "local_conversation_model_lane",
                "answer": str(local_model_result["answer"]),
                "confidence": "local_model_inference",
                "confidence_score": float(local_model_result.get("confidence_score") or 0.72),
                "selected_model_lane": model_lane,
                "local_model_result": local_model_result,
                "supporting_information_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
    if intent == "coding":
        answer = (
            "I can help with coding by reading the repo, explaining files, proposing patches, writing tests, and validating behavior. "
        )
        confidence = "local_coding_capability_route"
        confidence_score = 0.78
        support_offer = None
    elif "topics" in lower and ("know" in lower or "best" in lower or "most" in lower):
        answer = (
            "Right now I am strongest at explaining DELTA itself, working with local approved substrate memory, "
            "helping with code and planning conversations, and walking through governed evidence workflows. "
            "For ordinary world knowledge I can answer simple questions locally; if confidence is low, I should ask whether you want supporting information before escalating."
        )
        confidence = "local_capability_self_description"
        confidence_score = 0.84
        support_offer = None
    elif local["local_answer"]["matched"]:
        answer = str(local["draft"]["answer_text"])
        confidence = "repo_local_self_knowledge"
        confidence_score = 0.86
        support_offer = None
    elif direct := _direct_answer(message):
        answer = str(direct["answer"])
        confidence = str(direct["confidence"])
        confidence_score = float(direct["confidence_score"])
        support_offer = None
    elif intent in {"external_knowledge_request", "image"}:
        answer = (
            "I do not have enough governed local evidence to answer that confidently. "
            "I'm not confident enough locally. Would you like me to ask GPT or look for sources?"
        )
        confidence = "needs_supporting_information"
        confidence_score = 0.35
        support_offer = _support_offer(message, "insufficient_local_evidence", history)
    else:
        if execute_local_model and local_model_result and local_model_result.get("reason"):
            answer = (
                "I couldn't reach the local conversation model from this session, so I can only give a cautious built-in response. "
                "I'm not confident enough locally. Would you like me to ask GPT or look for sources?"
            )
            confidence = "local_model_unavailable"
            confidence_score = 0.3
            support_offer = _support_offer(message, "local_model_unavailable", history)
        else:
            answer = (
                "I don't think I know enough from my learned local knowledge yet. "
                "Would you like me to ask a local reasoning model?"
            )
            confidence = "needs_local_reasoning_model"
            confidence_score = 0.3
            support_offer = None
            local_model_offer = _local_model_offer(message, "missing_learned_or_direct_knowledge", history)
            return {
                "route": "local_model_consent_required",
                "answer": answer,
                "confidence": confidence,
                "confidence_score": confidence_score,
                "selected_model_lane": model_lane,
                "local_model_result": local_model_result,
                "supporting_information_offer": None,
                "local_model_offer": local_model_offer,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
    return {
        "route": "local_conversation_model_lane",
        "answer": answer,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "selected_model_lane": model_lane,
        "local_model_result": local_model_result,
        "supporting_information_offer": support_offer,
        "local_model_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
    }


def build_escalation_plan(message: str) -> dict[str, Any]:
    intent = classify_intent(message)["intent"]
    if intent == "external_knowledge_request":
        recommended = ["local_model_research", "web_search_with_operator_approval", "large_model_review_with_operator_approval"]
    elif intent in {"coding", "analysis", "planning", "investigation"}:
        recommended = ["local_conversation", "substrate_check", "local_model_with_operator_gate"]
    elif intent == "memory_request":
        recommended = ["conversation_memory_offer", "noncanonical_memory_with_operator_approval"]
    elif intent == "document":
        recommended = ["evidence_review", "operator_review", "noncanonical_memory_with_operator_approval"]
    else:
        recommended = ["local_conversation", "substrate_check"]
    return {
        "intent": intent,
        "recommended_routes": recommended,
        "requires_operator_approval": any("approval" in item for item in recommended),
        "provider_calls_performed": False,
        "web_search_performed": False,
        "enabled_now": False,
    }


def confidence_engine(message: str, substrate_matched: bool = False) -> dict[str, Any]:
    intent = classify_intent(message)
    if substrate_matched:
        confidence = 0.9
        evidence_quality = "approved_noncanonical_substrate"
        provider_necessity = "none"
    elif intent["intent"] in {"external_knowledge_request", "image"}:
        confidence = 0.35
        evidence_quality = "insufficient_local_evidence"
        provider_necessity = "gated_provider_or_web_may_be_needed"
    else:
        confidence = intent["confidence"]
        evidence_quality = "local_conversation_or_mode_context"
        provider_necessity = "not_required_for_local_response"
    return {
        "confidence": round(confidence, 2),
        "evidence_quality": evidence_quality,
        "retrieval_sufficiency": "sufficient" if substrate_matched else "not_checked_or_insufficient",
        "provider_necessity": provider_necessity,
    }


def route_message(
    mode: str,
    message: str,
    pasted_text: str = "",
    approve: bool = False,
    history: list[dict[str, str]] | None = None,
    *,
    execute_local_model: bool = False,
    provider_approved: bool = False,
    provider_transport: Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]] | None = None,
) -> dict[str, Any]:
    if mode not in MODES:
        mode = "Conversation"
    if mode == "Conversation":
        if provider_approved:
            payload = execute_gpt_support_request(message, history, transport=provider_transport)
            payload["intent"] = classify_intent(message)
            payload["confidence_decision"] = {
                "confidence": payload["confidence_score"],
                "evidence_quality": payload["confidence"],
                "retrieval_sufficiency": "provider_support_requested_by_user",
                "provider_necessity": "approved_by_user_for_this_turn",
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            return payload
        if message.strip().lower() in {"ask gpt", "ask gpt for supporting information", "yes ask gpt"}:
            prior_user = [item.get("content", "") for item in (history or []) if item.get("role") == "user" and item.get("content")]
            target = prior_user[-1] if prior_user else message
            payload = build_gpt_approval_preview(target, history)
            payload["intent"] = classify_intent(target)
            payload["confidence_decision"] = {
                "confidence": 0.0,
                "evidence_quality": "pending_explicit_provider_approval",
                "retrieval_sufficiency": "insufficient_locally",
                "provider_necessity": "available_only_after_user_approval",
            }
            payload["escalation_plan"] = build_escalation_plan(target)
            payload["mode_router_flags"] = ROUTER_FLAGS
            return payload
        concept = query_approved_concepts(message)
        substrate = query_noncanonical_substrate(message)
        if concept["matched"]:
            payload = {
                "mode": mode,
                "route": "developmental_concept_memory",
                "answer": concept["answer"],
                "confidence": "grounded_in_approved_noncanonical_concept",
                "confidence_score": 0.92,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": concept["matches"],
            }
        elif substrate["matched"]:
            payload = {
                "mode": mode,
                "route": "substrate_first_conversation",
                "answer": substrate["answer"],
                "confidence": "grounded_in_noncanonical_substrate",
                "confidence_score": 0.9,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
            }
        else:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                ),
            }
        payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
        payload["escalation_plan"] = build_escalation_plan(message)
        payload["intent"] = classify_intent(message)
        payload["confidence_decision"] = confidence_engine(message, substrate["matched"])
    elif mode == "Ask Substrate":
        answer = answer_operator_question(message)
        payload = {"mode": mode, **answer}
    elif mode == "Evidence Review":
        preview = preview_evidence_ingest(pasted_text)
        extracted = extract_propositions(pasted_text)
        payload = {"mode": mode, "route": "evidence_review", "preview": preview, "extracted": extracted, "answer": f"Detected {extracted['candidate_count']} proposition candidate(s)."}
    elif mode == "Review Mode":
        extracted = extract_propositions(pasted_text)
        payload = {"mode": mode, "route": "operator_review", "answer": "Review extracted proposition candidates before approval.", "candidates": extracted["candidates"]}
    elif mode == "Memory Mode":
        extracted = extract_propositions(pasted_text)
        if approve:
            result = approve_propositions(extracted["candidates"])
            answer = f"Approved {result['approved_count']} noncanonical proposition(s)."
        else:
            result = {"approved_count": 0, "requires_operator_approval": True, "candidates": extracted["candidates"]}
            answer = "Memory Mode prepared candidates only. Approval is required before noncanonical storage."
        payload = {"mode": mode, "route": "memory_mode_noncanonical", "answer": answer, "result": result}
    elif mode == "Contradiction Check":
        answer = answer_operator_question("Are there contradictions in my knowledge?")
        payload = {"mode": mode, **answer}
    elif mode == "Research":
        plan = build_escalation_plan(message)
        payload = {"mode": mode, "route": "research_scaffold", "answer": "Research mode can plan local, web, and larger-model escalation, but external routes are disabled until explicitly gated.", "escalation_plan": plan}
    elif mode == "Investigation":
        payload = {"mode": mode, "route": "investigation_scaffold", "answer": "Investigation mode organizes questions, evidence, contradictions, and unresolved claims without enabling autonomous research."}
    elif mode == "Developer":
        payload = {"mode": mode, "route": "developer_scaffold", "answer": "Developer mode can reason about code and implementation plans locally, but it does not execute tools or change files from the UI."}
    elif mode == "Replay":
        snapshot = build_operator_snapshot()
        payload = {"mode": mode, "route": "replay_inspection", "answer": "Replay and rollback inspection is available.", "replay": snapshot["replay_rollback"]}
    elif mode == "Diagnostics":
        payload = {"mode": mode, "route": "diagnostics", "answer": "Runtime diagnostics snapshot.", "state": build_cognitive_state(), "developmental_memory": build_developmental_memory_state(), "flags": ROUTER_FLAGS}
    elif mode == "Failure Log":
        payload = {"mode": mode, "route": "failure_log_scaffold", "answer": "Use the RC1 observation controls to log operational friction. This mode does not auto-file issues."}
    elif mode == "Research Analyst":
        plan = build_escalation_plan(message)
        payload = {"mode": mode, "route": "research_analyst_scaffold", "answer": "Research Analyst mode can plan local/provider/web escalation, but external routes are disabled until explicitly gated.", "escalation_plan": plan}
    else:
        payload = {"mode": mode, "route": "frontier_app_assistant", "answer": "Frontier App Assistant mode uses approved Frontier substrate evidence when available and otherwise asks you to add evidence."}
    payload.update({
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "mode_router_flags": ROUTER_FLAGS,
    })
    return payload


def render_route(payload: dict[str, Any]) -> str:
    if payload.get("mode") == "Conversation":
        lines = [str(payload.get("answer", ""))]
        packet = payload.get("compact_support_packet")
        if payload.get("route") == "gpt_support_approval_preview" and isinstance(packet, dict):
            lines.extend([
                "",
                "If you say yes, I will send only a compact request: your current question, a few relevant recent turns, and any relevant approved local concepts.",
            ])
        offer = payload.get("supporting_information_offer")
        if isinstance(offer, dict) and offer.get("offered"):
            prompt = str(offer["prompt"])
            if prompt not in lines[0]:
                lines.extend(["", prompt])
            lines.append("Reply yes to approve that one provider request, or no to keep chatting locally.")
        local_offer = payload.get("local_model_offer")
        if isinstance(local_offer, dict) and local_offer.get("offered"):
            prompt = str(local_offer["prompt"])
            if prompt not in lines[0]:
                lines.extend(["", prompt])
            lines.append("Reply yes to ask the local model for this one question, or no to leave it unanswered.")
        if payload.get("memory_candidate"):
            candidate = payload["memory_candidate"]
            lines.extend([
                "",
                f"If this was useful, I can keep it as the reversible concept `{candidate.get('concept_name', 'Learned Concept')}`. Choose `Keep This Concept` or type `keep this concept`.",
            ])
        return "\n".join(lines)

    lines = [
        f"Mode: {payload.get('mode')}",
        f"Route: {payload.get('route')}",
        "",
        str(payload.get("answer", "")),
    ]
    if payload.get("escalation_plan"):
        plan = payload["escalation_plan"]
        lines.extend([
            "",
            "Escalation plan:",
            f"- intent: {plan['intent']}",
            f"- recommended routes: {', '.join(plan['recommended_routes'])}",
            f"- enabled now: {plan['enabled_now']}",
        ])
    if payload.get("confidence_decision"):
        confidence = payload["confidence_decision"]
        lines.extend([
            "",
            "Confidence:",
            f"- estimate: {confidence['confidence']}",
            f"- evidence: {confidence['evidence_quality']}",
            f"- provider need: {confidence['provider_necessity']}",
        ])
    lines.extend([
        "",
        "Safety:",
        f"- provider_calls_performed: {payload['provider_calls_performed']}",
        f"- web_search_performed: {payload['web_search_performed']}",
        f"- training_performed: {payload['training_performed']}",
        f"- canonical_write_performed: {payload['canonical_write_performed']}",
        f"- autonomous_action_performed: {payload['autonomous_action_performed']}",
    ])
    return "\n".join(lines)


def build_rc2_report() -> dict[str, Any]:
    cases = [
        route_message("Conversation", "What color is the sky?"),
        route_message("Conversation", "What color is water?"),
        route_message("Conversation", "What do you know about coding?"),
        route_message("Conversation", "What is the relation between Avogadro's number and quantum field theory?"),
        route_message("Evidence Review", "", "Project Frontier has AI workers."),
        route_message("Ask Substrate", "What do you know about Frontier?"),
        route_message("Research Analyst", "Tell me about beluga whales."),
    ]
    return {
        "phase": "RC2 Conversational Shell With DELTA Mode Router",
        "modes": MODES,
        "display_modes": DISPLAY_MODES,
        "cases": cases,
        "flags": ROUTER_FLAGS,
        "local_model_lane_selection_enabled": True,
        "local_model_execution_enabled_by_default": False,
        "useful_answer_memory_enabled": True,
        "useful_answer_memory_scope": "local_noncanonical_rc2_developmental_concept_store",
        "developmental_memory_state": build_developmental_memory_state(),
        "local_model_discovery": discover_local_model_lanes(),
        "safe": all(not case["provider_calls_performed"] and not case["training_performed"] and not case["canonical_write_performed"] for case in cases),
        "final_recommendation": "USE_RC2_CONVERSATIONAL_SHELL_AS_PRIMARY_UI_WITH_RC1_OPERATOR_MODE_AVAILABLE",
    }


def report_payloads() -> dict[str, dict[str, Any]]:
    base = build_rc2_report()
    return {
        "RC2_CONVERSATIONAL_ARCHITECTURE": {
            **base,
            "focus": "conversation is the product; governed runtime is the engine",
            "conversation_primary_interface": True,
            "operator_console_advanced": True,
        },
        "RC2_MODE_ROUTER": {
            "modes": DISPLAY_MODES,
            "default_mode": "Conversation",
            "manual_mode_required": False,
            "safe": base["safe"],
        },
        "RC2_INTENT_ROUTER": {
            "supported_intents": [
                "conversation",
                "question",
                "coding",
                "research",
                "planning",
                "memory",
                "evidence",
                "investigation",
                "analysis",
                "document",
                "image",
                "diagnostics",
            ],
            "examples": [classify_intent(text) for text in ["What color is the sky?", "Remember that.", "Analyze this invoice.", "Show diagnostics."]],
            "safe": True,
        },
        "RC2_MEMORY_EXPERIENCE": {
            "technical_phrase_replaced": "Approve To Noncanonical Substrate",
            "user_facing_phrase": "Would you like me to remember this?",
            "default_storage": "none_until_user_approval",
            "advanced_workflow_preserved": True,
            "canonical_writes_enabled": False,
        },
        "RC2_OPERATOR_SEPARATION": {
            "default_tab": "Conversation",
            "advanced_tab": "Advanced / Operator Console",
            "operator_console_preserved": True,
            "regular_user_required_to_understand_substrate": False,
        },
        "RC2_UI_REVIEW": {
            "conversation_first": True,
            "visible_modes": DISPLAY_MODES,
            "reduced_default_implementation_terminology": True,
            "remaining_gap": "local model lane selection is wired; model execution, web, and GPT/provider routes remain gated/off by default",
            "safe": True,
        },
        "RC2_LOCAL_MODEL_ROUTING": {
            "local_model_lane_selection_enabled": True,
            "model_registry": "integration.model_runtime.model_registry",
            "discovery": discover_local_model_lanes(),
            "sample_selections": [
                select_model_lane("What is fire?", "conversation"),
                select_model_lane("Debug this Python function", "coding"),
                select_model_lane("Research beluga whales", "external_knowledge_request"),
            ],
            "model_execution_enabled_by_default": False,
            "provider_calls_performed": False,
            "safe": True,
        },
        "RC2_SELECTIVE_MEMORY_EXPERIMENT": {
            "enabled": True,
            "approval_paths": ["Keep This Concept button", "exact chat phrase: keep this concept"],
            "casual_yes_counts_as_memory_approval": False,
            "target_store": "data/rc2_developmental_memory/knowledge_concepts.jsonl",
            "canonical_writes_enabled": False,
            "training_enabled": False,
            "clear_store_confirmation": "DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE",
            "memory_state": build_developmental_memory_state(),
            "safe": True,
        },
        "RC2_MODEL_LANE_ROUTER": {
            "summary": "Automatic lane router selects everyday conversation, coding/technical, reasoning/analysis, planning, vision, concept extraction, or contradiction detection lanes from the existing model registry.",
            "discovery": discover_local_model_lanes(),
            "model_execution_enabled_by_default": False,
            "provider_calls_performed": False,
            "safe": True,
        },
        "RC2_DEVELOPMENTAL_CONCEPT_FORMATION": {
            "summary": "Useful answers become candidate concepts with propositions, related concepts, uncertainty, provenance, rollback handle, and approval status.",
            "sample_candidate": extract_candidate_concept(
                question="What is fire?",
                answer=DIRECT_LOCAL_ANSWERS["fire_definition"]["answer"],
                source_model_lane=select_model_lane("What is fire?"),
            ),
            "canonical_writes_enabled": False,
            "training_enabled": False,
            "safe": True,
        },
        "RC2_MEMORY_STORE_SEPARATION": {
            "summary": "Conversation, personal, and knowledge memory are separate. Default concept storage goes to knowledge memory unless the user makes it personal.",
            "stores": discover_memory_store_separation(),
            "safe": True,
        },
        "RC2_CONCEPT_GRAPH_LINKING": {
            "summary": "Approved concepts create noncanonical concept records, relation edges, contradiction records, replay items, and rollback handles.",
            "memory_state": build_developmental_memory_state(),
            "first_pass_contradiction_rules": ["X is Y vs X is not Y", "should X vs should not X", "can X vs cannot X", "automatic vs requires approval/manual review", "always vs not always", "must vs must not"],
            "safe": True,
        },
        "RC2_CONCEPT_APPROVAL_UX": {
            "summary": "The UI keeps the same layout but offers Keep This Concept, Not now/Discard/Forget after this chat, and compact ask-GPT approval preview paths.",
            "approval_required": True,
            "casual_yes_counts_as_approval": False,
            "safe": True,
        },
        "RC2_DEVELOPMENTAL_LIFECYCLE": {
            "lifecycle": ["Conversation", "Candidate Concept", "Operator Approval", "Knowledge Graph", "Replay", "Consolidation", "Curriculum", "Competency Tests", "Training Packet", "Distillation", "Better Base Model"],
            "invariant": "Neural training is a graduation event, not a day-to-day learning mechanism.",
            "day_to_day_learning": "governed concept formation, operator approval, knowledge graph integration, replay, consolidation, curriculum construction, and competency testing",
            "safe": True,
        },
        "RC2_COMPACT_PROVIDER_CONSENT": {
            "summary": "GPT/API escalation is ask-first and preview-only in RC2. The packet carries only the current question, short relevant chat history, relevant approved concepts, routing reason, and desired answer format.",
            "sample_packet": build_compact_support_packet("What is the relation between Avogadro's number and quantum field theory?", []),
            "provider_calls_performed": False,
            "safe": True,
        },
    }


def write_rc2_report() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    payload = build_rc2_report()
    (REPORTS / "RC2_CONVERSATIONAL_MODE_ROUTER.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# RC2 Conversational Shell With DELTA Mode Router",
        "",
        "RC2 adds a conversational front door with selectable DELTA modes. It does not enable providers, web search, training, canonical writes, autonomous actions, production routing, HYB1 promotion, or Model B replacement.",
        "",
        "## Modes",
        *[f"- {mode}" for mode in MODES],
        "",
        "## Recommendation",
        f"`{payload['final_recommendation']}`",
        "",
    ]
    (REPORTS / "RC2_CONVERSATIONAL_MODE_ROUTER.md").write_text("\n".join(md), encoding="utf-8")
    for name, data in report_payloads().items():
        (REPORTS / f"{name}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (REPORTS / f"{name}.md").write_text(
            "\n".join([
                f"# {name.replace('_', ' ').title()}",
                "",
                f"Safe: `{data.get('safe', True)}`",
                "",
                f"Summary: `{data.get('focus', data.get('remaining_gap', data.get('default_mode', 'RC2 report')) )}`",
                "",
            ]),
            encoding="utf-8",
        )
    return payload
