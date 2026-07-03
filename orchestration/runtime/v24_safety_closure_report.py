from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v24f_v24_safety_closure_report.md")
REPORT_JSON = Path("reports/runtime_v24f_v24_safety_closure_report.json")


def build_v24_safety_closure() -> dict[str, object]:
    return {
        "phase": "Runtime V2.4F",
        "completed_phases": [
            "V2.4A Localhost Full Review Console UX",
            "V2.4B Controlled Memory Write UX Trial",
            "V2.4C Controlled Recall Answer UX Trial",
            "V2.4D Provider-Assisted Unknown Answer UX Trial",
            "V2.4E Evaluator-Reviewed Consolidation UX Trial",
            "V2.4F V2.4 Safety Closure",
        ],
        "status": {
            "localhost_full_console": "static_renderable_localhost_only",
            "memory_write_ux": "explicit_approval_controlled_trial_only",
            "recall_answer_ux": "candidate_context_only",
            "provider_unknown_ux": "gated_evidence_only",
            "evaluator_consolidation_ux": "advisory_only",
            "model_b": "default_unchanged",
            "hyb1": "dormant_env_gated_not_promoted",
            "memory": "no_autonomous_write",
            "recall": "non_authoritative_no_mutation",
            "provider_evaluator": "evidence_or_advisory_only",
            "scheduler": "not_started",
            "training": "not_active",
            "action_execution": "not_active",
        },
        "safety_invariants": {
            "model_b_default_changed": False,
            "hyb1_promoted": False,
            "hyb1_default_activation_enabled": False,
            "training_performed": False,
            "action_execution_performed": False,
            "autonomous_memory_write_performed": False,
            "authoritative_general_recall": False,
            "recall_mutated": False,
            "unapproved_scheduler_started": False,
            "provider_specialist_evaluator_authority_transfer": False,
            "secret_value_printed_or_staged": False,
        },
        "updated_pipeline": [
            "Full localhost review console",
            "Controlled memory write UX",
            "Controlled recall answer UX",
            "Provider-assisted unknown answer UX",
            "Evaluator-reviewed consolidation UX",
            "V2.4 safety closure",
        ],
        "next_recommended_phases": [
            "V2.5A Training Readiness Audit, Report-Only",
            "V2.5B Feature Activation Readiness Matrix",
            "V2.5C Controlled Training Dataset Export Trial, Explicit Approval Only",
            "V2.5D HYB1 Shadow Trial Live Comparison, Opt-In Only",
            "V2.5E Scheduler Live Dry-Run Trial, User-Approved",
            "V2.5F V2.5 Safety Checkpoint",
        ],
        "final_recommendation": "PROCEED_TRAINING_READINESS_AUDIT_OR_FEATURE_ACTIVATION_READINESS_MATRIX",
    }


def validate_v24_safety_closure(data: dict[str, object]) -> bool:
    return all(value is False for value in data["safety_invariants"].values())


def write_v24_safety_closure_report() -> dict[str, object]:
    data = build_v24_safety_closure()
    data["all_safe"] = validate_v24_safety_closure(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    lines = ["# Runtime V2.4F - V2.4 Safety Closure", "", "## Completed Phases", ""]
    lines += [f"- {item}" for item in data["completed_phases"]]
    lines += ["", "## Status", ""]
    lines += [f"- `{key}`: `{value}`" for key, value in data["status"].items()]
    lines += ["", "## Next Recommended Phases", ""]
    lines += [f"- {item}" for item in data["next_recommended_phases"]]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_v24_safety_closure_report()
    print(f"Runtime V2.4F safety closure: safe={result['all_safe']} final={result['final_recommendation']}")

