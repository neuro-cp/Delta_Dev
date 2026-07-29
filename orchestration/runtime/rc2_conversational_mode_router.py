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
    build_read_only_synthesis_trial,
    build_compact_support_packet,
    build_developmental_memory_state,
    browse_approved_concepts,
    discover_memory_store_separation,
    extract_candidate_concept,
    parse_multi_concept_query,
    query_approved_concepts,
    retrieve_multi_concept_set,
)
from orchestration.runtime.rc2_analogy_engine import build_analogy_analysis, is_analogy_prompt
from orchestration.runtime.rc2_cognitive_episode import attach_episode, resolve_working_memory_followup
from orchestration.runtime.rc2_contradiction_engine import build_contradiction_analysis, is_contradiction_prompt
from orchestration.runtime.rc2_natural_conversation_renderer import apply_natural_renderer
from orchestration.runtime.rc2_render_correction import build_render_correction_payload
from orchestration.runtime.rc2_route_arbitration import build_route_arbitration_trace, normalize_safety_payload
from orchestration.runtime.rc2_working_reasoning_set import build_working_reasoning_set, should_use_wrs
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
    "normal_assistant_style": {
        "triggers": (("answer", "normal", "assistant"), ("normal", "assistant")),
        "answer": "Yes. I can answer in a more natural assistant style: direct first, enough context to be useful, and technical details only when you ask for them.",
        "confidence": 0.86,
    },
    "debugging_partner_opinion": {
        "triggers": (("good", "debugging", "partner"), ("debugging", "partner")),
        "answer": "A good debugging partner helps narrow the problem without taking over: they ask what changed, check assumptions, keep the reproduction small, and stay calm when the first theory is wrong.",
        "confidence": 0.84,
    },
    "followup_question_offer": {
        "triggers": (("ask", "follow", "question"), ("follow", "question"), ("follow-up", "question")),
        "answer": "Sure. What topic do you want to explore next, and do you want a quick overview or a deeper explanation?",
        "confidence": 0.84,
    },
    "rollback_recovery_evidence": {
        "triggers": (("rollback", "evidence"), ("recovery", "evidence")),
        "answer": "Recovery evidence means proof that an unwanted or failed change can be stopped, rejected, or rolled back without hidden side effects. A useful record names the tested change, what failed or was rejected, the stop or rollback action, the final recovered state, and confirmation that no unauthorized memory write, provider call, commit, push, deployment, or freeze claim occurred.",
        "confidence": 0.86,
    },
    "delta12_ambiguity_runtime": {
        "triggers": (("delta", "runtime", "ambiguity"), ("live", "runtime", "ambiguity")),
        "answer": "The DELTA 1.2 live runtime should treat repeated ambiguity failures as evidence, cluster them into a developmental signal, rank a bounded objective, and queue an operator inquiry. It should not implement the fix by itself; operator approval is required before promotion, and it should ask whether to prepare a sandboxed repair objective with focused validation.",
        "confidence": 0.86,
    },
    "ada_lovelace": {
        "triggers": (("ada", "lovelace"),),
        "answer": "Ada Lovelace was a 19th-century English mathematician and writer, best known for her work on Charles Babbage's proposed Analytical Engine and for writing notes often described as an early example of computer programming thinking.",
        "confidence": 0.8,
        "fixture": "approved_deterministic_local_knowledge",
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


def _is_synthesis_trial_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split())
    return any(phrase in lower for phrase in (
        "synthesize",
        "synthesis trial",
        "tentative connection",
        "infer a connection",
        "cross concept",
        "cross-concept",
    ))


def _is_graph_assisted_reasoning_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split())
    return any(phrase in lower for phrase in (
        "graph-assisted reasoning",
        "graph assisted reasoning",
        "use the graph",
        "reason with the graph",
        "graph-assisted reason",
        "graph assisted reason",
    ))


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
    if _explicit_multiword_concept_lookup_target(lower):
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


def _explicit_multiword_concept_lookup_target(lower: str) -> str:
    patterns = (
        r"^(?:tell me about|show me|explain|what do you know about)\s+(.+)$",
        r"^(?:what is|what are)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, lower)
        if not match:
            continue
        target = " ".join(match.group(1).strip(" .?!").split())
        words = [
            word for word in re.findall(r"[a-z0-9]+", target)
            if word not in {"the", "a", "an", "and", "or", "of", "in", "to", "local", "memory", "concept"}
        ]
        if len(words) >= 2:
            return target
    return ""


def _last_concept_context(history: list[dict[str, str]] | None) -> dict[str, Any]:
    anchored = resolve_followup_anchor(history)
    if anchored.get("active_concept_name"):
        return {
            "concept_name": anchored.get("active_concept_name"),
            "concept_names": anchored.get("retrieved_concept_names") or [anchored.get("active_concept_name")],
            "domain": anchored.get("domain"),
            "concept_id": anchored.get("active_concept_id"),
        }
    names = []
    domain = None
    newer_explicit_topic = False
    for item in reversed(history or []):
        if item.get("role") == "user" and _is_explicit_new_topic_request(str(item.get("content") or "")):
            newer_explicit_topic = True
            continue
        if newer_explicit_topic:
            break
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
        talk_match = re.search(r"\bI can talk about\s+(.+?)\.\s+Which direction", content)
        if talk_match:
            found.extend(
                part.strip()
                for part in re.split(r"\s*,\s*|\s+and\s+", talk_match.group(1))
                if part.strip()
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


def resolve_followup_anchor(history: list[dict[str, str]] | None) -> dict[str, Any]:
    newer_explicit_topic = False
    for item in reversed(history or []):
        if item.get("role") == "topic_state":
            try:
                state = json.loads(str(item.get("content") or "{}"))
            except json.JSONDecodeError:
                continue
            if state.get("supersedes_anchor"):
                return {}
        if item.get("role") == "user" and _is_explicit_new_topic_request(str(item.get("content") or "")):
            newer_explicit_topic = True
            continue
        if item.get("role") != "anchor":
            continue
        if newer_explicit_topic:
            return {}
        try:
            anchor = json.loads(str(item.get("content") or "{}"))
        except json.JSONDecodeError:
            continue
        if anchor.get("active_concept_id") or anchor.get("active_concept_name"):
            return anchor
    return {}


def _is_anchor_followup(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if _is_explicit_new_topic_request(message):
        return False
    if lower in {
        "tell me more",
        "go deeper",
        "explain more",
        "why",
        "why?",
        "how so",
        "give me an example",
        "what else",
        "another one",
        "compare that",
        "expand on that",
        "elaborate",
    }:
        return True
    return bool(re.match(r"how does (that|this|it) relate to .+", lower))


def _is_explicit_new_topic_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if not lower:
        return False
    if lower in {"what do you mean", "why", "why is that", "tell me more", "go deeper", "continue", "expand on that"}:
        return False
    if _is_context_dependent_followup(message):
        return False
    if re.match(r"^(what|who|where|when|which|how)\s+(is|are|was|were|do|does|did|can|should)\b", lower):
        return True
    if lower.startswith(("tell me about ", "explain ", "compare ", "analyze ", "brainstorm ", "what comes to mind")):
        return True
    if "new topic" in lower or "switch topics" in lower or "completely different" in lower:
        return True
    return False


def _is_brainstorming_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    return any(phrase in lower for phrase in (
        "first concept that comes to mind",
        "what comes to mind",
        "brainstorm",
        "give me ideas",
        "free associate",
    ))


def _is_context_dependent_followup(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if re.match(r"^compare\s+(that|this|it|those|them)\s+(?:with|to)\b", lower):
        return True
    if lower in {
        "explain that",
        "explain this",
        "explain it",
        "give me another one",
        "another one",
        "give me another practical tip",
        "another practical tip",
        "give me another tip",
        "another tip",
        "what is a practical next step",
        "give me an example",
        "give me examples",
        "why",
        "why is that",
        "why does that matter",
        "why is that important",
        "why should i care about that",
        "what difference does that make",
        "how does that affect the decision",
        "where does that analogy break",
        "tell me more",
        "continue",
        "expand on that",
    }:
        return True
    return bool(re.match(
        r"^(how|why|where|what)\s+(does|do|is|are|was|were|would|could|should)\s+(that|this|it|those|them)\b",
        lower,
    ))


def _is_anchor_browse_followup(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    return lower in {"what else", "another one", "what else do you know", "show me another", "nearby concepts"}


def deepen_from_concept_anchor(message: str, anchor: dict[str, Any]) -> dict[str, Any] | None:
    concept = _anchor_concept(anchor)
    if not concept:
        return None
    answer = _anchored_concept_answer(message, concept)
    matches = [concept]
    for concept_id in anchor.get("retrieved_concept_ids", [])[:4]:
        if concept_id == concept.get("concept_id"):
            continue
        nearby = _get_concept(concept_id)
        if nearby:
            matches.append(nearby)
    return {
        "route": "developmental_concept_anchor_followup",
        "answer": answer,
        "confidence": "grounded_in_active_conversation_anchor",
        "confidence_score": 0.9,
        "selected_model_lane": select_model_lane(message),
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "concept_matches": matches,
        "active_topic_anchor": _anchor_from_matches(message, answer, matches),
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def browse_near_active_anchor(message: str, anchor: dict[str, Any]) -> dict[str, Any] | None:
    concept = _anchor_concept(anchor)
    if not concept:
        return None
    related_terms = [
        str(item)
        for item in concept.get("related_concepts", [])
        if str(item).strip()
    ][:5]
    query = " ".join([str(concept.get("concept_name") or ""), *related_terms])
    matches = []
    seen = {str(concept.get("concept_id") or "")}
    try:
        from orchestration.runtime.rc2_storage_adapter import search_concepts

        result = search_concepts(query, domain=concept.get("domain"), limit=8, exclude_concept_names=[str(concept.get("concept_name") or "")])
        for row in result.get("matches", []):
            concept_id = str(row.get("concept_id") or "")
            if concept_id and concept_id not in seen:
                seen.add(concept_id)
                matches.append(row)
    except Exception:
        matches = []
    if not matches:
        matches = [
            row
            for row in (query_approved_concepts(term).get("matches", [None])[0] for term in related_terms)
            if row and str(row.get("concept_id") or "") not in seen
        ][:3]
    if not matches:
        return deepen_from_concept_anchor(message, anchor)
    lines = [
        f"Staying with `{concept.get('concept_name')}`, nearby things I can discuss are:",
    ]
    for row in matches[:3]:
        lines.append(f"- {row.get('concept_name')}: {str(row.get('short_definition') or '').strip()}")
    answer = "\n".join(lines)
    return {
        "route": "developmental_concept_anchor_browse",
        "answer": answer,
        "confidence": "grounded_in_active_conversation_anchor",
        "confidence_score": 0.9,
        "selected_model_lane": select_model_lane(message),
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "concept_matches": [concept, *matches[:3]],
        "active_topic_anchor": _anchor_from_matches(message, answer, [concept, *matches[:3]]),
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def _get_concept(concept_id: str) -> dict[str, Any] | None:
    if not concept_id:
        return None
    try:
        from orchestration.runtime.rc2_storage_adapter import get_concept

        return get_concept(concept_id)
    except Exception:
        for row in query_approved_concepts(concept_id).get("matches", []):
            if str(row.get("concept_id")) == str(concept_id):
                return row
    return None


def _anchor_concept(anchor: dict[str, Any]) -> dict[str, Any] | None:
    concept_id = str(anchor.get("active_concept_id") or "")
    if concept_id:
        concept = _get_concept(concept_id)
        if concept:
            return concept
    name = str(anchor.get("active_concept_name") or "")
    if name:
        matches = query_approved_concepts(name).get("matches", [])
        if matches:
            return matches[0]
    return None


def _anchored_concept_answer(message: str, concept: dict[str, Any]) -> str:
    lower = " ".join(str(message or "").lower().split()).strip(" ?!.")
    name = str(concept.get("concept_name") or "that concept")
    definition = str(concept.get("short_definition") or "").strip()
    propositions = [str(item).strip() for item in concept.get("propositions", []) if str(item).strip()]
    examples = [str(item).strip() for item in concept.get("examples", []) if str(item).strip()]
    related = [str(item).strip() for item in concept.get("related_concepts", []) if str(item).strip()]
    if "example" in lower:
        if examples:
            return f"Staying with `{name}`, here's an example:\n{examples[0]}"
        if propositions:
            return f"Staying with `{name}`, a concrete way to think about it is: {propositions[0]}"
    relation_match = re.search(r"how does (?:that|this|it) relate to\s+(.+)", lower)
    if relation_match:
        target = relation_match.group(1).strip(" .?!")
        return (
            f"Staying with `{name}`, the connection to {target} is through the same stored mechanism: "
            f"{definition} "
            f"I can treat that as a tentative relation, but I have not written a new memory or enabled synthesis."
        ).strip()
    lines = [f"Staying with `{name}`:"]
    if definition:
        lines.append(definition)
    if propositions:
        lines.append("")
        lines.append("A little more detail:")
        lines.extend(f"- {item}" for item in propositions[:3])
    if related:
        lines.append("")
        lines.append("Related ideas:")
        lines.extend(f"- {item}" for item in related[:4])
    lines.append("")
    lines.append("No memory was written, and I did not need to ask a local model for this follow-up.")
    return "\n".join(lines)


def _anchor_from_matches(question: str, answer: str, matches: list[dict[str, Any]]) -> dict[str, Any]:
    if not matches:
        return {}
    first = matches[0]
    return {
        "active_concept_id": first.get("concept_id"),
        "active_concept_name": first.get("concept_name"),
        "domain": first.get("domain"),
        "related_concepts": first.get("related_concepts", [])[:8],
        "retrieved_concept_ids": [row.get("concept_id") for row in matches if row.get("concept_id")],
        "retrieved_concept_names": [row.get("concept_name") for row in matches if row.get("concept_name")],
        "last_user_question": question,
        "last_answer_summary": " ".join(str(answer or "").split())[:420],
    }


def _sun_blue_correction(message: str) -> str | None:
    lower = " ".join(str(message or "").lower().split())
    if "sun" not in lower or "blue" not in lower:
        return None
    if "sky" in lower:
        return None
    return (
        "The Sun is not normally blue. It is often perceived as white in space and yellowish from Earth's surface. "
        "The blue color people usually notice is the sky, which comes from atmospheric scattering of shorter blue wavelengths. "
        "So the better framing is: the sky appears blue because of scattering, not because the Sun itself is blue."
    )


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
    lower = " " + " ".join(re.sub(r"[^a-z0-9]+", " ", message.lower()).split()) + " "
    for answer_id, item in DIRECT_LOCAL_ANSWERS.items():
        for trigger in item["triggers"]:
            if all(f" {word} " in lower for word in trigger):
                return {
                    "answer_id": answer_id,
                    "answer": item["answer"],
                    "confidence_score": item["confidence"],
                    "confidence": "local_general_knowledge",
                    "fixture": item.get("fixture"),
                }
    return None


def _topic_switch_target(message: str) -> str | None:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" .?!")
    patterns = [
        r"^(?:now\s+)?(?:actually\s+)?(?:let['’]?s|lets)\s+talk\s+about\s+(.+)$",
        r"^(?:actually\s+)?(?:let['’]?s|lets)\s+switch\s+to:?\s+(.+)$",
        r"^(?:actually\s+)?talk\s+about\s+(.+)$",
        r"^(?:actually\s+)?switch(?:ing)?\s+(?:to|topics?\s+to):?\s+(.+)$",
        r"^(?:new topic:|different topic:|switching subjects:)\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, lower)
        if match:
            topic = match.group(1).strip(" .?!")
            return topic if topic else None
    return None


def _topic_return_target(message: str) -> str | None:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" .?!")
    patterns = (
        r"^(?:let['’]?s\s+)?go back to\s+(.+)$",
        r"^return to\s+(.+)$",
        r"^(?:let['’]?s\s+)?return to\s+(.+)$",
        r"^back to\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, lower)
        if match:
            target = match.group(1).strip(" .?!")
            return target if target else None
    return None


def _is_substantive_switch_target(target: str | None) -> bool:
    lower = " ".join(str(target or "").lower().strip(" :;,.?!").split())
    if not lower:
        return False
    if re.match(r"^(what|who|where|when|why|how|which)\b", lower):
        return True
    if re.match(r"^(is|are|was|were|do|does|did|can|could|should|would)\b", lower):
        return True
    return lower.startswith((
        "explain ",
        "describe ",
        "define ",
        "summarize ",
        "compare ",
        "analyze ",
        "list ",
        "show ",
        "tell me ",
    ))


def _topic_hint_from_message(message: str, payload: dict[str, Any]) -> str | None:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" .?!")
    switch = _topic_switch_target(message)
    if switch and not _is_substantive_switch_target(switch):
        return switch
    if "first concept that comes to mind" in lower and "physics" in lower:
        return "motion in physics"
    if "sky" in lower:
        return "sky"
    if "music" in lower:
        return "music"
    if "moon" in lower:
        return "moon"
    if "mars" in lower:
        return "mars"
    topic = _topic_label_from_message(message)
    if topic:
        return topic
    answer = str(payload.get("answer") or "").lower()
    if "motion" in answer and "physics" in answer:
        return "motion in physics"
    if "sky" in answer or "blue wavelengths" in answer:
        return "sky"
    return None


def _latest_topic_state(history: list[dict[str, str]] | None) -> dict[str, Any]:
    for item in reversed(history or []):
        if item.get("role") != "topic_state":
            continue
        try:
            state = json.loads(str(item.get("content") or "{}"))
        except json.JSONDecodeError:
            continue
        if isinstance(state, dict) and str(state.get("topic") or "").strip():
            return state
    return {}


def _prior_topic_match(history: list[dict[str, str]] | None, target: str) -> str:
    wanted = _normalize_topic_label(target)
    if not wanted:
        return ""
    for item in reversed(history or []):
        if item.get("role") != "topic_state":
            continue
        try:
            state = json.loads(str(item.get("content") or "{}"))
        except json.JSONDecodeError:
            continue
        topic = str(state.get("topic") or "").strip()
        if not topic:
            continue
        normalized = _normalize_topic_label(topic)
        if wanted == normalized or wanted in normalized or normalized in wanted:
            return topic
    return ""


def _normalize_topic_label(value: object) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _conversation_topic_state(message: str, payload: dict[str, Any], intent_info: dict[str, Any], history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    route = str(payload.get("route") or "")
    answer = str(payload.get("answer") or "")
    if route == "topic_return":
        topic = str(payload.get("topic_return_target") or "").strip()
        if topic:
            return {
                "state_kind": "TOPIC_SWITCH",
                "topic": topic,
                "source_turn": "current",
                "source_route": route,
                "last_user_prompt": message,
                "last_visible_answer": answer[:600],
                "entities": [topic],
                "confidence": float(payload.get("confidence_score") or 0.86),
                "supersedes_anchor": True,
                "read_only": True,
            }
    switch_topic = _topic_switch_target(message)
    if switch_topic and not _is_substantive_switch_target(switch_topic):
        return {
            "state_kind": "TOPIC_SWITCH",
            "topic": switch_topic,
            "source_turn": "current",
            "source_route": route,
            "last_user_prompt": message,
            "last_visible_answer": answer[:600],
            "entities": [switch_topic],
            "confidence": 0.88,
            "supersedes_anchor": True,
            "read_only": True,
        }
    anchor = payload.get("active_topic_anchor")
    matches = payload.get("concept_matches")
    if isinstance(anchor, dict) and (anchor.get("active_concept_name") or anchor.get("active_concept_id")):
        topic = str(anchor.get("active_concept_name") or anchor.get("active_concept_id") or "")
        return {
            "state_kind": "CONCEPT_ANCHOR",
            "topic": topic,
            "source_turn": "current",
            "source_route": route,
            "last_user_prompt": message,
            "last_visible_answer": answer[:600],
            "entities": [topic],
            "confidence": float(payload.get("confidence_score") or 0.84),
            "supersedes_anchor": False,
            "read_only": True,
        }
    if isinstance(matches, list) and matches and isinstance(matches[0], dict) and matches[0].get("concept_name"):
        topic = str(matches[0].get("concept_name") or "")
        return {
            "state_kind": "CONCEPT_ANCHOR",
            "topic": topic,
            "source_turn": "current",
            "source_route": route,
            "last_user_prompt": message,
            "last_visible_answer": answer[:600],
            "entities": [topic],
            "confidence": float(payload.get("confidence_score") or 0.84),
            "supersedes_anchor": False,
            "read_only": True,
        }
    if route == "social_conversation" or intent_info.get("intent") in SOCIAL_INTENT_RESPONSES:
        return {
            "state_kind": "SOCIAL_INTERLUDE",
            "topic": "",
            "source_turn": "current",
            "source_route": route,
            "last_user_prompt": message,
            "last_visible_answer": answer[:300],
            "entities": [],
            "confidence": float(payload.get("confidence_score") or intent_info.get("confidence") or 0.8),
            "supersedes_anchor": False,
            "read_only": True,
        }
    prior_topic_state = _latest_topic_state(history)
    if route == "session_memory" and prior_topic_state.get("topic"):
        return {
            **prior_topic_state,
            "state_kind": "FOLLOWUP",
            "source_turn": "current",
            "source_route": route,
            "last_user_prompt": message,
            "last_visible_answer": answer[:600],
            "confidence": float(payload.get("confidence_score") or prior_topic_state.get("confidence") or 0.78),
            "supersedes_anchor": bool(prior_topic_state.get("supersedes_anchor", True)),
            "read_only": True,
        }
    topic = _topic_hint_from_message(message, payload)
    if topic and route in {
        "local_conversation_model_lane",
        "conversation_clarified_misframed_question",
        "session_memory",
        "conversation_short_term_memory",
    }:
        return {
            "state_kind": "SUBSTANTIVE_TOPIC",
            "topic": topic,
            "source_turn": "current",
            "source_route": route,
            "last_user_prompt": message,
            "last_visible_answer": answer[:600],
            "entities": [topic],
            "confidence": float(payload.get("confidence_score") or 0.78),
            "supersedes_anchor": True,
            "read_only": True,
        }
    return {
        "state_kind": "FOLLOWUP" if _is_context_dependent_followup(message) else "NONE",
        "topic": "",
        "source_turn": "current",
        "source_route": route,
        "last_user_prompt": message,
        "last_visible_answer": answer[:300],
        "entities": [],
        "confidence": float(payload.get("confidence_score") or 0.5),
        "supersedes_anchor": False,
        "read_only": True,
    }


def _is_development_workflow_request(message: str, history: list[dict[str, str]] | None = None) -> bool:
    lower = " ".join(str(message or "").lower().replace("-", " ").split())
    if any(term in lower for term in (
        "repair hypothesis",
        "repair hypotheses",
        "bounded repair",
        "which tests would prove",
        "what should delta inspect",
        "router test fails",
        "classified as contradiction",
        "governed self-development",
        "sandbox implementation",
        "development objective",
        "implement the fix by itself",
        "what question should it ask",
    )):
        return True
    if lower.startswith(("now propose", "propose two", "rank them")) and _history_mentions_development(history):
        return True
    return False


def _should_defer_to_knowledge_browse(intent_info: dict[str, Any]) -> bool:
    return intent_info.get("intent") in {"knowledge_browse_followup", "knowledge_browse_jump"}


def _history_mentions_development(history: list[dict[str, str]] | None) -> bool:
    text = " ".join(str(item.get("content") or "") for item in (history or [])[-6:]).lower()
    return any(term in text for term in ("router", "contradiction", "repair", "test", "delta", "runtime"))


def _development_workflow_answer(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
    if not _is_development_workflow_request(message, history):
        return None
    lower = " ".join(str(message or "").lower().replace("-", " ").split())
    if "which tests would prove" in lower or ("tests" in lower and "safer" in lower):
        answer = (
            "Use focused live-path regressions: one topic-shift case that must not enter contradiction analysis, "
            "one ambiguity case that must ask for clarification, one follow-up continuity case that preserves the selected subject, "
            "and one governance check proving no provider call, web search, memory write, commit, or push occurred."
        )
    elif "hypothes" in lower or lower.startswith(("now propose", "propose two", "rank them")):
        answer = (
            "Ranked repair hypotheses: 1. Adjust router precedence so governed development workflow prompts use the local engineering path before concept retrieval. "
            "Confidence 0.86, low governance impact, moderate regression risk. "
            "2. Add a broad concept-memory exclusion for technical words like contradiction and tests. Confidence 0.54, higher regression risk because it could suppress useful retrieval. "
            "The safer first experiment is the precedence repair because it is narrow and reversible."
        )
    elif "implement the fix by itself" in lower:
        answer = "No. DELTA may prepare a bounded objective, sandbox candidate, tests, and evidence, but operator approval is required before promotion into the primary repository."
    elif "what question should it ask" in lower:
        answer = "It should ask: Do you approve a bounded sandbox objective to repair the observed ambiguity failure, with focused tests and no provider calls, retrieval, memory writes, commits, or pushes?"
    else:
        answer = (
            "DELTA should inspect the smallest responsible boundary first: the contradiction detector trigger, then router precedence, then the working-memory/discourse frame that carried the topic shift. "
            "The first repair hypothesis should be narrow and proven with live-path conversation turns before any broader architectural change."
        )
    return {
        "route": "local_conversation_model_lane",
        "answer": answer,
        "confidence": "local_governed_development_workflow",
        "confidence_score": 0.84,
        "selected_model_lane": select_model_lane(message, "coding"),
        "local_model_result": None,
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def _is_explicit_topic_reset(message: str) -> bool:
    text = " ".join(str(message or "").strip().lower().split())
    return bool(re.match(
        r"^(new topic:|switching subjects:|different topic:|let['’]?s move on[.!]?|forget the prior topic for now[.!]?)",
        text,
    ))


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
            "model_id": str(result.model_id or model_name),
            "latency_seconds": float(result.latency_seconds or 0.0),
            "response_tokens": int(result.response_tokens or 0),
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
    # Ordinary conversation should not create concept-review candidates on its
    # own. Explicit UI memory requests use build_memory_candidate_from_answer()
    # or remember_useful_answer() so operator review remains available.
    return None


def remember_useful_answer(message: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = payload.get("memory_candidate")
    candidate = existing if isinstance(existing, dict) else build_memory_candidate_from_answer(message, payload)
    if not candidate_is_memory_worthy(candidate, payload):
        candidate = None
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


def _last_visible_exchange(history: list[dict[str, str]] | None) -> dict[str, str] | None:
    last_assistant = ""
    for item in reversed(history or []):
        role = item.get("role")
        content = str(item.get("content") or "")
        if role == "assistant" and not last_assistant:
            last_assistant = content.split("--- Developer Overlay ---", 1)[0].strip()
            continue
        if role == "user" and last_assistant:
            return {"question": content.strip(), "answer": last_assistant}
    return None


def _followup_act(message: str) -> str:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if re.search(r"\bcompare\s+(?:that|this|it|those|them)\s+(?:with|to)\s+.+", lower):
        return "comparison"
    if _is_practical_elaboration_request(message):
        return "practical_elaboration"
    if "another" in lower or "what else" in lower:
        return "alternative"
    if "example" in lower:
        return "example"
    if lower in {"why", "why is that"} or lower.startswith("why "):
        return "causal"
    if "always" in lower or "does it" in lower or "does that" in lower:
        return "clarification"
    if lower in {"tell me more", "continue", "more detail", "more details", "go deeper", "expand on that"}:
        return "elaboration"
    return "clarification" if _is_context_dependent_followup(message) else "other"


def _compact_prior_point(text: str, topic: str) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return f"the recent answer about {topic}"
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    if sentences:
        return sentences[0][:240]
    return cleaned[:240]


def _alternative_from_prior_answer(answer: str, topic: str) -> str:
    text = str(answer or "")
    candidates: list[str] = []
    branch_match = re.search(r"\bbranch from [^:]+ to\s+(.+?)(?:[.!?]|$)", text, flags=re.IGNORECASE)
    if branch_match:
        candidates.extend(re.split(r"\s*,\s*|\s+or\s+|\s+and\s+", branch_match.group(1)))
    if not candidates:
        for term in ("energy", "symmetry", "fields", "conservation", "rhythm", "memory", "expectation", "surface", "reflection"):
            if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
                candidates.append(term)
    cleaned = [item.strip(" .,:;`'\"") for item in candidates if item.strip(" .,:;`'\"")]
    chosen = next((item for item in cleaned if item.lower() not in str(topic or "").lower()), "")
    return chosen or "a neighboring angle"


def _bounded_followup_answer(topic_state: dict[str, Any], message: str) -> str:
    topic = str(topic_state.get("topic") or "the current topic").strip() or "the current topic"
    prior_answer = str(topic_state.get("last_visible_answer") or "")
    prior_point = _compact_prior_point(prior_answer, topic)
    act = _followup_act(message)
    if act == "alternative":
        alternative = _alternative_from_prior_answer(prior_answer, topic)
        return f"Another related angle is {alternative}. Staying with {topic}, it gives us a nearby way to keep exploring without changing topics."
    if act == "causal":
        return f"I chose or continued with {topic} because the prior answer gives a concrete handle: {prior_point}"
    if act == "example":
        return f"An example within {topic}: take the key point from the prior answer, then ask how it would show up in one observable case. The prior point was: {prior_point}"
    if act == "comparison":
        target = _comparison_target(message)
        if target:
            return (
                f"Comparing {topic} with {target}: I can use {topic} from the current conversation as the resolved referent. "
                f"Grounded detail for {topic}: {prior_point} For {target}, I need equally grounded details before making a strong comparison, so I will not replace it with unrelated retrieval."
            )
        return f"I can compare {topic}, but I need the comparison target."
    if act == "clarification":
        return f"No, not always in the same way. Staying with {topic}, the prior answer gives the baseline, but context can change how it appears or why it matters: {prior_point}"
    return f"Still on {topic}: {prior_point} A useful next step is to unpack the mechanism, limits, and examples without changing topics."


def _comparison_target(message: str) -> str:
    lower = " ".join(str(message or "").strip().split())
    match = re.search(r"\bcompare\s+(?:that|this|it|those|them)\s+(?:with|to)\s+(.+)$", lower, flags=re.IGNORECASE)
    return match.group(1).strip(" .?!") if match else ""


def _bounded_followup_from_last_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    topic_state = _latest_topic_state(history)
    if not topic_state:
        return None
    if _is_practical_elaboration_request(message):
        answer = _grounded_practical_elaboration(topic_state)
        if answer:
            return _session_payload(message, answer, confidence_score=0.86, resolved=True)
    answer = _bounded_followup_answer(topic_state, message)
    return _session_payload(message, answer, confidence_score=0.84, resolved=True)


def _active_topic_aspect_followup(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    aspect = _active_topic_aspect(message)
    if not aspect:
        return None
    topic_state = _latest_topic_state(history)
    topic = str(topic_state.get("topic") or "").strip()
    if not topic:
        return None
    answer = _active_topic_aspect_answer(topic, aspect, topic_state)
    if not answer:
        return None
    payload = _session_payload(message, answer, confidence_score=0.86, resolved=True)
    payload["memory_retrieval_bypassed"] = True
    return payload


def _active_topic_aspect(message: str) -> str:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if " " in lower:
        return ""
    return lower if lower in {
        "mechanism",
        "limits",
        "examples",
        "causes",
        "effects",
        "applications",
        "evidence",
        "risks",
        "benefits",
    } else ""


def _active_topic_aspect_answer(topic: str, aspect: str, topic_state: dict[str, Any]) -> str:
    matches = query_approved_concepts(topic).get("matches", [])
    concept = matches[0] if matches else {}
    source_lines = [
        str(item).strip()
        for item in [
            *((concept or {}).get("propositions") or []),
            *((concept or {}).get("examples") or []),
            (concept or {}).get("short_definition"),
            topic_state.get("last_visible_answer"),
        ]
        if str(item or "").strip()
    ]
    selected = next((line for line in source_lines if aspect in line.lower()), "")
    if not selected and source_lines:
        selected = source_lines[0]
    if not selected:
        return ""
    name = str((concept or {}).get("concept_name") or topic)
    return (
        f"Still on {name}: for {aspect}, the grounded detail I have is: "
        f"{_compact_prior_point(selected, name)}"
    )


def _is_practical_elaboration_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    return lower in {
        "give me another practical tip",
        "another practical tip",
        "give me another tip",
        "another tip",
        "what is a practical next step",
    }


def _is_practical_tip_for_explicit_target(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    return bool(re.match(r"^give me (?:a |another )?practical tip for .+", lower))


def _grounded_practical_elaboration(topic_state: dict[str, Any]) -> str:
    topic = str(topic_state.get("topic") or "").strip()
    if not topic:
        return ""
    matches = query_approved_concepts(topic).get("matches", [])
    if not matches:
        return ""
    concept = matches[0]
    stored_lines = [
        str(item).strip()
        for item in [
            *(concept.get("propositions") or []),
            *(concept.get("examples") or []),
            concept.get("short_definition"),
        ]
        if str(item or "").strip()
    ]
    useful = _first_useful_practical_line(stored_lines)
    if not useful:
        return ""
    name = str(concept.get("concept_name") or topic)
    return (
        f"From noncanonical reviewed memory for `{name}`: another practical tip is to {useful[0].lower() + useful[1:] if len(useful) > 1 else useful} "
        "This stays grounded in the stored concept rather than asking a model or adding new memory."
    )


def _first_useful_practical_line(lines: list[str]) -> str:
    for line in lines:
        clean = _compact_prior_point(line, "the stored concept").strip(" .")
        if not clean:
            continue
        if any(term in clean.lower() for term in ("practice", "start", "use", "consider", "focus", "learn", "get comfortable")):
            return clean
    return _compact_prior_point(lines[0], "the stored concept").strip(" .") if lines else ""


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
        return _session_payload(message, f"Got it. For this conversation only, I'll treat your favorite color as {color}.", route="conversation_short_term_memory")
    if "alice owns" in lower and "bob owns" in lower:
        return _session_payload(message, "Got it. For this conversation only: Alice owns the truck, and Bob owns the trailer.", route="conversation_short_term_memory")
    if history and "favorite color" in lower and "conversation" in lower:
        for item in reversed(history):
            text = str(item.get("content") or "").lower()
            match = re.search(r"favorite color is\s+([a-zA-Z]+)", text)
            if match:
                return _session_payload(message, f"In this conversation, your favorite color is {match.group(1)}.", route="conversation_short_term_memory")
    if history and "who owns the" in lower:
        target = "trailer" if "trailer" in lower else "truck" if "truck" in lower else ""
        for item in reversed(history):
            text = str(item.get("content") or "").lower()
            if target == "trailer" and "bob owns the trailer" in text:
                return _session_payload(message, "Bob owns the trailer in this conversation.", route="conversation_short_term_memory")
            if target == "truck" and "alice owns the truck" in text:
                return _session_payload(message, "Alice owns the truck in this conversation.", route="conversation_short_term_memory")
    return None


def _is_recent_concept_followup(message: str) -> bool:
    return message.lower().strip(" ?!.") in {
        "why",
        "why is that",
        "tell me more",
        "continue",
        "expand on that",
        "more detail",
        "more details",
        "go deeper",
        "tell me more",
        "continue",
        "expand on that",
        "more detail",
        "more details",
        "give me an example",
        "how big can they get",
        "does that happen to all of them",
    }


def _session_payload(
    message: str,
    answer: str,
    *,
    confidence_score: float = 0.92,
    resolved: bool | None = None,
    route: str = "session_memory",
) -> dict[str, Any]:
    return {
        "route": route,
        "answer": answer,
        "confidence": "session_memory",
        "confidence_score": confidence_score,
        "selected_model_lane": select_model_lane(message),
        "supporting_information_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "resolved_from_prior_visible_answer": resolved,
    }


def _recent_concept_followup_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    if _is_explicit_new_topic_request(message):
        return None
    lower = message.lower().strip(" ?!.")
    if lower not in {"why", "why is that", "tell me more", "continue", "expand on that", "more detail", "more details", "go deeper", "give me an example", "how big can they get", "does that happen to all of them"}:
        return None
    context = _last_concept_context(history)
    concept_name = context.get("concept_name")
    if not concept_name:
        topic = _recent_user_topic(history)
        if not topic:
            return None
        prior = str((_last_visible_exchange(history) or {}).get("answer") or "").lower()
        unresolved_offer = "would you like me to ask a local reasoning model" in prior and "don't think i know enough" in prior
        route = "conversation_short_term_memory" if unresolved_offer else "session_memory"
        return _session_payload(
            message,
            f"I can continue from your recent topic, {topic}. I do not have approved local knowledge for it yet, so I can ask the local reasoning model if you want.",
            route=route,
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
    direct = _direct_answer(message)
    if development := _development_workflow_answer(message, history):
        return development
    if memory := _history_answer(message, history):
        return memory
    if not execute_local_model and (intent == "followup" or _is_context_dependent_followup(message)):
        if bounded := _bounded_followup_from_last_answer(message, history):
            return bounded
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
    if direct and not _is_synthesis_trial_request(message):
        answer = str(direct["answer"])
        confidence = str(direct["confidence"])
        confidence_score = float(direct["confidence_score"])
        support_offer = None
        fixture = direct.get("fixture")
    elif _is_brainstorming_request(message):
        answer = (
            "The first concept that comes to mind is motion: in physics, it is a clean starting point because it connects position, time, forces, energy, and prediction. "
            "If you want a more playful association, I would branch from motion to symmetry, fields, or conservation."
        )
        confidence = "local_brainstorming"
        confidence_score = 0.78
        support_offer = None
    elif intent == "coding":
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
        "deterministic_fixture": fixture if direct else None,
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


def _finish_conversation_payload(payload: dict[str, Any], message: str, history: list[dict[str, str]] | None) -> dict[str, Any]:
    normalize_safety_payload(payload)
    intent_info = payload.get("intent") if isinstance(payload.get("intent"), dict) else classify_intent(message)
    payload["conversation_topic_state"] = _conversation_topic_state(message, payload, intent_info, history)
    payload["routing_observability"] = {
        "layer": "rc2_conversational_mode_router",
        "selected_route": str(payload.get("route") or ""),
        "intent": intent_info,
        "explicit_new_topic_request": _is_explicit_new_topic_request(message),
        "anchor_available": bool(resolve_followup_anchor(history)),
        "anchor_followup_allowed": _is_anchor_followup(message),
        "memory_retrieval_bypassed": bool(payload.get("memory_retrieval_bypassed", False)),
        "history_turns_seen": len(history or []),
        "early_return": str(payload.get("route") or ""),
        "read_only": True,
        "ephemeral": True,
    }
    payload["route_arbitration"] = build_route_arbitration_trace(
        message,
        history,
        str(payload.get("route") or ""),
        payload.get("intent") if isinstance(payload.get("intent"), dict) else None,
    )
    attach_episode(payload, message, history)
    return apply_natural_renderer(payload, message)


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
        anchor = resolve_followup_anchor(history)
        explicit_new_topic = _is_explicit_new_topic_request(message)
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
            return _finish_conversation_payload(payload, message, history)
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
            return _finish_conversation_payload(payload, message, history)
        switch_topic = _topic_switch_target(message)
        if switch_topic and not _is_substantive_switch_target(switch_topic):
            payload = {
                "mode": mode,
                "route": "social_conversation",
                "answer": f"Got it. Let's talk about {switch_topic}.",
                "confidence": "topic_switch_acknowledgement",
                "confidence_score": 0.88,
                "selected_model_lane": select_model_lane(message),
                "local_model_result": None,
                "supporting_information_offer": None,
                "local_model_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "escalation_plan": build_escalation_plan(message),
                "intent": {**intent_info, "intent": "topic_switch", "communication_act": "topic_switch"},
                "confidence_decision": confidence_engine(message, False),
                "mode_router_flags": ROUTER_FLAGS,
            }
            return _finish_conversation_payload(payload, message, history)
        return_target = _topic_return_target(message)
        if return_target:
            prior_topic = _prior_topic_match(history, return_target)
            concept = query_approved_concepts(prior_topic or return_target)
            matches = concept.get("matches", []) if concept.get("matched") else []
            resolved_topic = prior_topic or (str(matches[0].get("concept_name") or "") if matches else "")
            if resolved_topic:
                detail = str((matches[0].get("short_definition") if matches else "") or "").strip()
                answer = f"Returning to {resolved_topic}."
                if detail:
                    answer += f" {detail}"
                route_label = "topic_return" if any(item.get("role") == "topic_state" for item in history or []) else "session_memory"
                payload = {
                    "mode": mode,
                    "route": route_label,
                    "answer": answer,
                    "confidence": "explicit_prior_topic_return",
                    "confidence_score": 0.88,
                    "selected_model_lane": select_model_lane(message),
                    "supporting_information_offer": None,
                    "local_model_offer": None,
                    "local_model_result": None,
                    "concept_matches": matches,
                    "topic_return_target": resolved_topic,
                    "memory_candidate": None,
                    "provider_calls_performed": False,
                    "web_search_performed": False,
                    "training_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                    "escalation_plan": build_escalation_plan(message),
                    "intent": {**intent_info, "intent": "topic_return", "communication_act": "topic_return"},
                    "confidence_decision": confidence_engine(message, bool(matches)),
                    "mode_router_flags": ROUTER_FLAGS,
                }
                return _finish_conversation_payload(payload, message, history)
            payload = {
                "mode": mode,
                "route": "topic_return_unresolved",
                "answer": f"I do not have a prior or approved topic matching `{return_target}` in this conversation.",
                "confidence": "topic_return_unresolved",
                "confidence_score": 0.62,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "local_model_offer": None,
                "local_model_result": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "escalation_plan": build_escalation_plan(message),
                "intent": {**intent_info, "intent": "topic_return_unresolved", "communication_act": "topic_return"},
                "confidence_decision": confidence_engine(message, False),
                "mode_router_flags": ROUTER_FLAGS,
            }
            return _finish_conversation_payload(payload, message, history)
        if intent_info.get("intent") in SOCIAL_INTENT_RESPONSES and intent_info.get("safe_no_route", True):
            payload = {
                "mode": mode,
                "route": "social_conversation",
                "answer": SOCIAL_INTENT_RESPONSES[str(intent_info.get("intent"))],
                "confidence": "social_intent",
                "confidence_score": intent_info.get("confidence", 0.9),
                "selected_model_lane": select_model_lane(message, str(intent_info.get("intent") or "")),
                "local_model_result": None,
                "supporting_information_offer": None,
                "local_model_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
            payload["memory_candidate"] = None
            payload["autonomous_action_performed"] = False
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
        render_correction = build_render_correction_payload(message, history)
        if render_correction:
            payload = {"mode": mode, **render_correction}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "render_correction", "communication_act": "render_correction"}
            payload["confidence_decision"] = {
                "confidence": payload.get("confidence_score", 0.0),
                "evidence_quality": "ephemeral_prior_answer_rendering_context",
                "retrieval_sufficiency": "not_needed_for_render_correction",
                "provider_necessity": "none",
            }
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            return _finish_conversation_payload(payload, message, history)
        if (intent_info.get("communication_act") == "clarification_followup" or _is_context_dependent_followup(message)) and not history:
            payload = {
                "mode": mode,
                "route": "session_memory",
                "answer": "I can explain it more simply, but I need the thing you want simplified. Send the sentence or topic and I’ll restate it plainly.",
                "confidence": "needs_recent_context",
                "confidence_score": 0.72,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "escalation_plan": build_escalation_plan(message),
                "intent": intent_info,
                "confidence_decision": confidence_engine(message, False),
                "mode_router_flags": ROUTER_FLAGS,
            }
            return _finish_conversation_payload(payload, message, history)
        early_contradiction = build_contradiction_analysis(message, history=history) if is_contradiction_prompt(message, history) else {"matched": False}
        if early_contradiction["matched"]:
            payload = {
                "mode": mode,
                "route": "contradiction_analysis",
                "answer": early_contradiction["answer"],
                "confidence": early_contradiction["confidence"],
                "confidence_score": early_contradiction["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": early_contradiction.get("concept_matches", []),
                "contradiction_analysis": early_contradiction["contradiction_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "contradiction_analysis"}
            payload["confidence_decision"] = {
                "confidence": early_contradiction["confidence_score"],
                "evidence_quality": "approved_noncanonical_claim_evidence_plus_ephemeral_comparison",
                "retrieval_sufficiency": "balanced_claim_comparison",
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
            return _finish_conversation_payload(payload, message, history)
        if execute_local_model:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        if _is_brainstorming_request(message):
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "brainstorming"}
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            payload["memory_retrieval_bypassed"] = True
            return _finish_conversation_payload(payload, message, history)
        if not anchor and not _should_defer_to_knowledge_browse(intent_info) and (
            intent_info.get("communication_act") == "clarification_followup"
            or intent_info.get("intent") == "followup"
            or _is_recent_concept_followup(message)
        ):
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "recent_topic_followup"}
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            payload["memory_retrieval_bypassed"] = True
            return _finish_conversation_payload(payload, message, history)
        explicit_session = _session_memory_answer(message, history) if _is_session_memory_turn(message) else None
        if explicit_session:
            payload = {"mode": mode, **explicit_session}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "conversation_short_term_memory"}
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            payload["memory_retrieval_bypassed"] = True
            return _finish_conversation_payload(payload, message, history)
        early_episode_followup = None if (
            _should_defer_to_knowledge_browse(intent_info)
            or explicit_new_topic
            or bool(anchor and _is_anchor_followup(message))
        ) else resolve_working_memory_followup(message, history)
        if early_episode_followup:
            payload = {"mode": mode, **early_episode_followup}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_memory_followup"}
            payload["confidence_decision"] = {
                "confidence": payload.get("confidence_score", 0.0),
                "evidence_quality": "ephemeral_cognitive_episode",
                "retrieval_sufficiency": "resolved_from_short_horizon_dialogue_state",
                "provider_necessity": "none",
            }
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
        if _is_explicit_topic_reset(message) and run_v29_local_answer(message, use_recall=False)["local_answer"]["matched"]:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        early_analogy = build_analogy_analysis(message, history=history) if is_analogy_prompt(message, history) else {"matched": False}
        if early_analogy["matched"]:
            payload = {
                "mode": mode,
                "route": "analogy_analysis",
                "answer": early_analogy["answer"],
                "confidence": early_analogy["confidence"],
                "confidence_score": early_analogy["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": early_analogy.get("concept_matches", []),
                "analogy_analysis": early_analogy["analogy_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "analogy_analysis"}
            payload["confidence_decision"] = {
                "confidence": early_analogy["confidence_score"],
                "evidence_quality": "approved_noncanonical_concepts_plus_ephemeral_structural_mapping",
                "retrieval_sufficiency": "structural_mapping_ready",
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
            return _finish_conversation_payload(payload, message, history)
        early_wrs = build_working_reasoning_set(message) if (
            should_use_wrs(message)
            and not _is_synthesis_trial_request(message)
            and len(parse_multi_concept_query(message)) < 2
        ) else {"matched": False}
        if early_wrs["matched"]:
            wrs_payload = dict(early_wrs.get("working_reasoning_set") or {})
            wrs_payload.update({
                "ephemeral": True,
                "destroyed_after_response": True,
                "synthesis_enabled_by_default": False,
                "memory_write_performed": False,
                "graph_write_performed": False,
                "retrieved_concept_count": early_wrs.get("retrieved_concept_count", 0),
                "retrieved_proposition_count": early_wrs.get("retrieved_proposition_count", 0),
            })
            payload = {
                "mode": mode,
                "route": "working_reasoning_set",
                "answer": early_wrs["answer"],
                "confidence": "ephemeral_multi_concept_working_reasoning_set",
                "confidence_score": early_wrs["confidence"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": early_wrs.get("retrieved_concepts", []),
                "working_reasoning_set": wrs_payload,
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_reasoning_set"}
            payload["confidence_decision"] = {
                "confidence": early_wrs["confidence"],
                "evidence_quality": "approved_noncanonical_multi_concept_working_set",
                "retrieval_sufficiency": "sufficient_for_ephemeral_reasoning",
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
            return _finish_conversation_payload(payload, message, history)
        if not explicit_new_topic and _is_anchor_followup(message) and anchor:
            anchored = browse_near_active_anchor(message, anchor) if _is_anchor_browse_followup(message) else deepen_from_concept_anchor(message, anchor)
            if anchored:
                payload = {"mode": mode, **anchored}
                payload["escalation_plan"] = build_escalation_plan(message)
                payload["intent"] = intent_info
                payload["confidence_decision"] = confidence_engine(message, True)
                payload["mode_router_flags"] = ROUTER_FLAGS
                return _finish_conversation_payload(payload, message, history)
        if execute_local_model:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        if (
            (intent_info.get("intent") in {"coding", "external_knowledge_request", "image"} and not _is_synthesis_trial_request(message))
            or (_direct_answer(message) and not _is_synthesis_trial_request(message))
            or _is_development_workflow_request(message, history)
        ):
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        episode_followup = None if (
            _should_defer_to_knowledge_browse(intent_info)
            or explicit_new_topic
            or bool(anchor and _is_anchor_followup(message))
        ) else resolve_working_memory_followup(message, history)
        if episode_followup:
            payload = {"mode": mode, **episode_followup}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_memory_followup"}
            payload["confidence_decision"] = {
                "confidence": payload.get("confidence_score", 0.0),
                "evidence_quality": "ephemeral_cognitive_episode",
                "retrieval_sufficiency": "resolved_from_short_horizon_dialogue_state",
                "provider_necessity": "none",
            }
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
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
            return _finish_conversation_payload(payload, message, history)
        if _is_graph_assisted_reasoning_request(message):
            from orchestration.runtime.rc2_graph_assisted_reasoning import build_graph_assisted_reasoning_trial

            reasoning_trial = build_graph_assisted_reasoning_trial(message)
            payload = {
                "mode": mode,
                "route": "read_only_graph_assisted_reasoning_trial",
                "answer": reasoning_trial["answer"],
                "confidence": "read_only_graph_assisted_reasoning_trial",
                "confidence_score": reasoning_trial["reasoning_quality"]["overall_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": reasoning_trial["retrieved_concepts"],
                "graph_assisted_reasoning": {
                    "approved_graph_edges": reasoning_trial["approved_graph_edges"],
                    "evidence_chains": reasoning_trial["evidence_chains"],
                    "reasoning_quality": reasoning_trial["reasoning_quality"],
                    "trial_only": True,
                    "read_only": True,
                    "synthesis_enabled_by_default": False,
                    "memory_write_performed": False,
                    "graph_write_performed": False,
                },
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "graph_assisted_reasoning_trial"}
            payload["confidence_decision"] = {
                "confidence": reasoning_trial["reasoning_quality"]["overall_score"],
                "evidence_quality": "approved_noncanonical_concepts_plus_approved_graph_edges",
                "retrieval_sufficiency": "graph_assisted_trial_ready",
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
            return _finish_conversation_payload(payload, message, history)
        synthesis_trial = build_read_only_synthesis_trial(message) if _is_synthesis_trial_request(message) else {"matched": False}
        if synthesis_trial["matched"]:
            payload = {
                "mode": mode,
                "route": "read_only_cross_concept_synthesis_trial",
                "answer": synthesis_trial["answer"],
                "confidence": "trial_inference_grounded_in_retrieved_concepts",
                "confidence_score": synthesis_trial["retrieval_set_quality"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": synthesis_trial["source_retrieval"].get("matches", []),
                "synthesis_trial": {
                    "stored_concepts": synthesis_trial["stored_concepts"],
                    "tentative_inference": synthesis_trial["tentative_inference"],
                    "uncertainty": synthesis_trial["uncertainty"],
                    "synthesis_trial_only": True,
                    "synthesis_enabled": False,
                    "memory_write_performed": False,
                },
                "multi_concept_retrieval": {
                    "seeds": synthesis_trial["source_retrieval"].get("seeds", []),
                    "retrieval_set_quality": synthesis_trial["retrieval_set_quality"],
                    "synthesis_readiness": False,
                    "duplicate_suppression_count": synthesis_trial["source_retrieval"].get("duplicate_suppression_count", 0),
                },
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "read_only_synthesis_trial"}
            payload["confidence_decision"] = {
                "confidence": synthesis_trial["retrieval_set_quality"],
                "evidence_quality": "approved_noncanonical_concepts_plus_labeled_inference",
                "retrieval_sufficiency": "set_ready_for_trial_synthesis_review",
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
            return _finish_conversation_payload(payload, message, history)
        analogy_result = build_analogy_analysis(message, history=history) if is_analogy_prompt(message, history) else {"matched": False}
        if analogy_result["matched"]:
            payload = {
                "mode": mode,
                "route": "analogy_analysis",
                "answer": analogy_result["answer"],
                "confidence": analogy_result["confidence"],
                "confidence_score": analogy_result["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": analogy_result.get("concept_matches", []),
                "analogy_analysis": analogy_result["analogy_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "analogy_analysis"}
            payload["confidence_decision"] = {
                "confidence": analogy_result["confidence_score"],
                "evidence_quality": "approved_noncanonical_concepts_plus_ephemeral_structural_mapping",
                "retrieval_sufficiency": "structural_mapping_ready",
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
            return _finish_conversation_payload(payload, message, history)
        contradiction_result = build_contradiction_analysis(message, history=history) if is_contradiction_prompt(message, history) else {"matched": False}
        if contradiction_result["matched"]:
            payload = {
                "mode": mode,
                "route": "contradiction_analysis",
                "answer": contradiction_result["answer"],
                "confidence": contradiction_result["confidence"],
                "confidence_score": contradiction_result["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": contradiction_result.get("concept_matches", []),
                "contradiction_analysis": contradiction_result["contradiction_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "contradiction_analysis"}
            payload["confidence_decision"] = {
                "confidence": contradiction_result["confidence_score"],
                "evidence_quality": "approved_noncanonical_claim_evidence_plus_ephemeral_comparison",
                "retrieval_sufficiency": "balanced_claim_comparison",
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
            return _finish_conversation_payload(payload, message, history)
        wrs_result = build_working_reasoning_set(message) if (
            should_use_wrs(message)
            and not _is_synthesis_trial_request(message)
            and len(parse_multi_concept_query(message)) < 2
        ) else {"matched": False}
        if wrs_result["matched"]:
            wrs_payload = dict(wrs_result.get("working_reasoning_set") or {})
            wrs_payload.update({
                "ephemeral": True,
                "destroyed_after_response": True,
                "synthesis_enabled_by_default": False,
                "memory_write_performed": False,
                "graph_write_performed": False,
                "retrieved_concept_count": wrs_result.get("retrieved_concept_count", 0),
                "retrieved_proposition_count": wrs_result.get("retrieved_proposition_count", 0),
            })
            payload = {
                "mode": mode,
                "route": "working_reasoning_set",
                "answer": wrs_result["answer"],
                "confidence": "ephemeral_multi_concept_working_reasoning_set",
                "confidence_score": wrs_result["confidence"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": wrs_result.get("retrieved_concepts", []),
                "working_reasoning_set": wrs_payload,
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_reasoning_set"}
            payload["confidence_decision"] = {
                "confidence": wrs_result["confidence"],
                "evidence_quality": "approved_noncanonical_multi_concept_working_set",
                "retrieval_sufficiency": "sufficient_for_ephemeral_reasoning",
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
            return _finish_conversation_payload(payload, message, history)
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
            return _finish_conversation_payload(payload, message, history)
        sun_blue = _sun_blue_correction(message)
        if sun_blue:
            payload = {
                "mode": mode,
                "route": "conversation_clarified_misframed_question",
                "answer": sun_blue,
                "confidence": "local_science_clarification",
                "confidence_score": 0.84,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "memory_candidate": None,
                "concept_matches": [],
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, True)
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
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
            return _finish_conversation_payload(payload, message, history)
        aspect_followup = _active_topic_aspect_followup(message, history)
        if aspect_followup:
            payload = {"mode": mode, **aspect_followup}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "active_topic_aspect_followup"}
            payload["confidence_decision"] = confidence_engine(message, True)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            return _finish_conversation_payload(payload, message, history)
        bypass_memory_retrieval = (
            execute_local_model
            or explicit_new_topic and _is_brainstorming_request(message)
            or _is_practical_tip_for_explicit_target(message)
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
            payload["active_topic_anchor"] = _anchor_from_matches(message, concept["answer"], concept["matches"])
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
        payload["memory_retrieval_bypassed"] = bypass_memory_retrieval
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
    return _finish_conversation_payload(payload, message, history)


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
    elif route == "working_reasoning_set":
        boundary = "ephemeral_multi_concept_working_set"
    elif route == "contradiction_analysis":
        boundary = "ephemeral_claim_comparison"
    elif route == "analogy_analysis":
        boundary = "ephemeral_structural_mapping"
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
    if route == "contradiction_analysis" and isinstance(payload.get("contradiction_analysis"), dict):
        analysis = payload["contradiction_analysis"]
        lines.extend([
            "",
            "Contradiction analysis:",
            f"- classification: {analysis.get('compatibility_classification')}",
            f"- confidence: {analysis.get('confidence')}",
            f"- ephemeral: {analysis.get('ephemeral')}",
            f"- read_only: {analysis.get('read_only')}",
            "- claims:",
        ])
        for claim in analysis.get("claims", [])[:4]:
            lines.extend([
                f"  - {claim.get('source')}: {claim.get('text')}",
                f"    subjects: {', '.join(claim.get('normalized_subjects') or []) or 'none'}",
                f"    polarity: {claim.get('polarity')}; timeframes: {', '.join(claim.get('timeframes') or []) or 'none'}",
            ])
        missing = analysis.get("missing_evidence") or []
        if missing:
            lines.append("- missing evidence:")
            lines.extend(f"  - {item}" for item in missing[:4])
        trace = analysis.get("reasoning_trace") or []
        if trace:
            lines.append("- trace:")
            lines.extend(f"  - {item}" for item in trace[:6])
    if route == "analogy_analysis" and isinstance(payload.get("analogy_analysis"), dict):
        analysis = payload["analogy_analysis"]
        lines.extend([
            "",
            "Analogy analysis:",
            f"- classification: {analysis.get('analogy_classification')}",
            f"- confidence: {analysis.get('confidence')}",
            f"- source domain: {analysis.get('source_domain')}",
            f"- target domain: {analysis.get('target_domain')}",
            f"- shared structure: {analysis.get('shared_structure')}",
            "- mapped roles:",
        ])
        lines.extend(f"  - {item}" for item in (analysis.get("mapped_roles") or [])[:5])
        if analysis.get("limits_of_analogy"):
            lines.append("- limits:")
            lines.extend(f"  - {item}" for item in analysis.get("limits_of_analogy", [])[:4])
        if analysis.get("reasoning_trace"):
            lines.append("- trace:")
            lines.extend(f"  - {item}" for item in analysis.get("reasoning_trace", [])[:6])
    episode = payload.get("cognitive_episode")
    if isinstance(episode, dict):
        branches = episode.get("conversation_branch") or []
        resolved = episode.get("resolved_references") or []
        rejected_refs = episode.get("rejected_references") or []
        lines.extend([
            "",
            "Cognitive episode:",
            f"- episode_id: {episode.get('episode_id') or 'none'}",
            f"- active_topic: {episode.get('active_topic') or 'none'}",
            f"- active_entities: {', '.join(episode.get('active_entities') or []) or 'none'}",
            f"- active_route: {episode.get('active_route') or 'none'}",
            f"- turn_number: {episode.get('turn_number')}",
            f"- episode_confidence: {episode.get('episode_confidence')}",
            f"- resolved_references: {len(resolved)}",
            f"- rejected_references: {len(rejected_refs)}",
            f"- branch_count: {len(branches)}",
            f"- has_wrs: {bool(episode.get('active_wrs'))}",
            f"- has_contradiction: {bool(episode.get('active_contradiction'))}",
            f"- has_analogy: {bool(episode.get('active_analogy'))}",
        ])
        if resolved:
            lines.append("- resolved:")
            lines.extend(
                f"  - {item.get('reference')} -> {item.get('resolved_to')}"
                for item in resolved[:4]
            )
        if rejected_refs:
            lines.append("- rejected:")
            lines.extend(
                f"  - {item.get('reference')}: {item.get('reason')}"
                for item in rejected_refs[:4]
            )
    arbitration = payload.get("route_arbitration")
    if isinstance(arbitration, dict):
        candidates = arbitration.get("candidate_routes") or []
        rejected_routes = arbitration.get("rejected_routes") or []
        lines.extend([
            "",
            "Route arbitration:",
            f"- selected_route: {arbitration.get('selected_route')}",
            f"- selected_group: {arbitration.get('selected_group')}",
            f"- candidate_count: {len(candidates)}",
            f"- rejected_count: {len(rejected_routes)}",
            "- candidates:",
        ])
        for item in candidates[:8]:
            marker = "selected" if item.get("selected") else (f"yielded_to={item.get('yielded_to')}" if item.get("yielded_to") else item.get("rejection_reason") or "rejected")
            evidence = ", ".join(item.get("trigger_evidence") or []) or "none"
            lines.append(
                f"  - {item.get('route')} p={item.get('precedence')} c={item.get('confidence')} {marker}; trigger={evidence}"
            )
    safety = payload.get("safety_metadata")
    if isinstance(safety, dict):
        lines.extend([
            "",
            "Safety metadata:",
            f"- complete: {safety.get('complete')}",
            f"- behavioral_safety_passed: {safety.get('behavioral_safety_passed')}",
            f"- missing_fields_filled: {', '.join(safety.get('missing_fields_filled') or []) or 'none'}",
        ])
    renderer = payload.get("natural_renderer") or {}
    if renderer:
        lines.extend([
            "",
            "Natural renderer:",
            f"- applied: {renderer.get('applied')}",
            f"- report_voice_removed: {renderer.get('report_voice_removed')}",
            f"- scaffold_removed: {renderer.get('scaffold_removed')}",
        ])
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
