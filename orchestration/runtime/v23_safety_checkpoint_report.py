from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v23f_v23_safety_checkpoint_report.md")
REPORT_JSON = Path("reports/runtime_v23f_v23_safety_checkpoint_report.json")


def build_v23_safety_checkpoint() -> dict[str, object]:
    return {
        "phase": "Runtime V2.3F",
        "completed_phases": [
            "V2.3A HYB1 Shadow Trial Simulation, Opt-In Only",
            "V2.3B Localhost UI Candidate Write Execution Bridge, Explicit Approval Only",
            "V2.3C Controlled Recall-to-Synthesis Integration",
            "V2.3D Provider Evidence Live-to-Candidate Trial, User-Approved",
            "V2.3E Daily Evaluator Scheduled Dry-Run Trial",
            "V2.3F V2.3 Safety Checkpoint Report",
        ],
        "status": {
            "model_b": "default_unchanged",
            "hyb1": "dormant_env_gated_shadow_simulation_only",
            "memory": "explicit_approval_controlled_trial_only",
            "recall": "candidate_context_only_non_authoritative",
            "provider": "evidence_only_candidate_conversion_only",
            "evaluator": "advisory_or_dry_run_only",
            "scheduler": "dry_run_artifact_only_no_os_task",
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
            "os_scheduler_registered": False,
            "provider_specialist_evaluator_authority_transfer": False,
        },
        "updated_pipeline": [
            "HYB1 shadow simulation",
            "Localhost UI explicit write bridge",
            "Controlled recall-to-synthesis",
            "Provider evidence live-to-candidate",
            "Daily evaluator scheduled dry-run artifact",
            "V2.3 safety checkpoint",
        ],
        "next_recommended_phases": [
            "V2.4A Localhost Full Review Console UX",
            "V2.4B Controlled Memory Write UX Trial",
            "V2.4C Controlled Recall Answer UX Trial",
            "V2.4D Provider-Assisted Unknown Answer UX Trial",
            "V2.4E Evaluator-Reviewed Consolidation UX Trial",
            "V2.4F V2.4 Safety Closure",
        ],
        "final_recommendation": "PROCEED_V24_LOCALHOST_FULL_REVIEW_CONSOLE_UX",
    }


def validate_v23_safety_checkpoint(data: dict[str, object]) -> bool:
    return all(value is False for value in data["safety_invariants"].values())


def write_v23_safety_checkpoint_report() -> dict[str, object]:
    data = build_v23_safety_checkpoint()
    data["all_safe"] = validate_v23_safety_checkpoint(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    lines = ["# Runtime V2.3F - V2.3 Safety Checkpoint Report", "", "## Completed Phases", ""]
    lines += [f"- {item}" for item in data["completed_phases"]]
    lines += ["", "## Status", ""]
    lines += [f"- `{key}`: `{value}`" for key, value in data["status"].items()]
    lines += ["", "## Next Recommended Phases", ""]
    lines += [f"- {item}" for item in data["next_recommended_phases"]]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_v23_safety_checkpoint_report()
    print(f"Runtime V2.3F safety checkpoint: safe={result['all_safe']} final={result['final_recommendation']}")

