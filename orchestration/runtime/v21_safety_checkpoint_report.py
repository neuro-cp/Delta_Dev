from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v21f_v21_safety_checkpoint_report.md")
REPORT_JSON = Path("reports/runtime_v21f_v21_safety_checkpoint_report.json")


def build_v21_safety_checkpoint() -> dict[str, object]:
    return {
        "phase": "Runtime V2.1F",
        "completed_phases": [
            "V2.1A Web / Localhost Review UI Prototype",
            "V2.1B Controlled General Memory Trial Expansion",
            "V2.1C Provider Live Trial, User-Approved",
            "V2.1D Daily Evaluator Scheduler Activation, User-Approved",
            "V2.1E HYB1 Re-evaluation, Report-Only",
            "V2.1F V2.1 Safety Checkpoint Report",
        ],
        "active_capabilities": [
            "localhost review UI rendering",
            "structured approval export",
            "controlled explicit-approval memory expansion",
            "candidate-context recall inspection",
            "provider live trial dry-run and gated one-shot path",
            "scheduler local artifact design",
            "HYB1 report-only re-evaluation",
        ],
        "inactive_capabilities": [
            "training",
            "fine-tuning",
            "model weight update",
            "HYB1 default activation",
            "authoritative recall",
            "unapproved scheduler/background worker",
            "action execution",
            "autonomous memory writes",
        ],
        "status": {
            "model_b": "default_unchanged",
            "hyb1": "dormant_env_gated_report_only",
            "localhost_ui": "local_only_prototype",
            "memory": "controlled_explicit_approval_only",
            "recall": "candidate_context_only",
            "provider": "dry_run_default_user_approved_live_path_only",
            "scheduler": "disabled_by_default_local_artifact_gate_only",
            "training": "not_active",
            "action_execution": "not_active",
        },
        "safety_invariants": {
            "model_b_default_changed": False,
            "hyb1_promoted": False,
            "training_performed": False,
            "action_execution_performed": False,
            "autonomous_memory_write_performed": False,
            "authoritative_general_recall": False,
            "recall_mutated": False,
            "unapproved_scheduler_started": False,
            "provider_specialist_evaluator_authority_transfer": False,
        },
        "updated_pipeline": [
            "Localhost review UI prototype",
            "Controlled memory expansion",
            "User-approved provider live trial path",
            "User-approved scheduler local artifact gate",
            "HYB1 report-only re-evaluation",
            "V2.1 safety checkpoint",
        ],
        "next_recommended_phases": [
            "V2.2A Localhost UI Mutation Bridge, Explicit Approval Only",
            "V2.2B Controlled General Recall Expansion",
            "V2.2C Provider Evidence to Memory Candidate Conversion",
            "V2.2D Evaluator-Assisted Memory Candidate Review",
            "V2.2E HYB1 Opt-In Shadow Trial Design",
            "V2.2F V2.2 Safety Closure",
        ],
        "final_recommendation": "PROCEED_V22_LOCALHOST_UI_MUTATION_BRIDGE_OR_CONTROLLED_RECALL_EXPANSION",
    }


def validate_v21_safety_checkpoint(data: dict[str, object]) -> bool:
    return all(value is False for value in data["safety_invariants"].values())


def write_v21_safety_checkpoint_report() -> dict[str, object]:
    data = build_v21_safety_checkpoint()
    data["all_safe"] = validate_v21_safety_checkpoint(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    lines = ["# Runtime V2.1F - V2.1 Safety Checkpoint Report", "", "## Completed Phases", ""]
    lines += [f"- {item}" for item in data["completed_phases"]]
    lines += ["", "## Status", ""]
    lines += [f"- `{key}`: `{value}`" for key, value in data["status"].items()]
    lines += ["", "## Next Recommended Phases", ""]
    lines += [f"- {item}" for item in data["next_recommended_phases"]]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_v21_safety_checkpoint_report()
    print(f"Runtime V2.1F safety checkpoint: safe={result['all_safe']} final={result['final_recommendation']}")
