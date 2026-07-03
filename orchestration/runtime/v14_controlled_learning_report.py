from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_controlled_learning import RUNTIME_V14H_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_REPORT_ONLY_HYPOTHESIS_ARBITRATION_DESIGN"


def build_controlled_learning_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4H",
        "title": "Controlled Learning Design",
        "summary": (
            "V1.4H defines a governed, rollback-aware, evidence-bound controlled-learning scaffold. "
            "It can represent eligibility signals, evidence packets, inactive learning candidates, "
            "safety reviews, review-only decisions, design-only plans, rollback plans, and audit records. "
            "It does not train, fine-tune, export datasets, mutate memory, or change runtime behavior."
        ),
        "principles": [
            "learning_design != learning",
            "eligibility != promotion",
            "review != training",
            "candidate != canonical mutation",
            "offline hypothesis != live behavior change",
            "rollback plan != applied rollback",
        ],
        "current_default": {
            "runtime_v13_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only",
            "training": "disabled",
            "fine_tuning": "disabled",
            "runtime_recall_mutation": "disabled",
        },
        "pipeline": [
            "AnswerTrace / FeedbackCaptureRecord / ReplayReviewResult / ConsolidationCandidate",
            "CanonicalStoreDecision / TemporaryPruningProjection",
            "LearningEligibilitySignal",
            "LearningEvidencePacket",
            "LearningCandidate",
            "LearningSafetyReview",
            "ControlledLearningDecision",
            "ControlledLearningPlan",
            "LearningRollbackPlan",
            "LearningAuditRecord",
        ],
        "files_added": [
            "orchestration/runtime/v14_controlled_learning.py",
            "orchestration/runtime/v14_learning_audit.py",
            "orchestration/runtime/v14_controlled_learning_report.py",
            "tests/runtime_v14/test_v14_controlled_learning_design.py",
            "docs/runtime_v14h_controlled_learning_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14H_INVARIANT_FLAGS),
        "inactive_systems": {
            "training": False,
            "fine_tuning": False,
            "model_weight_update": False,
            "training_dataset_export": False,
            "autonomous_learning": False,
            "background_learning": False,
            "canonical_memory_mutation": False,
            "live_memory_mutation": False,
            "runtime_recall_mutation": False,
            "active_pruning": False,
            "projection_application": False,
            "provider_calls": False,
            "scheduler_or_daemon": False,
            "activation_attention_integration": False,
            "specialist_routing_activation": False,
            "execution_gate_activation": False,
        },
        "verification": {
            "py_compile": "passed for V1.4H modules and tests",
            "tests": "passed: tests/runtime_v14",
        },
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_controlled_learning_report(
    md_path: str | Path = "reports/runtime_v14h_controlled_learning_design.md",
    json_path: str | Path = "reports/runtime_v14h_controlled_learning_design.json",
) -> None:
    data = build_controlled_learning_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4H - Controlled Learning Design",
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
            "Controlled Learning Design is an eligibility and governance scaffold, not training.",
            "Evidence packets are not training datasets, candidates are inactive, decisions are review-only, and rollback plans are not applied.",
            "",
            "## Final Recommendation",
            str(data["final_recommendation"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    write_controlled_learning_report()
