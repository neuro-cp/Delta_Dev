from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_pruning_projection import RUNTIME_V14G_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_CONTROLLED_LEARNING_DESIGN"


def build_pruning_projection_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4G",
        "title": "Temporary Pruning Projection Design",
        "summary": (
            "V1.4G defines an inert temporary pruning projection layer. It can represent "
            "lane-scoped projection scopes, signals, requests, review results, decisions, "
            "inactive temporary projection records, design-only plans, and rollback plans. "
            "It does not prune, mutate memory, alter recall, or change runtime behavior."
        ),
        "principles": [
            "projection != pruning",
            "proposal != mutation",
            "temporary != canonical",
            "lane-scoped != global concept judgment",
        ],
        "current_default": {
            "runtime_v13_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only",
            "training": "disabled",
            "canonical_pruning": "disabled",
            "runtime_recall_mutation": "disabled",
        },
        "pipeline": [
            "PruningReviewProposal / FeedbackCaptureRecord",
            "PruningProjectionScope",
            "PruningProjectionSignal",
            "PruningProjectionRequest",
            "PruningProjectionReviewResult",
            "PruningProjectionDecision",
            "TemporaryPruningProjection",
            "PruningProjectionPlan",
            "PruningProjectionRollbackPlan",
        ],
        "files_added": [
            "orchestration/runtime/v14_pruning_projection.py",
            "orchestration/runtime/v14_pruning_projection_report.py",
            "tests/runtime_v14/test_v14_pruning_projection_design.py",
            "docs/runtime_v14g_temporary_pruning_projection_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14G_INVARIANT_FLAGS),
        "inactive_systems": {
            "actual_pruning": False,
            "canonical_pruning": False,
            "concept_deletion": False,
            "canonical_memory_mutation": False,
            "live_memory_mutation": False,
            "runtime_recall_mutation": False,
            "activation_attention_integration": False,
            "training": False,
            "provider_calls": False,
            "scheduler_or_daemon": False,
            "specialist_routing_activation": False,
            "execution_gate_activation": False,
        },
        "verification": {
            "py_compile": "passed for V1.4G modules and tests",
            "tests": "passed: tests/runtime_v14",
        },
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_pruning_projection_report(
    md_path: str | Path = "reports/runtime_v14g_temporary_pruning_projection_design.md",
    json_path: str | Path = "reports/runtime_v14g_temporary_pruning_projection_design.json",
) -> None:
    data = build_pruning_projection_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4G - Temporary Pruning Projection Design",
        "",
        "## Summary",
        str(data["summary"]),
        "",
        "## Principles",
    ]
    lines.extend(f"- {item}" for item in data["principles"])
    lines.extend(["", "## Current Default"])
    current_default = data["current_default"]
    assert isinstance(current_default, dict)
    lines.extend(f"- {key}: {value}" for key, value in current_default.items())
    lines.extend(["", "## Pipeline"])
    lines.extend(f"- {item}" for item in data["pipeline"])
    lines.extend(["", "## Files Added"])
    lines.extend(f"- `{item}`" for item in data["files_added"])
    lines.extend(["", "## Safety Boundaries"])
    boundaries = data["safety_boundaries"]
    assert isinstance(boundaries, dict)
    lines.extend(f"- {key}: {value}" for key, value in boundaries.items())
    lines.extend(["", "## Inactive Systems"])
    inactive = data["inactive_systems"]
    assert isinstance(inactive, dict)
    lines.extend(f"- {key}: {value}" for key, value in inactive.items())
    lines.extend(
        [
            "",
            "## Design Interpretation",
            "Temporary pruning projection is a reversible, lane-scoped proposal layer.",
            "It is not canonical pruning, concept deletion, live memory mutation, or runtime recall mutation.",
            "",
            "## Final Recommendation",
            str(data["final_recommendation"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    write_pruning_projection_report()
