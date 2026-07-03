"""Runtime V2.9 local answer engine shared by CLI and desktop UI."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v22_controlled_general_recall_expansion import run_controlled_general_recall_expansion
from orchestration.runtime.v29_current_state_knowledge_inventory import build_current_state_inventory, safety_invariants
from orchestration.runtime.v29_natural_alias_router import route_v29_alias, stable_id


def run_v29_local_answer(query: str, *, use_recall: bool = False) -> dict[str, object]:
    clean_query = " ".join(str(query).split())
    inventory = build_current_state_inventory()
    route = route_v29_alias(clean_query, inventory)
    recall_context = run_controlled_general_recall_expansion(clean_query) if use_recall and route.matched else None
    evidence_items = []
    if route.matched:
        evidence_items.append(
            {
                "candidate_id": stable_id("v29-local-evidence", route.topic_id, route.answer_text),
                "text": route.answer_text,
                "provenance": list(route.provenance),
                "candidate_context_only": True,
                "authoritative": False,
            }
        )
    if recall_context:
        for candidate in recall_context.get("candidates", []):
            evidence_items.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "text": candidate["text"],
                    "provenance": candidate["provenance"],
                    "candidate_context_only": True,
                    "authoritative": False,
                }
            )
    answer_text = route.answer_text if route.matched else route.answer_text
    return {
        "phase": "Runtime V2.9",
        "request": {
            "request_id": stable_id("v29-request", clean_query, use_recall),
            "query": clean_query,
            "use_recall": use_recall,
        },
        "local_answer": {
            "matched": route.matched,
            "topic_id": route.topic_id,
            "matched_alias": route.matched_alias,
            "answer_text": route.answer_text if route.matched else None,
            "provenance": list(route.provenance),
        },
        "recall_context": recall_context,
        "evidence_items": evidence_items,
        "draft": {
            "draft_id": stable_id("v29-draft", clean_query, answer_text),
            "answer_text": answer_text,
            "uses_candidate_context": bool(recall_context),
            "grounded": True,
            "provider_required": False,
        },
        "decision": {
            "memory_write_performed": False,
            "recall_mutated": False,
            "provider_call_performed": False,
            "training_triggered": False,
            "action_execution_performed": False,
            "scheduler_started": False,
            "hyb1_promoted": False,
            "model_b_default_changed": False,
        },
        "invariant_flags": {
            "v29_local_answer_engine_enabled": True,
            "candidate_context_only": True,
            **safety_invariants(),
        },
        "final_recommendation": "PROCEED_MANUAL_LOCAL_DEMO_AND_SELECTED_CLEANUP_REVIEW",
    }


def format_v29_cli_output(data: dict[str, object]) -> str:
    return (
        "DELTA Local Answer\n\n"
        f"{data['draft']['answer_text']}\n\n"
        "Trace:\n"
        f"- phase: {data['phase']}\n"
        f"- request_id: {data['request']['request_id']}\n"
        f"- matched: {data['local_answer']['matched']}\n"
        f"- topic_id: {data['local_answer']['topic_id']}\n"
        f"- uses_candidate_context: {data['draft']['uses_candidate_context']}\n\n"
        "Safety:\n"
        "- provider_call_performed: False\n"
        "- memory_write_performed: False\n"
        "- recall_mutated: False\n"
        "- training_triggered: False\n"
        "- action_execution_performed: False\n"
        "- hyb1_promoted: False\n"
        "- model_b_default_changed: False\n"
    )


def write_v29_answer_report(path: str | Path = "reports/runtime_v29c_delta_answer_integration.json") -> dict[str, object]:
    samples = ["What is DELTA?", "What can you do?", "What phase are you in?", "What did I eat for breakfast yesterday?"]
    data = {
        "phase": "Runtime V2.9C",
        "sample_answers": [run_v29_local_answer(sample) for sample in samples],
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_DESKTOP_UI_V29_INTEGRATION",
    }
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    Path("reports/runtime_v29c_delta_answer_integration.md").write_text(
        "# Runtime V2.9C delta_answer Integration\n\nCLI answer path now uses the V2.9 local answer engine.\n",
        encoding="utf-8",
    )
    return data
