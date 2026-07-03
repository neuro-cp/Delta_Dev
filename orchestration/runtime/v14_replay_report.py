from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_replay import RUNTIME_V14E_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_LIVE_CANONICAL_STORE_DESIGN"


def build_sleep_replay_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4E",
        "title": "Sleep / Replay Consolidation Design Scaffold",
        "summary": (
            "V1.4E adds inert replay batch, replay review, consolidation candidate, "
            "consolidation decision, and sleep-cycle plan records. Replay can now evaluate "
            "whether an episode or feedback signal deserves future consolidation, but it "
            "does not consolidate directly."
        ),
        "current_default": {
            "runtime_v13_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only",
            "training": "disabled",
            "canonical_mutation": "disabled",
        },
        "pipeline": [
            "EpisodeTrace",
            "FeedbackCaptureRecord",
            "ReplayReviewMarker",
            "PruningReviewProposal",
            "ReplayBatch",
            "ReplayReviewResult",
            "ConsolidationCandidate",
            "ConsolidationDecision",
            "SleepCyclePlan",
        ],
        "core_rule": "Replay evaluates future consolidation eligibility; replay does not consolidate directly.",
        "files_added": [
            "orchestration/runtime/v14_replay.py",
            "orchestration/runtime/v14_consolidation.py",
            "orchestration/runtime/v14_sleep_cycle.py",
            "orchestration/runtime/v14_replay_report.py",
            "tests/runtime_v14/test_v14_sleep_replay_consolidation.py",
            "docs/runtime_v14e_sleep_replay_consolidation_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14E_INVARIANT_FLAGS),
        "inactive_systems": {
            "training": False,
            "active_replay_loop": False,
            "scheduler_or_daemon": False,
            "canonical_writes": False,
            "live_pruning": False,
            "provider_calls": False,
            "specialist_routing_activation": False,
            "execution_gate_activation": False,
            "recall_bridge": False,
            "routing_influence": False,
        },
        "old_runtime_path": {
            "old_engine_runtime_adopted_directly": False,
            "preserved_conceptual_path": "observation -> episode -> replay review -> consolidation candidate -> decision",
        },
        "verification": {
            "py_compile": "passed for V1.4E modules and tests",
            "tests": "passed: tests/runtime_v14",
        },
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_sleep_replay_report(
    md_path: str | Path = "reports/runtime_v14e_sleep_replay_consolidation_design.md",
    json_path: str | Path = "reports/runtime_v14e_sleep_replay_consolidation_design.json",
) -> None:
    data = build_sleep_replay_report_data()
    md = _render_markdown(data)
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(md, encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4E - Sleep / Replay Consolidation Design Scaffold",
        "",
        "## Summary",
        str(data["summary"]),
        "",
        "## Current Default",
    ]
    current_default = data["current_default"]
    assert isinstance(current_default, dict)
    lines.extend(f"- {key}: {value}" for key, value in current_default.items())
    lines.extend(
        [
            "",
            "## Pipeline",
        ]
    )
    lines.extend(f"- {item}" for item in data["pipeline"])
    lines.extend(
        [
            "",
            "## Core Rule",
            str(data["core_rule"]),
            "",
            "## Files Added",
        ]
    )
    lines.extend(f"- `{item}`" for item in data["files_added"])
    lines.extend(
        [
            "",
            "## Safety Boundaries",
        ]
    )
    boundaries = data["safety_boundaries"]
    assert isinstance(boundaries, dict)
    lines.extend(f"- {key}: {value}" for key, value in boundaries.items())
    lines.extend(
        [
            "",
            "## Inactive Systems",
        ]
    )
    inactive = data["inactive_systems"]
    assert isinstance(inactive, dict)
    lines.extend(f"- {key}: {value}" for key, value in inactive.items())
    lines.extend(
        [
            "",
            "## Original DELTA Path",
            "The old `G:\\Delta_DevV0\\engine\\runtime.py` is not adopted directly.",
            f"Preserved conceptual path: {data['old_runtime_path']['preserved_conceptual_path']}",  # type: ignore[index]
            "",
            "## Final Recommendation",
            str(data["final_recommendation"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    write_sleep_replay_report()
