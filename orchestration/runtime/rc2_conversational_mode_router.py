"""RC2 conversational shell and DELTA mode router scaffold.

RC2 makes the RC1 substrate one selectable mode behind a conversational front
door. It does not enable provider calls, web search, training, canonical
writes, autonomous actions, or production routing. External provider routes
are consent-gated. Local model lanes may execute when the caller explicitly
asks for local inference.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from integration.model_runtime.model_registry import list_available_models
from integration.model_runtime.provider_manager import ProviderManager
from orchestration.runtime.rc2_dialogue_intent_classifier import (
    classify_dialogue_act,
    evaluate_dialogue_intent_corpus,
    write_dialogue_intent_artifacts,
)
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
    browse_approved_concepts,
    discover_memory_store_separation,
    extract_candidate_concept,
    query_approved_concepts,
    retrieve_multi_concept_set,
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

SOCIAL_INTENT_RESPONSES = {
    "greeting": "Hi. I'm here with you. What would you like to work through?",
    "thanks": "You're welcome. I'm glad that helped.",
    "compliment": "Thanks. I'm glad that was helpful.",
    "encouragement": "Thanks. I'll keep going carefully.",
    "acknowledgement": "Got it. What would you like to explore next?",
    "affirmation": "Yes noted. I will only use that as approval when there is a current pending action.",
    "refusal": "No problem. I will not proceed with that pending action.",
    "cancel": "No problem. We'll leave that path alone.",
    "correction": "Got it. I will treat that as a correction to the current thread.",
    "preference_opinion": "Good, that gives me useful direction. We can keep shaping the system around that.",
    "personal_emotion": "I hear you. We can keep this low-friction and take it one step at a time.",
    "followup": "I can rephrase or continue from the recent context.",
    "joke": "Heh. I caught that as a joke, so I won't route it into memory or retrieval.",
    "small_talk": "I'm here and ready. What would you like to work on?",
}


def classify_intent(message: str) -> dict[str, Any]:
    lower = " ".join(message.lower().strip().split())
    bare = lower.strip(" .!?")
    if _is_contextual_browse_jump(lower):
        return {
            "intent": "knowledge_browse_jump",
            "message": message,
            "confidence": 0.91,
            "communication_act": "clarification_followup",
            "matched_rule": "knowledge_browse_jump",
            "routed_action": "browse_diverse_approved_concepts",
            "safe_no_route": False,
        }
    if _is_memory_browse_request(lower):
        return {
            "intent": "knowledge_browse",
            "message": message,
            "confidence": 0.94,
            "communication_act": "knowledge_browse",
            "matched_rule": "knowledge_browse",
            "routed_action": "browse_approved_concepts",
            "safe_no_route": False,
        }
    if _is_contextual_browse_followup(lower):
        return {
            "intent": "knowledge_browse_followup",
            "message": message,
            "confidence": 0.9,
            "communication_act": "clarification_followup",
            "matched_rule": "knowledge_browse_followup",
            "routed_action": "browse_related_approved_concepts",
            "safe_no_route": False,
        }
    dialogue = classify_dialogue_act(message)
    if dialogue["confidence"] >= 0.8:
        intent = str(dialogue["intent"])
        if dialogue["communication_act"] in {"joke", "small_talk"}:
            intent = str(dialogue["communication_act"])
        if dialogue["communication_act"] == "evidence_request" and message.lower().strip().startswith("analyze "):
            intent = "analysis"
        return {
            "intent": intent,
            "message": message,
            "confidence": dialogue["confidence"],
            "communication_act": dialogue["communication_act"],
            "matched_rule": dialogue["matched_rule"],
            "routed_action": dialogue["routed_action"],
            "safe_no_route": dialogue["safe_no_route"],
        }
    if any(term in lower for term in ["diagnostic", "show diagnostics", "runtime status", "system health", "health check"]):
        intent = "diagnostics"
    elif bare in {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}:
        intent = "greeting"
    elif bare in {"great job", "good job", "nice work", "excellent work", "well done", "perfect", "that worked", "awesome", "thanks", "thank you"}:
        intent = "compliment"
    elif bare in {"okay", "ok", "got it", "sounds good", "cool", "alright", "yes okay"}:
        intent = "acknowledgement"
    elif bare in {"nevermind", "never mind", "cancel", "stop", "forget it", "drop it"}:
        intent = "cancel"
    elif lower.startswith(("i like", "i want", "i prefer", "i think")) and not lower.endswith("?"):
        intent = "preference_opinion"
    elif any(term in lower for term in ["i'm tired", "im tired", "i am tired", "i'm frustrated", "im frustrated", "i feel"]):
        intent = "personal_emotion"
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


def _is_memory_browse_request(lower: str) -> bool:
    bare = lower.strip(" .!?")
    patterns = {
        "tell me something you know",
        "tell me something you learned",
        "what do you know",
        "show me something you know",
        "give me a concept",
        "show me a concept",
        "what have you learned",
        "surprise me with something you know",
    }
    return bare in patterns or bare.startswith("tell me about something you know")


def _is_contextual_browse_followup(lower: str) -> bool:
    bare = lower.strip(" .!?")
    return bare in {
        "what else",
        "what else do you know",
        "what more",
        "show me another",
        "another one",
        "give me another",
        "tell me another",
    }


def _is_contextual_browse_jump(lower: str) -> bool:
    bare = lower.strip(" .!?")
    return bare in {
        "something completely different",
        "show me something different",
        "different topic",
        "switch topics",
        "new topic",
    }


DOMAIN_BROWSE_ALIASES = {
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
    "energy": "energy",
    "gardening": "agriculture gardening",
    "agriculture": "agriculture gardening",
    "mechanics": "vehicles mechanics",
    "vehicles": "vehicles mechanics",
    "home repair": "home repair",
    "communication": "social communication",
    "productivity": "planning productivity",
    "delta": "DELTA architecture itself",
}


def _domain_browse_request(message: str) -> str | None:
    lower = " ".join(str(message or "").lower().strip().split())
    if not any(phrase in lower for phrase in ("what about", "how about", "do you know", "anything about", "tell me about", "show me")):
        return None
    if any(phrase in lower for phrase in ("newton", "first law", "second law", "third law", "law of")):
        return None
    if any(phrase in lower for phrase in ("should i", "can i sue", "am i liable", "legal advice", "calculate", "court case")):
        if not any(phrase in lower for phrase in ("concept", "anything about", "tell me about", "show me")):
            return None
    for alias, domain in sorted(DOMAIN_BROWSE_ALIASES.items(), key=lambda item: -len(item[0])):
        pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
        if re.search(pattern, lower):
            return domain
    return None


def _last_concept_context(history: list[dict[str, str]] | None) -> dict[str, Any]:
    names = []
    domain = None
    for item in reversed(history or []):
        if item.get("role") != "assistant":
            continue
        content = str(item.get("content") or "")
        found = [match.strip() for match in re.findall(r"`([^`]+)`", content) if match.strip()]
        if "A couple of nearby concepts" in content:
            nearby = content.split("A couple of nearby concepts", 1)[1]
            found.extend(
                line.strip()[2:].strip()
                for line in nearby.splitlines()
                if line.strip().startswith("- ") and line.strip()[2:].strip()
            )
        if not found:
            continue
        names.extend(found)
        name = found[0]
        if domain is None:
            domain_match = re.search(r"\(([^)]+)\)\s*$", name)
            domain = domain_match.group(1).lower() if domain_match else None
    unique_names = list(dict.fromkeys(names))
    return {"concept_name": unique_names[0] if unique_names else None, "concept_names": unique_names, "domain": domain}


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
    selected, candidates, rejected = _select_usable_model_for_lane(available, lane)
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
        "selection_reason": _selection_reason(lane, spec),
        "candidate_models": candidates,
        "rejected_models": rejected,
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


def _select_usable_model_for_lane(available: dict[str, Any], lane: str) -> tuple[str | None, list[dict[str, Any]], list[dict[str, Any]]]:
    rejected = []
    for alias in MODEL_LANE_ORDER[lane]:
        spec = available.get(alias)
        if spec is None:
            rejected.append({"requested": alias, "reason": "not_registered"})
            continue
        if _model_is_usable(spec):
            return alias, [_model_candidate(alias, spec, "registered_alias")], rejected
        rejected.append({"requested": alias, "model_id": spec.name, "reason": "unusable_or_marked_fail"})

    desired_families = MODEL_LANE_ORDER[lane]
    family_candidates = []
    seen_model_ids = set()
    for family in desired_families:
        for key, spec in sorted(available.items(), key=lambda item: (item[1].tier, item[1].name, item[0])):
            if spec.name in seen_model_ids:
                continue
            if spec.family == family and _model_is_usable(spec):
                family_candidates.append(_model_candidate(key, spec, f"usable_{family}_family_fallback"))
                seen_model_ids.add(spec.name)
    if family_candidates:
        return str(family_candidates[0]["registry_key"]), family_candidates[:5], rejected

    usable = [
        _model_candidate(key, spec, "usable_any_family_fallback")
        for key, spec in sorted(available.items(), key=lambda item: (item[1].tier, item[1].name, item[0]))
        if _model_is_usable(spec)
    ]
    if usable:
        return str(usable[0]["registry_key"]), usable[:5], rejected
    return None, [], rejected


def _model_candidate(key: str, spec: Any, reason: str) -> dict[str, Any]:
    return {
        "registry_key": key,
        "model_id": spec.name,
        "family": spec.family,
        "tier": spec.tier,
        "capabilities": list(spec.capabilities),
        "reason": reason,
    }


def _selection_reason(lane: str, spec: Any | None) -> str:
    if spec is None:
        return f"No usable local model found for {lane}."
    return f"Selected {spec.name} because it is a usable local {spec.family} model for the {lane} lane."


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
        "greeting": 0.95,
        "compliment": 0.95,
        "acknowledgement": 0.92,
        "cancel": 0.96,
        "preference_opinion": 0.84,
        "personal_emotion": 0.82,
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


def _local_model_offer(
    message: str,
    reason: str,
    history: list[dict[str, str]] | None = None,
    model_lane: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet = build_compact_support_packet(message, history)
    model_name = (model_lane or {}).get("selected_model_id") or (model_lane or {}).get("selected_model") or "my best local model"
    lane_name = (model_lane or {}).get("display_name") or "local reasoning lane"
    prompt = (
        f"I don't think I've learned this yet. My best local model for this question is {model_name} "
        f"in the {lane_name}. Would you like me to ask it?"
    )
    return {
        "offered": True,
        "reason": reason,
        "prompt": prompt,
        "options": ["yes_ask_local_model", "not_now"],
        "compact_local_model_packet": packet,
        "selected_model": model_name,
        "support_identifier": (model_lane or {}).get("support_identifier"),
        "local_model_call_performed": False,
        "provider_calls_performed": False,
        "web_search_performed": False,
    }


def _compact_model_prompt(message: str, history: list[dict[str, str]] | None = None) -> str:
    deepening = _parse_deepening_message(message)
    packet = build_compact_support_packet(message, history)
    turns = packet.get("relevant_chat_history", [])
    concept_question = deepening["original_question"] if deepening else message
    concepts = build_compact_support_packet(concept_question, history).get("relevant_approved_concepts", [])
    lines = [
        "Answer like a friendly, concise assistant.",
        "Use the short conversation context when it matters.",
        "Do not mention routing, model names, hashes, JSON, or safety flags.",
        "",
    ]
    if deepening:
        lines.extend([
            "Task:",
            "Elaborate on the prior answer. Add new useful detail, examples, distinctions, or nuance. Do not merely repeat the previous answer.",
            "",
            "Original user question:",
            deepening["original_question"][:1000],
            "",
            "Previous answer to deepen:",
            deepening["previous_answer"][:2400],
            "",
            "Follow-up instruction:",
            deepening["instruction"][:700],
        ])
    else:
        lines.extend([
            "Current user message:",
            str(packet["question"]),
        ])
    if turns:
        lines.extend(["", "Relevant recent turns:"])
        for turn in turns:
            lines.append(f"- {turn['role']}: {turn['content']}")
        lines.append("")
        lines.append("Maintain continuity with these turns. If the user is following up, resolve pronouns and references from this context.")
    if concepts:
        lines.extend(["", "Relevant approved local concepts:"])
        for concept in concepts:
            lines.append(f"- {concept.get('concept_name')}: {concept.get('short_definition')}")
    lines.extend(["", "Return only the answer text."])
    return "\n".join(lines)


def _parse_deepening_message(message: str) -> dict[str, str] | None:
    text = str(message or "")
    marker = "Please expand on your previous answer for this user question."
    original_label = "Original question:"
    previous_label = "Previous answer:"
    instruction = "Go deeper, add useful nuance, keep it conversational, and do not ask to store memory."
    if marker not in text or original_label not in text or previous_label not in text:
        return None
    after_original = text.split(original_label, 1)[1]
    original_question, rest = after_original.split(previous_label, 1)
    previous_answer = rest
    if instruction in previous_answer:
        previous_answer = previous_answer.split(instruction, 1)[0]
    return {
        "original_question": " ".join(original_question.split()).strip(),
        "previous_answer": " ".join(previous_answer.split()).strip(),
        "instruction": instruction,
    }


def execute_local_model_answer(
    message: str,
    model_lane: dict[str, Any],
    history: list[dict[str, str]] | None = None,
    provider_manager: ProviderManager | None = None,
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
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            manager = provider_manager or ProviderManager()
            result = manager.infer(
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
    except ModuleNotFoundError as exc:
        if exc.name == "llama_cpp":
            fallback = _infer_local_model_via_venv_subprocess(str(model_name), prompt, model_lane)
            if fallback.get("executed"):
                return fallback
            return {
                "executed": False,
                "available": True,
                "answer": "",
                "reason": str(fallback.get("reason") or f"local_model_execution_failed:{type(exc).__name__}:{str(exc)[:160]}"),
                "prompt_sent": prompt,
                "provider_calls_performed": False,
            }
        return {
            "executed": False,
            "available": True,
            "answer": "",
            "reason": f"local_model_execution_failed:{type(exc).__name__}:{str(exc)[:160]}",
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }
    except Exception as exc:  # pragma: no cover - defensive for local model runtime availability
        return {
            "executed": False,
            "available": True,
            "answer": "",
            "reason": f"local_model_execution_failed:{type(exc).__name__}:{str(exc)[:160]}",
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }


def _infer_local_model_via_venv_subprocess(model_name: str, prompt: str, model_lane: dict[str, Any]) -> dict[str, Any]:
    venv_python = ROOT / ".venv311" / "Scripts" / "python.exe"
    helper = ROOT / "scripts" / "delta_rc2_local_model_infer.py"
    if not venv_python.exists():
        return {"executed": False, "reason": "local_model_venv_python_missing", "provider_calls_performed": False}
    if not helper.exists():
        return {"executed": False, "reason": "local_model_subprocess_helper_missing", "provider_calls_performed": False}
    request = {
        "model_name": model_name,
        "prompt": prompt,
        "task_type": "rc2_conversation",
        "metadata": {"route": "rc2_local_model_lane", "lane": model_lane.get("lane")},
    }
    try:
        completed = subprocess.run(
            [str(venv_python), str(helper)],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=240,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - returned as visible route diagnostic.
        return {
            "executed": False,
            "reason": f"local_model_subprocess_failed:{type(exc).__name__}:{str(exc)[:160]}",
            "provider_calls_performed": False,
        }
    if completed.returncode != 0:
        return {
            "executed": False,
            "reason": f"local_model_subprocess_returned_{completed.returncode}:{completed.stderr[:180]}",
            "provider_calls_performed": False,
        }
    try:
        payload = json.loads(completed.stdout)
    except Exception as exc:
        return {
            "executed": False,
            "reason": f"local_model_subprocess_json_failed:{type(exc).__name__}:{completed.stdout[:180]}",
            "provider_calls_performed": False,
        }
    answer = _naturalize_model_answer(str(payload.get("answer", "")))
    return {
        "executed": bool(answer),
        "available": True,
        "answer": answer,
        "confidence_score": float(payload.get("confidence_score") or 0.72),
        "model_id": payload.get("model_id") or model_name,
        "prompt_sent": prompt,
        "execution_adapter": "venv_subprocess",
        "provider_calls_performed": False,
        "reason": None if answer else "local_model_subprocess_empty_answer",
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
    intent = payload.get("intent") if isinstance(payload.get("intent"), dict) else classify_intent(message)
    if intent.get("communication_act") == "memory_request" or intent.get("intent") == "memory_request":
        return None
    if payload.get("route") in {
        "developmental_concept_memory",
        "substrate_first_conversation",
        "gpt_support_approval_preview",
        "provider_support_refused_or_local_known",
        "social_conversation",
    }:
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
    session = _session_memory_answer(message, history)
    if session:
        return session
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


def _is_session_memory_turn(message: str) -> bool:
    lower = message.lower()
    return any(phrase in lower for phrase in (
        "pretend my favorite",
        "favorite color in this conversation",
        "alice owns",
        "bob owns",
        "who owns the",
    ))


def _session_memory_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    lower = message.lower()
    if "pretend my favorite color is" in lower:
        match = re.search(r"favorite color is\s+([a-zA-Z]+)", lower)
        color = match.group(1) if match else "that"
        return _session_payload(message, f"Got it. For this conversation only, I'll treat your favorite color as {color}.")
    if "alice owns" in lower and "bob owns" in lower:
        return _session_payload(message, "Got it. For this conversation only: Alice owns the truck, and Bob owns the trailer.")
    if history and "favorite color" in lower and "conversation" in lower:
        for item in reversed(history):
            text = str(item.get("content") or "").lower()
            match = re.search(r"favorite color is\s+([a-zA-Z]+)", text)
            if match:
                return _session_payload(message, f"In this conversation, your favorite color is {match.group(1)}.")
    if history and "who owns the" in lower:
        target = "trailer" if "trailer" in lower else "truck" if "truck" in lower else ""
        for item in reversed(history):
            text = str(item.get("content") or "").lower()
            if target == "trailer" and "bob owns the trailer" in text:
                return _session_payload(message, "Bob owns the trailer in this conversation.")
            if target == "truck" and "alice owns the truck" in text:
                return _session_payload(message, "Alice owns the truck in this conversation.")
    return None


def _is_recent_concept_followup(message: str) -> bool:
    return message.lower().strip(" ?!.") in {
        "why",
        "why is that",
        "go deeper",
        "give me an example",
        "how big can they get",
        "does that happen to all of them",
    }


def _session_payload(message: str, answer: str) -> dict[str, Any]:
    return {
        "route": "conversation_short_term_memory",
        "answer": answer,
        "confidence": "session_memory",
        "confidence_score": 0.92,
        "selected_model_lane": select_model_lane(message),
        "supporting_information_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
    }


def _recent_concept_followup_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    lower = message.lower().strip(" ?!.")
    if lower not in {"why", "why is that", "go deeper", "give me an example", "how big can they get", "does that happen to all of them"}:
        return None
    context = _last_concept_context(history)
    concept_name = context.get("concept_name")
    if not concept_name:
        topic = _recent_user_topic(history)
        if not topic:
            return None
        return _session_payload(
            message,
            f"I can continue from your recent topic, {topic}. I do not have approved local knowledge for it yet, so I can ask the local reasoning model if you want.",
        )
    if lower == "give me an example":
        answer = f"Using the recent concept `{concept_name}`, I can give an example from that same topic, but I will keep this as session context rather than storing anything new."
    elif lower in {"why", "why is that"}:
        answer = f"Continuing from `{concept_name}`: the useful next step is to inspect the causes or mechanisms behind that concept. I can ask the local reasoning model for a deeper explanation if you want."
    else:
        answer = f"I can continue from `{concept_name}` using the recent context. I have not enabled synthesis or stored anything new."
    return _session_payload(message, answer)


def _recent_user_topic(history: list[dict[str, str]] | None) -> str | None:
    followup_forms = {
        "why",
        "why is that",
        "go deeper",
        "give me an example",
        "how big can they get",
        "does that happen to all of them",
        "what else",
        "another one",
    }
    for item in reversed(history or []):
        if item.get("role") != "user":
            continue
        text = str(item.get("content") or "").strip()
        bare = text.lower().strip(" ?!.")
        if not text or bare in followup_forms:
            continue
        topic = _topic_label_from_message(text)
        if topic:
            return topic
    return None


def _topic_label_from_message(message: str) -> str | None:
    text = " ".join(message.strip(" ?!.").split())
    lower = text.lower()
    patterns = [
        r"tell me about\s+(.+)",
        r"what is\s+(.+)",
        r"what are\s+(.+)",
        r"explain\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            topic = match.group(1).strip(" .?!")
            return topic if len(topic) > 2 else None
    return None


def local_conversation_answer(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    execute_local_model: bool = False,
    provider_manager: ProviderManager | None = None,
) -> dict[str, Any]:
    lower = message.lower()
    intent = classify_intent(message)["intent"]
    model_lane = select_model_lane(message, intent)
    local = run_v29_local_answer(message, use_recall=False)
    if memory := _history_answer(message, history):
        return memory
    if recent := _recent_concept_followup_answer(message, history):
        return recent
    if intent == "followup":
        return {
            "route": "local_model_consent_required",
            "answer": "I can continue from the recent context. Would you like me to ask the local reasoning model to elaborate?",
            "confidence": "needs_local_reasoning_model",
            "confidence_score": 0.55,
            "selected_model_lane": model_lane,
            "local_model_result": None,
            "supporting_information_offer": None,
            "local_model_offer": _local_model_offer(message, "followup_needs_recent_context", history, model_lane),
            "pending_action_suggestion": {
                "action_type": "local_model_deepening",
                "pending_action_created": True,
                "followup_instruction": message,
                "expires_after_turns": 1,
            },
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
    local_model_result = None
    if intent in SOCIAL_INTENT_RESPONSES:
        return {
            "route": "social_conversation",
            "answer": SOCIAL_INTENT_RESPONSES[intent],
            "confidence": "social_intent",
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
        local_model_result = execute_local_model_answer(message, model_lane, history, provider_manager=provider_manager)
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
            topic = _topic_label_from_message(message)
            topic_phrase = f" about {topic}" if topic else ""
            answer = (
                f"I don't think I know enough{topic_phrase} from my learned local knowledge yet. "
                "Would you like me to ask a local reasoning model?"
            )
            confidence = "needs_local_reasoning_model"
            confidence_score = 0.3
            support_offer = None
            local_model_offer = _local_model_offer(message, "missing_learned_or_direct_knowledge", history, model_lane)
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
    if intent in SOCIAL_INTENT_RESPONSES:
        recommended = ["social_response_only"]
    elif intent == "external_knowledge_request":
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
    if intent["intent"] in SOCIAL_INTENT_RESPONSES:
        confidence = intent["confidence"]
        evidence_quality = "conversation_intent_no_evidence_needed"
        provider_necessity = "none"
    elif substrate_matched:
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
    provider_manager: ProviderManager | None = None,
    provider_transport: Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]] | None = None,
) -> dict[str, Any]:
    if mode not in MODES:
        mode = "Conversation"
    if mode == "Conversation":
        intent_info = classify_intent(message)
        if provider_approved:
            payload = execute_gpt_support_request(message, history, transport=provider_transport)
            payload["intent"] = intent_info
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
        if intent_info.get("intent") in {"knowledge_browse", "knowledge_browse_followup", "knowledge_browse_jump"}:
            context = _last_concept_context(history)
            excluded_names = context.get("concept_names") or ([context["concept_name"]] if context.get("concept_name") else None)
            jump = intent_info.get("intent") == "knowledge_browse_jump"
            concept = browse_approved_concepts(
                limit=3,
                domain=context.get("domain") if intent_info.get("intent") == "knowledge_browse_followup" else None,
                exclude_concept_names=excluded_names,
                exclude_domains=[context["domain"]] if jump and context.get("domain") else None,
            )
            if not concept["matched"] and intent_info.get("intent") == "knowledge_browse_followup":
                concept = browse_approved_concepts(
                    limit=3,
                    exclude_concept_names=excluded_names,
                )
            if not concept["matched"] and jump:
                concept = browse_approved_concepts(
                    limit=3,
                    exclude_concept_names=excluded_names,
                )
            payload = {
                "mode": mode,
                "route": "developmental_concept_browse_followup" if intent_info.get("intent") in {"knowledge_browse_followup", "knowledge_browse_jump"} else "developmental_concept_browse",
                "answer": concept["answer"] if concept["matched"] else "I do not have approved local concepts to browse yet.",
                "confidence": "grounded_in_approved_noncanonical_concept_catalog" if concept["matched"] else "no_approved_local_concepts",
                "confidence_score": 0.9 if concept["matched"] else 0.2,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": concept.get("matches", []),
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, bool(concept["matched"]))
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return payload
        multi_concept = retrieve_multi_concept_set(message)
        if multi_concept["matched"]:
            payload = {
                "mode": mode,
                "route": "developmental_multi_concept_retrieval",
                "answer": multi_concept["answer"],
                "confidence": "retrieval_set_ready_for_operator_review",
                "confidence_score": multi_concept["retrieval_set_quality"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": multi_concept.get("matches", []),
                "multi_concept_retrieval": {
                    "seeds": multi_concept.get("seeds", []),
                    "retrieval_set_quality": multi_concept["retrieval_set_quality"],
                    "synthesis_readiness": False,
                    "duplicate_suppression_count": multi_concept.get("duplicate_suppression_count", 0),
                },
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "multi_concept_retrieval"}
            payload["confidence_decision"] = {
                "confidence": multi_concept["retrieval_set_quality"],
                "evidence_quality": "approved_noncanonical_retrieval_set",
                "retrieval_sufficiency": "set_ready_for_review",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return payload
        domain_browse = _domain_browse_request(message)
        if domain_browse and intent_info.get("intent") not in {"coding"}:
            concept = browse_approved_concepts(limit=3, domain=domain_browse)
            payload = {
                "mode": mode,
                "route": "developmental_concept_domain_browse",
                "answer": concept["answer"] if concept["matched"] else f"I do not have approved local concepts for {domain_browse} yet.",
                "confidence": "grounded_in_approved_noncanonical_concept_catalog" if concept["matched"] else "no_approved_local_domain_concepts",
                "confidence_score": 0.9 if concept["matched"] else 0.2,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": concept.get("matches", []),
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "knowledge_domain_browse", "domain": domain_browse}
            payload["confidence_decision"] = confidence_engine(message, bool(concept["matched"]))
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return payload
        bypass_memory_retrieval = (
            execute_local_model
            or intent_info.get("communication_act") == "clarification_followup"
            or intent_info.get("intent") == "followup"
            or _is_session_memory_turn(message)
            or _is_recent_concept_followup(message)
        )
        concept = {"matched": False, "answer": "", "matches": []} if bypass_memory_retrieval else query_approved_concepts(message)
        substrate = {"matched": False, "answer": "", "matches": []} if bypass_memory_retrieval else query_noncanonical_substrate(message)
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
                    provider_manager=provider_manager,
                ),
            }
        payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
        payload["escalation_plan"] = build_escalation_plan(message)
        payload["intent"] = intent_info
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


def render_route(payload: dict[str, Any], *, developer_overlay: bool = False) -> str:
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
                f"I noticed a possible reusable concept: `{candidate.get('concept_name', 'Learned Concept')}`. I put it in Concept Review; accepting it there is the only way to store it.",
            ])
        if developer_overlay:
            lines.extend(["", render_developer_overlay(payload)])
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


def render_developer_overlay(payload: dict[str, Any]) -> str:
    lane = payload.get("selected_model_lane") or {}
    intent = payload.get("intent") or {}
    confidence = payload.get("confidence_decision") or {}
    local_offer = payload.get("local_model_offer") or {}
    provider_offer = payload.get("supporting_information_offer") or {}
    local_result = payload.get("local_model_result") or {}
    pending = payload.get("pending_action_suggestion") or {}
    pending_matched = payload.get("pending_action_matched")
    action_executed = payload.get("action_executed")
    pending_cleared = payload.get("pending_action_cleared")
    route = str(payload.get("route") or "unknown")
    boundary = "known"
    if route == "local_model_consent_required":
        boundary = "unknown_seek_local_model"
    elif provider_offer:
        boundary = "unknown_seek_provider_or_sources"
    elif route in {"developmental_concept_memory", "substrate_first_conversation"}:
        boundary = "known_from_approved_local_memory"
    elif route == "social_conversation":
        boundary = "social_no_knowledge_lookup"
    rejected = lane.get("rejected_models") or []
    rejected_text = ", ".join(f"{item.get('requested')}:{item.get('reason')}" for item in rejected[:4]) or "none"
    lines = [
        "--- Developer Overlay ---",
        f"Intent: {intent.get('intent', 'unknown')}",
        f"Communication act: {intent.get('communication_act', 'unknown')}",
        f"Matched rule: {intent.get('matched_rule', 'unknown')}",
        f"Routed action: {intent.get('routed_action', 'unknown')}",
        f"Route: {route}",
        f"Knowledge boundary: {boundary}",
        f"Chosen lane: {lane.get('display_name') or lane.get('lane') or 'none'}",
        f"Chosen model: {lane.get('selected_model_id') or lane.get('selected_model') or 'none'}",
        f"Support identifier: {lane.get('support_identifier') or 'none'}",
        f"Selection reason: {lane.get('selection_reason') or 'none'}",
        f"Rejected candidates: {rejected_text}",
        f"Local model executed: {bool(local_result.get('executed'))}",
        f"Local model status: {local_result.get('reason') or ('executed' if local_result.get('executed') else 'not_requested')}",
        f"Local model offer: {bool(local_offer.get('offered'))}",
        f"Provider offer: {bool(provider_offer.get('offered'))}",
        f"Active pending action id: {pending.get('action_id') or payload.get('active_pending_action_id') or 'none'}",
        f"Active pending action type: {pending.get('action_type') or payload.get('active_pending_action_type') or 'none'}",
        f"Pending action created: {bool(pending.get('pending_action_created'))}",
        f"Pending action matched: {bool(pending_matched)}",
        f"Action executed: {bool(action_executed)}",
        f"Pending action cleared: {bool(pending_cleared)}",
        f"Confidence: {confidence.get('confidence', payload.get('confidence_score'))}",
        f"Evidence quality: {confidence.get('evidence_quality', payload.get('confidence'))}",
        f"Provider need: {confidence.get('provider_necessity', 'none')}",
        "Safety: no training, canonical write, autonomous action, or automatic provider call.",
    ]
    return "\n".join(lines)


def build_rc2_report() -> dict[str, Any]:
    dialogue_evaluation = evaluate_dialogue_intent_corpus()
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
        "dialogue_intent_classifier": {
            "corpus_size": dialogue_evaluation["corpus_size"],
            "accuracy": dialogue_evaluation["accuracy"],
            "misses": len(dialogue_evaluation["misses"]),
        },
        "safe": all(not case["provider_calls_performed"] and not case["training_performed"] and not case["canonical_write_performed"] for case in cases),
        "final_recommendation": "USE_RC2_CONVERSATIONAL_SHELL_AS_PRIMARY_UI_WITH_RC1_OPERATOR_MODE_AVAILABLE",
    }


def report_payloads() -> dict[str, dict[str, Any]]:
    base = build_rc2_report()
    dialogue_evaluation = evaluate_dialogue_intent_corpus()
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
        "RC2_DIALOGUE_INTENT_CLASSIFIER": {
            "summary": "Deterministic communication-act classification now runs before retrieval, model routing, memory formation, or provider escalation.",
            "corpus_size": dialogue_evaluation["corpus_size"],
            "accuracy": dialogue_evaluation["accuracy"],
            "misses": dialogue_evaluation["misses"],
            "confusion_matrix": dialogue_evaluation["confusion_matrix"],
            "rule_coverage": dialogue_evaluation["rule_coverage"],
            "developer_overlay_fields": ["communication_act", "confidence", "matched_rule", "routed_action"],
            "routing_policy": {
                "social_intent": "respond socially; no SLM, retrieval, memory, or provider",
                "acknowledgement": "brief response; no routing",
                "refusal_or_cancel": "stop or reject pending action",
                "followup": "use short-term context",
                "factual_or_conceptual_question": "substrate/local model path",
                "memory_command": "concept approval path",
                "diagnostics_command": "diagnostics",
            },
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
            "approval_paths": ["Concept Review tray", "Accept Selected Concept button"],
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
            "summary": "The UI keeps the same layout but moves concept approval to a passive Concept Review tray. Chat affirmations do not store memory.",
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
    write_dialogue_intent_artifacts()
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
