from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_specialist_merge import RUNTIME_V14J_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_RECALL_BRIDGE_DESIGN"


def build_specialist_merge_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4J",
        "title": "Dormant Specialist Result Merge Protocol Design",
        "summary": (
            "V1.4J defines an inert specialist evidence merge protocol. It can represent "
            "specialist evidence packets, claims, evidence links, conflicts, scorecards, "
            "report-only merge decisions, reports, and design-only plans. It does not call "
            "providers, route specialists, transfer authority, mutate memory, train, prune, "
            "or change runtime behavior."
        ),
        "principles": [
            "specialist result != truth",
            "merge != authority",
            "evidence packet != canonical memory",
            "dormant merge != provider call",
        ],
        "current_default": {
            "runtime_v13_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only",
            "provider_calls": "disabled",
            "active_specialist_routing": "disabled",
            "authority_transfer": "disabled",
        },
        "pipeline": [
            "SpecialistEvidencePacket",
            "SpecialistResultClaim",
            "SpecialistEvidenceLink",
            "SpecialistMergeInput",
            "SpecialistMergeConflict",
            "SpecialistMergeScorecard",
            "SpecialistMergeDecision",
            "SpecialistMergeReport",
            "SpecialistMergePlan",
        ],
        "files_added": [
            "orchestration/runtime/v14_specialist_merge.py",
            "orchestration/runtime/v14_specialist_merge_report.py",
            "tests/runtime_v14/test_v14_specialist_merge_protocol.py",
            "docs/runtime_v14j_dormant_specialist_merge_protocol_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14J_INVARIANT_FLAGS),
        "inactive_systems": {
            "provider_calls": False,
            "active_specialist_routing": False,
            "authority_transfer": False,
            "canonical_memory_mutation": False,
            "live_memory_mutation": False,
            "runtime_recall_mutation": False,
            "training": False,
            "fine_tuning": False,
            "model_weight_update": False,
            "active_pruning": False,
            "projection_application": False,
            "scheduler_or_daemon": False,
            "execution_gate_activation": False,
        },
        "verification": {
            "py_compile": "passed for V1.4J modules and tests",
            "tests": "passed: tests/runtime_v14",
        },
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_specialist_merge_report(
    md_path: str | Path = "reports/runtime_v14j_dormant_specialist_merge_protocol_design.md",
    json_path: str | Path = "reports/runtime_v14j_dormant_specialist_merge_protocol_design.json",
) -> None:
    data = build_specialist_merge_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4J - Dormant Specialist Result Merge Protocol Design",
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
            "Dormant specialist merge accepts evidence packets only as report material.",
            "A merge candidate is not truth, authority, canonical memory, or a provider call.",
            "",
            "## Final Recommendation",
            str(data["final_recommendation"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    write_specialist_merge_report()
