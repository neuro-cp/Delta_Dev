"""Local ARC III reasoning answers."""

from __future__ import annotations

from orchestration.runtime.arc_iii_reasoning_engine import run_reasoning


def is_arc_iii_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    return any(
        trigger in normalized
        for trigger in (
            "why is this true",
            "what evidence supports it",
            "what evidence opposes it",
            "show reasoning graph",
            "show confidence",
            "show discarded hypotheses",
            "show reflection",
        )
    )


def run_arc_iii_answer(query: str) -> dict[str, object]:
    reasoning = run_reasoning(query)
    normalized = " ".join(str(query).lower().split())
    if "evidence supports" in normalized:
        answer = "The supporting evidence is shown as an explicit cited evidence chain from question to observation, evidence, relationship, concept, and hypothesis."
        payload = {"evidence_chain": reasoning["evidence_chain"]}
    elif "evidence opposes" in normalized:
        answer = "Opposing evidence is handled by the contradiction framework. ARC III presents conflicts and does not silently choose."
        payload = {"contradiction_framework": reasoning["contradiction_framework"]}
    elif "reasoning graph" in normalized:
        answer = "The reasoning graph is session-only and destroyed after the request."
        payload = {"reasoning_graph": reasoning["reasoning_graph"]}
    elif "confidence" in normalized:
        answer = "Confidence propagates through graph edges and never exceeds the strongest supporting evidence."
        payload = {"derived_confidence": reasoning["derived_confidence"]}
    elif "discarded hypotheses" in normalized:
        answer = "Discarded hypotheses are alternatives that were lower ranked by support, confidence, coverage, or risk."
        payload = {"discarded_hypotheses": reasoning["hypotheses"][1:]}
    elif "reflection" in normalized:
        answer = "The reflection pass reports missing evidence, weak assumptions, contradictions, and alternative explanations."
        payload = {"reflection_pass": reasoning["reflection_pass"]}
    else:
        answer = reasoning["explanation_tree"]["selected_explanation"]
        payload = {"explanation_tree": reasoning["explanation_tree"]}
    return {
        "phase": "Runtime ARC III",
        "query": query,
        "answer_text": answer,
        **payload,
        "safety": {
            "knowledge_mutation_performed": False,
            "memory_mutation_performed": False,
            "provider_call_performed": False,
            "training_performed": False,
            "scheduler_started": False,
            "action_execution_performed": False,
            "hypotheses_promoted": False,
        },
        "final_recommendation": "PROCEED_ARC_IV_DELIBERATIVE_RESPONSE_SYNTHESIS_DESIGN",
    }
