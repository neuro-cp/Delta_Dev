from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_canonical_store import RUNTIME_V14F_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_TEMPORARY_PRUNING_PROJECTION_DESIGN"


def build_canonical_store_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4F",
        "title": "Live Canonical Store Design Scaffold",
        "summary": (
            "V1.4F defines the inert contract for future canonical memory drafts, "
            "inactive canonical record shapes, store decisions, store plans, revision "
            "records, and rollback plans. It does not activate canonical writes or "
            "connect canonical memory to runtime recall."
        ),
        "current_default": {
            "runtime_v13_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only",
            "training": "disabled",
            "canonical_writes": "disabled",
            "runtime_recall_bridge": "disabled",
        },
        "pipeline": [
            "ConsolidationCandidate",
            "ConsolidationDecision",
            "CanonicalMemoryDraft",
            "CanonicalStoreDecision",
            "CanonicalMemoryRecord",
            "CanonicalRevisionRecord",
            "CanonicalRollbackPlan",
            "CanonicalStorePlan",
        ],
        "files_added": [
            "orchestration/runtime/v14_canonical_store.py",
            "orchestration/runtime/v14_canonical_revision.py",
            "orchestration/runtime/v14_canonical_report.py",
            "tests/runtime_v14/test_v14_canonical_store_design.py",
            "docs/runtime_v14f_live_canonical_store_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14F_INVARIANT_FLAGS),
        "inactive_systems": {
            "canonical_write_path": False,
            "active_canonical_store": False,
            "runtime_recall_bridge": False,
            "activation_attention_integration": False,
            "training": False,
            "live_pruning": False,
            "canonical_pruning": False,
            "provider_calls": False,
            "scheduler_or_daemon": False,
            "specialist_routing_activation": False,
            "execution_gate_activation": False,
        },
        "verification": {
            "py_compile": "passed for V1.4F modules and tests",
            "tests": "passed: tests/runtime_v14",
        },
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_canonical_store_report(
    md_path: str | Path = "reports/runtime_v14f_live_canonical_store_design.md",
    json_path: str | Path = "reports/runtime_v14f_live_canonical_store_design.json",
) -> None:
    data = build_canonical_store_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4F - Live Canonical Store Design Scaffold",
        "",
        "## Summary",
        str(data["summary"]),
        "",
        "## Current Default",
    ]
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
            "Canonical memory is now represented as a governed target contract, not an active store.",
            "Drafts and inactive records preserve provenance and rollback planning, but they are not connected to activation, attention, or runtime recall.",
            "",
            "## Final Recommendation",
            str(data["final_recommendation"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    write_canonical_store_report()
