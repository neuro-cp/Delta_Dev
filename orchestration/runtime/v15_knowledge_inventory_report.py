from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_knowledge_inventory import (
    RuntimeKnowledgeInventory,
    build_runtime_knowledge_inventory,
    summarize_inventory,
)


REPORT_MD = Path("reports/runtime_v15_knowledge_inventory.md")
REPORT_JSON = Path("reports/runtime_v15_knowledge_inventory.json")


def build_knowledge_inventory_report_data(repo_root: str | Path = ".") -> dict[str, object]:
    inventory = build_runtime_knowledge_inventory(repo_root)
    summary = summarize_inventory(inventory)
    return {
        "phase": "Runtime V1.5 Knowledge Inventory",
        "title": "DELTA Runtime Knowledge Inventory / Self-Inspection",
        "status": "repo-local-self-inspection-only_no-training_no-provider_no-memory-mutation",
        "final_recommendation": "PROCEED_WITH_CONSOLE_UI_REVIEW_OR_V15E_HYB1_LIMITED_OPT_IN_TRIAL_DESIGN",
        "inventory": inventory.as_dict(),
        "summary": summary,
        "questions_answered": {
            "what_does_delta_know_from_static_repo_artifacts": inventory.repo_local_knowledge_summary,
            "what_can_delta_answer_locally_without_provider_calls": list(inventory.local_answer_scope),
            "what_is_still_scaffold_only": list(inventory.inactive_capabilities),
            "what_is_active": list(inventory.active_capabilities),
            "what_remains_disabled": list(inventory.inactive_capabilities),
            "was_any_model_training_performed": False,
            "was_hyb1_promoted": False,
            "what_knowledge_is_unavailable": list(inventory.unavailable_knowledge),
        },
        "test_status": "run py_compile and tests/runtime_v14 tests/runtime_v15 to verify",
    }


def write_knowledge_inventory_report(repo_root: str | Path = ".") -> dict[str, object]:
    data = build_knowledge_inventory_report_data(repo_root)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data["inventory"], data), encoding="utf-8")
    return data


def format_inventory_summary(data: dict[str, object]) -> str:
    summary = data["summary"]
    questions = data["questions_answered"]
    return "\n".join(
        [
            "DELTA Runtime Knowledge Inventory",
            "",
            f"Status: {data['status']}",
            f"Final recommendation: {data['final_recommendation']}",
            "",
            "Summary:",
            f"- model training occurred: {summary['model_training_occurred']}",
            f"- HYB1 promoted: {summary['hyb1_promoted']}",
            f"- provider calls occurred: {summary['provider_calls_occurred']}",
            f"- memory/recall mutation occurred: {summary['memory_or_recall_mutation_occurred']}",
            "",
            "Local answer scope:",
            *[f"- {item}" for item in questions["what_can_delta_answer_locally_without_provider_calls"]],
            "",
            "Unavailable knowledge:",
            *[f"- {item}" for item in questions["what_knowledge_is_unavailable"]],
        ]
    )


def _render_markdown(inventory_dict: dict[str, object], report_data: dict[str, object]) -> str:
    inventory = RuntimeKnowledgeInventory(
        inventory_id=str(inventory_dict["inventory_id"]),
        repo_root=str(inventory_dict["repo_root"]),
        generated_at=str(inventory_dict["generated_at"]),
        items=(),
        invariant_flags=dict(inventory_dict["invariant_flags"]),
        active_capabilities=tuple(inventory_dict["active_capabilities"]),
        inactive_capabilities=tuple(inventory_dict["inactive_capabilities"]),
        unavailable_knowledge=tuple(inventory_dict["unavailable_knowledge"]),
        local_answer_scope=tuple(inventory_dict["local_answer_scope"]),
        learned_model_knowledge_summary=str(inventory_dict["learned_model_knowledge_summary"]),
        repo_local_knowledge_summary=str(inventory_dict["repo_local_knowledge_summary"]),
    )
    counts = report_data["summary"]["category_counts"]
    lines = [
        "# DELTA Runtime Knowledge Inventory / Self-Inspection",
        "",
        "This is repo-local self-inspection only. It does not train, call providers, mutate memory, activate recall, or promote HYB1.",
        "",
        f"- Status: `{report_data['status']}`",
        f"- Final recommendation: `{report_data['final_recommendation']}`",
        "",
        "## What DELTA Knows From Static Repo Artifacts",
        "",
        inventory.repo_local_knowledge_summary,
        "",
        "## Learned Model Knowledge",
        "",
        inventory.learned_model_knowledge_summary,
        "",
        "## Local Answer Scope",
        "",
    ]
    lines.extend(f"- {item}" for item in inventory.local_answer_scope)
    lines.extend(["", "## Active Capabilities", ""])
    lines.extend(f"- {item}" for item in inventory.active_capabilities)
    lines.extend(["", "## Inactive Capabilities", ""])
    lines.extend(f"- {item}" for item in inventory.inactive_capabilities)
    lines.extend(["", "## Unavailable Knowledge", ""])
    lines.extend(f"- {item}" for item in inventory.unavailable_knowledge)
    lines.extend(["", "## Category Counts", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in counts.items())
    lines.extend(["", "## Safety Answers", ""])
    lines.extend(
        [
            "- Codex did not train model weights.",
            "- DELTA has repo-local architectural/self-description knowledge.",
            "- DELTA can answer questions about its own scaffold, phase history, safety boundaries, and local reports.",
            "- DELTA cannot yet answer arbitrary world questions unless provider/model integration is later added.",
            "- Canonical memory remains inactive.",
            "- Training remains inactive.",
            "- HYB1 remains dormant/env-gated and was not promoted.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    data = write_knowledge_inventory_report()
    print(format_inventory_summary(data))
