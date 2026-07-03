from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_hypothesis_arbitration import RUNTIME_V14I_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_DORMANT_SPECIALIST_MERGE_PROTOCOL_DESIGN"


def build_hypothesis_arbitration_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4I",
        "title": "Report-Only Hypothesis Arbitration Design",
        "summary": (
            "V1.4I defines an inert, deterministic, evidence-bound hypothesis arbitration scaffold. "
            "It can compare competing claims with evidence links, unresolved conflicts, scorecards, "
            "report-only decisions, review escalations, and design-only plans. It does not assign truth, "
            "promote hypotheses, mutate memory, call providers, route specialists, or change runtime behavior."
        ),
        "principles": [
            "arbitration != authority",
            "ranking != truth",
            "winner != canonical memory",
            "comparison != mutation",
            "hypothesis != learned belief",
            "report-only != runtime behavior change",
        ],
        "current_default": {
            "runtime_v13_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only",
            "arbitration_authority": "disabled",
            "canonical_writes": "disabled",
            "provider_calls": "disabled",
        },
        "pipeline": [
            "HypothesisClaim",
            "HypothesisEvidenceLink",
            "HypothesisConflict",
            "HypothesisArbitrationInput",
            "HypothesisScorecard",
            "HypothesisArbitrationDecision",
            "HypothesisArbitrationReport",
            "HypothesisArbitrationPlan",
            "HypothesisReviewEscalation",
        ],
        "files_added": [
            "orchestration/runtime/v14_hypothesis_arbitration.py",
            "orchestration/runtime/v14_hypothesis_report.py",
            "tests/runtime_v14/test_v14_hypothesis_arbitration_design.py",
            "docs/runtime_v14i_report_only_hypothesis_arbitration_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14I_INVARIANT_FLAGS),
        "inactive_systems": {
            "arbitration_authority": False,
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
            "activation_attention_integration": False,
            "execution_gate_activation": False,
        },
        "verification": {
            "py_compile": "passed for V1.4I modules and tests",
            "tests": "passed: tests/runtime_v14",
        },
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_hypothesis_arbitration_report(
    md_path: str | Path = "reports/runtime_v14i_report_only_hypothesis_arbitration_design.md",
    json_path: str | Path = "reports/runtime_v14i_report_only_hypothesis_arbitration_design.json",
) -> None:
    data = build_hypothesis_arbitration_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4I - Report-Only Hypothesis Arbitration Design",
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
            "Report-Only Hypothesis Arbitration compares claims without authority.",
            "A report-preferred hypothesis is not truth, canonical memory, a learned belief, or a runtime behavior change.",
            "",
            "## Final Recommendation",
            str(data["final_recommendation"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    write_hypothesis_arbitration_report()
