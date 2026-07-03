from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_local_knowledge_router import (
    RUNTIME_V15E_LOCAL_ROUTER_FLAGS,
    build_local_knowledge_router_report_entries,
    build_local_knowledge_topics,
    route_local_knowledge_answer,
)


REPORT_MD = Path("reports/runtime_v15e_local_knowledge_inventory_answer_router.md")
REPORT_JSON = Path("reports/runtime_v15e_local_knowledge_inventory_answer_router.json")

SAMPLE_QUESTIONS: tuple[str, ...] = (
    "What is DELTA's current replay and consolidation path?",
    "What is HYB1?",
    "Is HYB1 active?",
    "What is Model B?",
    "Can DELTA remember things yet?",
    "Can DELTA train itself yet?",
    "Can DELTA call providers?",
    "Can DELTA execute actions?",
    "What is currently active?",
    "What is still disabled?",
    "What is the safest next activation gate?",
    "What can DELTA not answer yet?",
    "Who won a game yesterday?",
)


def build_local_knowledge_router_report_data() -> dict[str, object]:
    topics = build_local_knowledge_topics()
    entries = build_local_knowledge_router_report_entries()
    samples = [route_local_knowledge_answer(question).as_dict() for question in SAMPLE_QUESTIONS]
    matched = [sample for sample in samples if sample["matched"]]
    unsupported = [sample for sample in samples if not sample["matched"]]
    return {
        "phase": "Runtime V1.5E",
        "title": "Local Knowledge Inventory Answer Router",
        "status": "local-static-router-only_no-provider_no-memory_no-training_no-action",
        "final_recommendation": "PROCEED_SELF_QUESTION_TEST_PACK",
        "topic_count": len(topics),
        "topics": [topic.as_dict() for topic in topics],
        "report_entries": [entry.as_dict() for entry in entries],
        "sample_routes": samples,
        "known_local_answer_count": len(matched),
        "unsupported_sample_count": len(unsupported),
        "invariant_flags": dict(RUNTIME_V15E_LOCAL_ROUTER_FLAGS),
        "safety_summary": {
            "model_b_default_unchanged": True,
            "hyb1_promoted": False,
            "hyb1_default_activation_enabled": False,
            "provider_calls_performed": False,
            "tool_calls_enabled": False,
            "action_execution_enabled": False,
            "memory_mutation_enabled": False,
            "canonical_write_enabled": False,
            "runtime_recall_active": False,
            "runtime_recall_mutation_enabled": False,
            "training_enabled": False,
            "scheduler_enabled": False,
            "runtime_defaults_changed": False,
        },
    }


def write_local_knowledge_router_report() -> dict[str, object]:
    data = build_local_knowledge_router_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def format_local_knowledge_router_summary(data: dict[str, object]) -> str:
    safety = data["safety_summary"]
    return "\n".join(
        [
            "Runtime V1.5E Local Knowledge Inventory Answer Router",
            "",
            f"Status: {data['status']}",
            f"Topics: {data['topic_count']}",
            f"Sample local answers: {data['known_local_answer_count']}",
            f"Unsupported samples: {data['unsupported_sample_count']}",
            f"Final recommendation: {data['final_recommendation']}",
            "",
            "Safety:",
            f"- provider_calls_performed: {safety['provider_calls_performed']}",
            f"- memory_mutation_enabled: {safety['memory_mutation_enabled']}",
            f"- canonical_write_enabled: {safety['canonical_write_enabled']}",
            f"- training_enabled: {safety['training_enabled']}",
            f"- hyb1_default_activation_enabled: {safety['hyb1_default_activation_enabled']}",
            f"- model_b_default_unchanged: {safety['model_b_default_unchanged']}",
        ]
    )


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.5E - Local Knowledge Inventory Answer Router",
        "",
        "This report describes a deterministic local router for DELTA self-knowledge questions. It is not provider integration, active recall, canonical memory, training, or semantic intelligence.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Topic count: `{data['topic_count']}`",
        f"- Known local sample answers: `{data['known_local_answer_count']}`",
        f"- Unsupported sample count: `{data['unsupported_sample_count']}`",
        "",
        "## Safety Summary",
        "",
    ]
    for key, value in data["safety_summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Topics", ""])
    for topic in data["topics"]:
        lines.append(f"- `{topic['topic_id']}`: {topic['source_summary']}")
    lines.extend(["", "## Sample Routes", ""])
    for sample in data["sample_routes"]:
        status = "matched" if sample["matched"] else "unsupported"
        lines.append(f"- `{sample['user_message']}` -> `{status}` / `{sample['topic_id']}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Local knowledge routing is not learned memory.",
            "- Static report summary is not active recall.",
            "- Answer template is not provider generation.",
            "- Question match is not semantic authority.",
            "- Unsupported answer is not failure.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    report = write_local_knowledge_router_report()
    print(format_local_knowledge_router_summary(report))
