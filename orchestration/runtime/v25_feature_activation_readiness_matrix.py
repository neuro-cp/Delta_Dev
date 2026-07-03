from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v25b_feature_activation_readiness_matrix.md")
REPORT_JSON = Path("reports/runtime_v25b_feature_activation_readiness_matrix.json")

FEATURES = (
    "controlled_memory_writes",
    "controlled_recall",
    "provider_live_trial",
    "evaluator_live_trial",
    "scheduler_dry_run",
    "scheduler_live",
    "hyb1_shadow",
    "hyb1_promotion",
    "training_dataset_export",
    "training_job_execution",
    "action_execution",
)


def build_feature_activation_readiness_matrix() -> dict[str, object]:
    matrix = {}
    for feature in FEATURES:
        if feature in {"controlled_memory_writes", "controlled_recall", "scheduler_dry_run", "hyb1_shadow"}:
            status = "explicit_approval_required" if feature != "controlled_recall" else "dry_run_only"
        elif feature in {"hyb1_promotion", "training_job_execution", "action_execution", "scheduler_live"}:
            status = "blocked_by_safety"
        else:
            status = "ready_for_human_review"
        matrix[feature] = {
            "status": status,
            "activated": False,
            "blockers": [] if status in {"dry_run_only", "explicit_approval_required", "ready_for_human_review"} else ["requires_future_safety_phase"],
        }
    return {
        "phase": "Runtime V2.5B",
        "matrix": matrix,
        "invariant_flags": {
            "feature_activation_readiness_matrix_enabled": True,
            "readiness_only": True,
            "feature_activated": False,
            "training_activated": False,
            "scheduler_started": False,
            "hyb1_promoted": False,
            "action_execution_performed": False,
            "model_b_default_changed": False,
        },
        "final_recommendation": "PROCEED_CONTROLLED_TRAINING_DATASET_EXPORT_TRIAL",
    }


def validate_feature_activation_matrix_safe(data: dict[str, object]) -> bool:
    flags = data["invariant_flags"]
    return all(not item["activated"] for item in data["matrix"].values()) and flags["feature_activation_readiness_matrix_enabled"] and flags["readiness_only"] and all(
        value is False for key, value in flags.items() if key not in {"feature_activation_readiness_matrix_enabled", "readiness_only"}
    )


def write_feature_activation_readiness_matrix_report() -> dict[str, object]:
    data = build_feature_activation_readiness_matrix()
    data["all_safe"] = validate_feature_activation_matrix_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    lines = ["# Runtime V2.5B - Feature Activation Readiness Matrix", "", "No feature is activated by this matrix.", ""]
    lines += [f"- `{name}`: `{entry['status']}`" for name, entry in data["matrix"].items()]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_feature_activation_readiness_matrix_report()
    print(f"Runtime V2.5B feature matrix: safe={result['all_safe']} final={result['final_recommendation']}")

