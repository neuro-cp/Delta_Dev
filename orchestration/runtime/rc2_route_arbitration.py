"""RC2 route arbitration trace for cognitive-route boundary debugging.

This module does not dispatch routes. It builds a deterministic, read-only
explanation of which routes had a plausible claim on a turn, their precedence,
and why the selected route won or yielded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_analogy_engine import is_analogy_prompt
from orchestration.runtime.rc2_cognitive_episode import resolve_working_memory_followup
from orchestration.runtime.rc2_contradiction_engine import is_contradiction_prompt
from orchestration.runtime.rc2_working_reasoning_set import should_use_wrs


PRECEDENCE = [
    ("safety", 1),
    ("explicit_user_command", 2),
    ("social_conversation", 3),
    ("contradiction_analysis", 4),
    ("analogy_analysis", 5),
    ("working_memory_reference_resolution", 6),
    ("working_reasoning_set", 7),
    ("multi_concept_retrieval", 8),
    ("single_concept_retrieval", 9),
    ("local_model_consent_required", 10),
    ("provider_consent_gate", 11),
]

PRECEDENCE_BY_ROUTE = dict(PRECEDENCE)

ROUTE_GROUPS = {
    "contradiction_analysis": "contradiction_analysis",
    "analogy_analysis": "analogy_analysis",
    "session_memory": "working_memory_reference_resolution",
    "recent_concept_followup": "working_memory_reference_resolution",
    "working_reasoning_set": "working_reasoning_set",
    "developmental_multi_concept_retrieval": "multi_concept_retrieval",
    "developmental_concept_memory": "single_concept_retrieval",
    "substrate_first_conversation": "single_concept_retrieval",
    "developmental_concept_domain_browse": "single_concept_retrieval",
    "developmental_concept_browse": "single_concept_retrieval",
    "local_model_consent_required": "local_model_consent_required",
    "gpt_support_approval_preview": "provider_consent_gate",
    "provider_support_answer": "provider_consent_gate",
    "social_conversation": "social_conversation",
    "local_conversation_scaffold": "social_conversation",
}

SAFETY_FIELDS = {
    "provider_calls_performed": False,
    "web_search_performed": False,
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "autonomous_action_performed": False,
    "scheduler_action_performed": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}


@dataclass
class RouteCandidate:
    route: str
    precedence: int
    confidence: float
    trigger_evidence: list[str]
    required_context: str
    context_available: bool
    selected: bool = False
    yielded_to: str | None = None
    rejection_reason: str = ""


def normalize_safety_payload(payload: dict[str, Any]) -> dict[str, Any]:
    missing = []
    for key, default in SAFETY_FIELDS.items():
        if key not in payload:
            payload[key] = default
            missing.append(key)
    payload["safety_metadata"] = {
        "required_fields": sorted(SAFETY_FIELDS),
        "missing_fields_filled": sorted(missing),
        "complete": True,
        "behavioral_safety_passed": all(payload.get(key) is False for key in SAFETY_FIELDS),
        "read_only": True,
    }
    return payload


def build_route_arbitration_trace(
    message: str,
    history: list[dict[str, str]] | None,
    selected_route: str,
    intent_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    history = history or []
    selected_group = ROUTE_GROUPS.get(selected_route, selected_route or "unknown")
    candidates = _build_candidates(message, history, intent_info or {})
    if not any(item.route == selected_group for item in candidates):
        candidates.append(RouteCandidate(
            route=selected_group,
            precedence=PRECEDENCE_BY_ROUTE.get(selected_group, 99),
            confidence=0.5,
            trigger_evidence=[f"actual_dispatch:{selected_route}"],
            required_context="route_specific",
            context_available=True,
        ))
    candidates = sorted(candidates, key=lambda item: (item.precedence, -item.confidence, item.route))
    selected_precedence = PRECEDENCE_BY_ROUTE.get(selected_group, 99)
    for item in candidates:
        if item.route == selected_group:
            item.selected = True
            item.rejection_reason = ""
        elif item.precedence > selected_precedence:
            item.yielded_to = selected_group
            item.rejection_reason = "lower_precedence_than_selected_route"
        elif item.precedence < selected_precedence:
            item.rejection_reason = "candidate_not_matched_or_context_insufficient_at_dispatch"
        else:
            item.rejection_reason = "same_precedence_non_selected_candidate"
    return {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "selected_route": selected_route,
        "selected_group": selected_group,
        "precedence_order": [{"route": route, "precedence": precedence} for route, precedence in PRECEDENCE],
        "candidate_routes": [asdict(item) for item in candidates],
        "rejected_routes": [
            asdict(item) for item in candidates
            if not item.selected
        ],
        "read_only": True,
        "ephemeral": True,
    }


def safety_schema_complete(payload: dict[str, Any]) -> bool:
    return all(key in payload for key in SAFETY_FIELDS)


def write_arbitration_reference(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "precedence": [{"route": route, "precedence": precedence} for route, precedence in PRECEDENCE],
        "route_groups": ROUTE_GROUPS,
        "safety_fields": SAFETY_FIELDS,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_candidates(message: str, history: list[dict[str, str]], intent_info: dict[str, Any]) -> list[RouteCandidate]:
    lower = _norm(message)
    candidates = [
        RouteCandidate(
            route="safety",
            precedence=1,
            confidence=1.0,
            trigger_evidence=["hard_invariants_checked"],
            required_context="none",
            context_available=True,
        )
    ]
    if _explicit_command(lower):
        candidates.append(RouteCandidate(
            route="explicit_user_command",
            precedence=2,
            confidence=0.9,
            trigger_evidence=["explicit_command_or_mode_control"],
            required_context="none",
            context_available=True,
        ))
    if intent_info.get("safe_no_route") is True or intent_info.get("intent") in {"greeting", "thanks", "compliment", "acknowledgement", "cancel"}:
        candidates.append(RouteCandidate(
            route="social_conversation",
            precedence=3,
            confidence=float(intent_info.get("confidence") or 0.82),
            trigger_evidence=[str(intent_info.get("communication_act") or intent_info.get("intent") or "social")],
            required_context="none",
            context_available=True,
        ))
    if is_contradiction_prompt(message, history):
        candidates.append(RouteCandidate(
            route="contradiction_analysis",
            precedence=4,
            confidence=0.93,
            trigger_evidence=_matched_terms(lower, ("contradict", "conflict", "inconsistent", "both be true", "cannot both")),
            required_context="current_or_prior_claims",
            context_available=bool(history) or _has_two_claims(lower),
        ))
    if is_analogy_prompt(message, history):
        candidates.append(RouteCandidate(
            route="analogy_analysis",
            precedence=5,
            confidence=0.9,
            trigger_evidence=_matched_terms(lower, ("analogy", "like", "similar", "maps to", "works and what breaks", "where does that analogy")),
            required_context="source_and_target_or_prior_analogy",
            context_available=bool(history) or _has_analogy_shape(lower),
        ))
    wm_payload = resolve_working_memory_followup(message, history)
    if wm_payload:
        episode = wm_payload.get("cognitive_episode") or {}
        candidates.append(RouteCandidate(
            route="working_memory_reference_resolution",
            precedence=6,
            confidence=float(wm_payload.get("confidence_score") or 0.72),
            trigger_evidence=_matched_terms(lower, ("that", "this", "those", "it", "first", "second", "earlier", "return to", "continue", "go deeper")),
            required_context="recent_episode_or_branch",
            context_available=bool(episode.get("active_topic")),
        ))
    if should_use_wrs(message) or ("what works" in lower and "break" in lower) or ("similar as systems" in lower):
        candidates.append(RouteCandidate(
            route="working_reasoning_set",
            precedence=7,
            confidence=0.84,
            trigger_evidence=_matched_terms(lower, ("compare", "connect", "relate", "common", "higher order", "what evidence", "what information")),
            required_context="retrievable_concept_set",
            context_available=True,
        ))
    if _looks_multi_concept(lower):
        candidates.append(RouteCandidate(
            route="multi_concept_retrieval",
            precedence=8,
            confidence=0.76,
            trigger_evidence=["multiple_named_entities_or_relation_terms"],
            required_context="approved_concept_candidates",
            context_available=True,
        ))
    if _looks_single_concept(lower):
        candidates.append(RouteCandidate(
            route="single_concept_retrieval",
            precedence=9,
            confidence=0.74,
            trigger_evidence=["single_topic_lookup"],
            required_context="approved_concept_candidate",
            context_available=True,
        ))
    if _looks_unknown_or_external(lower):
        candidates.append(RouteCandidate(
            route="local_model_consent_required",
            precedence=10,
            confidence=0.68,
            trigger_evidence=["insufficient_local_or_external_knowledge_signal"],
            required_context="operator_consent",
            context_available=False,
        ))
    return candidates


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower().replace("-", " ")).strip()


def _matched_terms(lower: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in lower] or ["implicit_route_signal"]


def _explicit_command(lower: str) -> bool:
    return lower in {"ask gpt", "yes ask gpt", "remember that", "don't remember that", "forget that"} or lower.startswith(("switch to ", "open "))


def _has_two_claims(lower: str) -> bool:
    return " and " in lower and any(term in lower for term in ("both", "true", "claim", "statement"))


def _has_analogy_shape(lower: str) -> bool:
    return " is like " in lower or "/" in lower or " to " in lower and " like " in lower


def _looks_multi_concept(lower: str) -> bool:
    return any(term in lower for term in ("compare", "relate", "connect", "with", "between", "common")) and len(re.findall(r"\b(and|with|between|to)\b", lower)) >= 1


def _looks_single_concept(lower: str) -> bool:
    return lower.startswith(("what is ", "what are ", "explain ", "tell me about ", "do you know anything about "))


def _looks_unknown_or_external(lower: str) -> bool:
    return any(term in lower for term in ("latest", "current", "gpt", "web", "source", "outside", "unknown"))
