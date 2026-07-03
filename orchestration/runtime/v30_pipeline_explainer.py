"""Runtime V3.0 deterministic pipeline explanation.

The explainer describes the already-produced V2.9 local answer payload. It is
read-only instrumentation and does not alter answer routing, recall, memory, or
runtime defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


REPORT_MD = Path("reports/runtime_v30b_pipeline_explanation_engine.md")
REPORT_JSON = Path("reports/runtime_v30b_pipeline_explanation_engine.json")


def explain_answer_pipeline(answer_data: dict[str, object]) -> dict[str, object]:
    request = answer_data["request"]
    local_answer = answer_data["local_answer"]
    draft = answer_data["draft"]
    decision = answer_data["decision"]
    evidence_items = answer_data.get("evidence_items", [])
    return {
        "input": request["query"],
        "route_matched": local_answer["matched"],
        "matched_topic": local_answer["topic_id"],
        "matched_alias": local_answer["matched_alias"],
        "inventory_source": local_answer["provenance"],
        "recall_used": draft["uses_candidate_context"],
        "recall_authoritative": False,
        "evidence_used": [
            {
                "candidate_id": item["candidate_id"],
                "candidate_context_only": item["candidate_context_only"],
                "authoritative": item["authoritative"],
                "provenance": item["provenance"],
            }
            for item in evidence_items
        ],
        "safety_gates_checked": {
            "provider_call_performed": decision["provider_call_performed"],
            "memory_write_performed": decision["memory_write_performed"],
            "recall_mutated": decision["recall_mutated"],
            "training_triggered": decision["training_triggered"],
            "action_execution_performed": decision["action_execution_performed"],
            "scheduler_started": decision["scheduler_started"],
            "hyb1_promoted": decision["hyb1_promoted"],
            "model_b_default_changed": decision["model_b_default_changed"],
        },
        "mutation_status": "none",
        "final_synthesis": draft["answer_text"],
    }


def render_pipeline_explanation(explanation: dict[str, object]) -> str:
    evidence_count = len(explanation["evidence_used"])
    gates = explanation["safety_gates_checked"]
    gate_lines = "\n".join(f"- {name}: {value}" for name, value in gates.items())
    return (
        "Pipeline explanation\n\n"
        f"Input: {explanation['input']}\n"
        f"Route matched: {explanation['route_matched']} ({explanation['matched_topic']})\n"
        f"Matched alias: {explanation['matched_alias'] or 'none'}\n"
        f"Recall used: {explanation['recall_used']} (authoritative: {explanation['recall_authoritative']})\n"
        f"Evidence items: {evidence_count}\n"
        f"Mutation status: {explanation['mutation_status']}\n\n"
        "Safety gates:\n"
        f"{gate_lines}\n\n"
        f"Final synthesis: {explanation['final_synthesis']}"
    )


def build_pipeline_explanation(query: str, *, use_recall: bool = False) -> dict[str, object]:
    answer_data = run_v29_local_answer(query, use_recall=use_recall)
    explanation = explain_answer_pipeline(answer_data)
    return {
        "phase": "Runtime V3.0B",
        "answer_data": answer_data,
        "pipeline_explanation": explanation,
        "rendered_explanation": render_pipeline_explanation(explanation),
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_GUIDED_REVIEW_CONSOLE_UX",
    }


def write_pipeline_explanation_report() -> dict[str, object]:
    sample = build_pipeline_explanation("What is DELTA?")
    data = {
        "phase": "Runtime V3.0B",
        "sample": sample,
        "runtime_behavior_changed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_GUIDED_REVIEW_CONSOLE_UX",
    }
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.0B Pipeline Explanation Engine\n\n"
        "Added deterministic explanation output for local answers: input, matched route, inventory source, recall status, evidence, safety gates, mutation status, and final synthesis.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    print(write_pipeline_explanation_report()["final_recommendation"])
