from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_recall_bridge import RUNTIME_V14K_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_STRUCTURAL_SEMANTIC_ADAPTER_DESIGN"


def build_recall_bridge_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4K",
        "title": "Recall Bridge Design",
        "summary": (
            "V1.4K defines an inert, deterministic recall bridge design scaffold between "
            "canonical-memory design artifacts and future activation/attention/evidence gates. "
            "It can describe source eligibility, hypothetical queries, review-only candidates, "
            "safety reviews, traces, plans, and report entries. It does not activate recall, "
            "connect canonical memory to runtime, mutate memory, alter activation or attention, "
            "select evidence, train, call providers, route specialists, or change runtime behavior."
        ),
        "principles": [
            "bridge design != live recall",
            "candidate != retrieved memory",
            "eligibility != activation",
            "recall trace != recall mutation",
            "canonical record shape != active memory source",
            "recall plan != runtime behavior change",
        ],
        "current_default": {
            "runtime_v13_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only",
            "live_recall": "disabled",
            "activation_attention_integration": "disabled",
            "canonical_writes": "disabled",
        },
        "pipeline": [
            "RecallBridgeSource",
            "RecallBridgeQuery",
            "RecallBridgeCandidate",
            "RecallBridgeSafetyReview",
            "RecallBridgeEligibilityDecision",
            "RecallBridgeTrace",
            "RecallBridgePlan",
            "RecallBridgeReportEntry",
        ],
        "files_added": [
            "orchestration/runtime/v14_recall_bridge.py",
            "orchestration/runtime/v14_recall_bridge_report.py",
            "tests/runtime_v14/test_v14_recall_bridge_design.py",
            "docs/runtime_v14k_recall_bridge_design_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14K_INVARIANT_FLAGS),
        "inactive_systems": {
            "recall_bridge_activation": False,
            "live_recall": False,
            "canonical_memory_as_live_source": False,
            "activation_integration": False,
            "attention_integration": False,
            "evidence_selection_integration": False,
            "canonical_memory_mutation": False,
            "live_memory_mutation": False,
            "runtime_recall_mutation": False,
            "training": False,
            "fine_tuning": False,
            "model_weight_update": False,
            "active_pruning": False,
            "projection_application": False,
            "provider_calls": False,
            "specialist_routing": False,
            "scheduler_or_daemon": False,
            "execution_gate_activation": False,
        },
        "verification": {
            "py_compile": "passed for V1.4K modules and tests",
            "tests": "passed: tests/runtime_v14",
        },
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_recall_bridge_report(
    md_path: str | Path = "reports/runtime_v14k_recall_bridge_design.md",
    json_path: str | Path = "reports/runtime_v14k_recall_bridge_design.json",
) -> None:
    data = build_recall_bridge_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4K - Recall Bridge Design",
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
            "Recall Bridge Design evaluates future eligibility only.",
            "A recall bridge candidate is not retrieved memory, active context, evidence selection, or live recall.",
            "",
            "## Final Recommendation",
            str(data["final_recommendation"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    write_recall_bridge_report()
