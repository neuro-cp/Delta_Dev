from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v25a_training_readiness_audit_report_only.md")
REPORT_JSON = Path("reports/runtime_v25a_training_readiness_audit_report_only.json")

TRAINING_READINESS_FLAGS = {
    "training_readiness_audit_enabled": True,
    "report_only": True,
    "training_performed": False,
    "dataset_exported": False,
    "model_artifact_created": False,
    "model_b_default_changed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "scheduler_started": False,
    "action_execution_performed": False,
}


def build_training_readiness_audit() -> dict[str, object]:
    blockers = [
        "missing_dataset_policy",
        "redaction_not_validated_for_training",
        "insufficient_export_approval_path",
        "model_artifact_policy_not_active",
    ]
    return {
        "phase": "Runtime V2.5A",
        "dimensions": {
            "candidate_data_quality": "review_required",
            "provenance_completeness": "partial",
            "approval_status": "explicit_approval_required",
            "redaction_readiness": "not_validated",
            "hallucination_risk": "must_remain_reviewed",
            "evaluator_review_coverage": "advisory_only",
            "rollback_readiness": "design_present",
            "training_hazard_blockers": blockers,
            "model_artifact_policy": "design_only",
            "promotion_policy": "not_training_authority",
        },
        "outcome": "report_only_no_training",
        "blockers": blockers,
        "invariant_flags": dict(TRAINING_READINESS_FLAGS),
        "final_recommendation": "PROCEED_FEATURE_ACTIVATION_READINESS_MATRIX",
    }


def validate_training_readiness_audit_safe(data: dict[str, object]) -> bool:
    flags = data["invariant_flags"]
    return flags["training_readiness_audit_enabled"] and flags["report_only"] and all(
        value is False for key, value in flags.items() if key not in {"training_readiness_audit_enabled", "report_only"}
    )


def write_training_readiness_audit_report() -> dict[str, object]:
    data = build_training_readiness_audit()
    data["all_safe"] = validate_training_readiness_audit_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.5A - Training Readiness Audit, Report-Only",
        "",
        "Training readiness remains report-only. No dataset export, model artifact, fine-tune, or weight update occurred.",
        "",
        f"Outcome: `{data['outcome']}`",
        f"Blockers: `{', '.join(data['blockers'])}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_training_readiness_audit_report()
    print(f"Runtime V2.5A training readiness: safe={result['all_safe']} final={result['final_recommendation']}")

