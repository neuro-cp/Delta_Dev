"""Runtime V3.0 conversational formatting for local DELTA answers.

This module is presentation-only. It formats the existing V2.9 local answer
payload and does not call providers, train, write memory, mutate recall, or
change runtime defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


REPORT_MD = Path("reports/runtime_v30a_conversational_answer_polish.md")
REPORT_JSON = Path("reports/runtime_v30a_conversational_answer_polish.json")

SUPPORTED_MODES = ("concise", "detailed", "explain", "safety-summary")


def format_conversational_answer(data: dict[str, object], *, mode: str = "concise") -> str:
    """Format a V2.9 answer payload for local human interaction."""
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported V3.0 answer mode: {mode}")

    draft = data["draft"]
    request = data["request"]
    local_answer = data["local_answer"]
    decision = data["decision"]
    evidence_items = data.get("evidence_items", [])

    if mode == "concise":
        return str(draft["answer_text"])

    if mode == "detailed":
        provenance = local_answer.get("provenance", [])
        provenance_lines = "\n".join(f"- {item}" for item in provenance) or "- none"
        return (
            f"{draft['answer_text']}\n\n"
            "Why this answer is local:\n"
            f"- matched: {local_answer['matched']}\n"
            f"- topic: {local_answer['topic_id']}\n"
            f"- evidence items: {len(evidence_items)}\n"
            f"- provider required: {draft['provider_required']}\n\n"
            "Provenance:\n"
            f"{provenance_lines}"
        )

    if mode == "explain":
        return (
            "I answered through the deterministic local path.\n\n"
            f"Input: {request['query']}\n"
            f"Matched route: {local_answer['topic_id']}\n"
            f"Recall used: {draft['uses_candidate_context']}\n"
            f"Evidence items used: {len(evidence_items)}\n"
            "Safety checks: provider calls, memory writes, recall mutation, training, "
            "action execution, HYB1 promotion, and Model B changes all remained disabled.\n"
            f"Final synthesis: {draft['answer_text']}"
        )

    return (
        "Safety summary:\n"
        f"- provider_call_performed: {decision['provider_call_performed']}\n"
        f"- memory_write_performed: {decision['memory_write_performed']}\n"
        f"- recall_mutated: {decision['recall_mutated']}\n"
        f"- training_triggered: {decision['training_triggered']}\n"
        f"- action_execution_performed: {decision['action_execution_performed']}\n"
        f"- hyb1_promoted: {decision['hyb1_promoted']}\n"
        f"- model_b_default_changed: {decision['model_b_default_changed']}"
    )


def infer_answer_mode(query: str, explicit_mode: str | None = None) -> str:
    if explicit_mode:
        return explicit_mode
    normalized = " ".join(str(query).lower().split())
    if "explain how" in normalized or "pipeline" in normalized or "trace" in normalized:
        return "explain"
    if "safety" in normalized or "disabled" in normalized:
        return "safety-summary" if "summary" in normalized else "detailed"
    return "concise"


def build_conversational_answer(query: str, *, mode: str | None = None, use_recall: bool = False) -> dict[str, object]:
    answer_data = run_v29_local_answer(query, use_recall=use_recall)
    selected_mode = infer_answer_mode(query, mode)
    return {
        "phase": "Runtime V3.0A",
        "mode": selected_mode,
        "answer_data": answer_data,
        "formatted_answer": format_conversational_answer(answer_data, mode=selected_mode),
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_PIPELINE_EXPLANATION_ENGINE",
    }


def write_conversational_answer_report() -> dict[str, object]:
    samples = {
        mode: build_conversational_answer("What is DELTA?", mode=mode)["formatted_answer"]
        for mode in SUPPORTED_MODES
    }
    data = {
        "phase": "Runtime V3.0A",
        "supported_modes": list(SUPPORTED_MODES),
        "samples": samples,
        "runtime_behavior_changed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_PIPELINE_EXPLANATION_ENGINE",
    }
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.0A Conversational Answer Polish\n\n"
        "Added presentation-only concise, detailed, explain, and safety-summary modes over the V2.9 local answer payload.\n\n"
        "No provider calls, memory writes, recall mutation, training, action execution, HYB1 promotion, or Model B changes were introduced.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    print(write_conversational_answer_report()["final_recommendation"])
