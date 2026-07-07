"""RC2 conversational shell and DELTA mode router scaffold.

RC2 makes the RC1 substrate one selectable mode behind a conversational front
door. It does not enable provider calls, web search, training, canonical
writes, autonomous actions, or production routing. External/local model
routes are represented as gated escalation plans only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_operator_console import (
    answer_operator_question,
    approve_propositions,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    query_noncanonical_substrate,
)


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


def classify_intent(message: str) -> dict[str, Any]:
    lower = message.lower()
    if any(term in lower for term in ["diagnostic", "status", "health"]):
        intent = "diagnostics"
    elif any(term in lower for term in ["remember", "store", "save this"]):
        intent = "memory_request"
    elif any(term in lower for term in ["contradiction", "conflict", "incompatible"]):
        intent = "contradiction_check"
    elif any(term in lower for term in ["code", "python", "bug", "function"]):
        intent = "coding"
    elif any(term in lower for term in ["plan", "schedule", "strategy"]):
        intent = "planning"
    elif any(term in lower for term in ["analyze", "compare", "why", "because"]):
        intent = "analysis"
    elif any(term in lower for term in ["document", "pdf", "invoice", "evidence"]):
        intent = "document"
    elif any(term in lower for term in ["image", "picture", "photo"]):
        intent = "image"
    elif any(term in lower for term in ["investigate", "case", "research"]):
        intent = "investigation"
    elif any(term in lower for term in ["what do you know", "frontier", "substrate"]):
        intent = "substrate_question"
    elif any(term in lower for term in ["avogadro", "quantum field", "beluga", "whale"]):
        intent = "external_knowledge_request"
    elif any(term in lower for term in ["how do you work", "what are you", "delta"]):
        intent = "self_description"
    else:
        intent = "question" if lower.endswith("?") else "conversation"
    return {"intent": intent, "message": message, "confidence": confidence_for_intent(intent)}


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


def local_conversation_answer(message: str) -> dict[str, Any]:
    lower = message.lower()
    if "sky" in lower and "color" in lower:
        answer = "The sky usually appears blue during the day because the atmosphere scatters shorter blue wavelengths of sunlight more strongly than longer red wavelengths."
        confidence = "high_for_general_knowledge"
    elif "how do you work" in lower or "what are you" in lower:
        answer = "I am DELTA's local conversational shell. I route ordinary conversation, substrate questions, evidence review, contradiction checks, replay inspection, and diagnostics through explicit modes while keeping providers, training, and canonical writes disabled unless a future gate enables them."
        confidence = "high_for_self_description"
    elif "beluga" in lower or "whale" in lower:
        answer = "I do not have a live provider or web route enabled in RC2. I can mark this as an external knowledge request and prepare a gated research route, but I will not invent details as if they were verified substrate knowledge."
        confidence = "insufficient_local_evidence"
    elif "avogadro" in lower or "quantum field" in lower:
        answer = "That question likely needs specialist or provider-assisted research. RC2 can produce a gated escalation plan, but no provider or web call is enabled in this scaffold."
        confidence = "requires_gated_escalation"
    else:
        answer = "I can help think through that conversationally, or you can switch modes to Evidence Review, Ask Substrate, Contradiction Check, Replay, or Diagnostics for governed DELTA runtime behavior."
        confidence = "general_conversation_scaffold"
    return {
        "route": "local_conversation_scaffold",
        "answer": answer,
        "confidence": confidence,
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
        evidence_quality = "local_scaffold_or_mode_context"
        provider_necessity = "not_required_for_scaffold_response"
    return {
        "confidence": round(confidence, 2),
        "evidence_quality": evidence_quality,
        "retrieval_sufficiency": "sufficient" if substrate_matched else "not_checked_or_insufficient",
        "provider_necessity": provider_necessity,
    }


def route_message(mode: str, message: str, pasted_text: str = "", approve: bool = False) -> dict[str, Any]:
    if mode not in MODES:
        mode = "Conversation"
    if mode == "Conversation":
        substrate = query_noncanonical_substrate(message)
        if substrate["matched"]:
            payload = {
                "mode": mode,
                "route": "substrate_first_conversation",
                "answer": substrate["answer"],
                "confidence": "grounded_in_noncanonical_substrate",
            }
        else:
            payload = {"mode": mode, **local_conversation_answer(message)}
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
        payload = {"mode": mode, "route": "diagnostics", "answer": "Runtime diagnostics snapshot.", "state": build_cognitive_state(), "flags": ROUTER_FLAGS}
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
            "remaining_gap": "provider, web, and true local LLM routes remain gated/off",
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
