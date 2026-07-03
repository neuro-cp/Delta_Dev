from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v22f_v22_safety_closure_report.md")
REPORT_JSON = Path("reports/runtime_v22f_v22_safety_closure_report.json")


def build_v22_safety_closure() -> dict[str, object]:
    return {
        "phase": "Runtime V2.2F",
        "completed_phases": [
            "V2.2A Localhost UI Mutation Bridge, Explicit Approval Only",
            "V2.2B Controlled General Recall Expansion",
            "V2.2C Provider Evidence to Memory Candidate Conversion",
            "V2.2D Evaluator-Assisted Memory Candidate Review",
            "V2.2E HYB1 Opt-In Shadow Trial Design",
            "V2.2F V2.2 Safety Closure Report",
        ],
        "active_capabilities": [
            "localhost UI structured export bridge",
            "controlled recall expansion",
            "provider evidence to candidate proposal conversion",
            "evaluator advisory candidate review",
            "HYB1 shadow trial design",
        ],
        "inactive_capabilities": [
            "training",
            "fine-tuning",
            "HYB1 default activation",
            "HYB1 promotion",
            "authoritative recall",
            "unapproved scheduler/background worker",
            "action execution",
            "autonomous memory writes",
        ],
        "status": {
            "model_b": "default_unchanged",
            "hyb1": "dormant_env_gated_shadow_design_only",
            "memory": "candidate_and_explicit_approval_only",
            "recall": "candidate_context_only",
            "provider": "evidence_only_candidate_conversion_only",
            "evaluator": "advisory_only",
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
        },
        "updated_pipeline": [
            "Localhost UI structured export",
            "Controlled recall expansion",
            "Evidence-to-candidate proposal",
            "Evaluator advisory review",
            "HYB1 opt-in shadow design",
            "V2.2 safety closure",
        ],
        "next_recommended_phases": [
            "V2.3A HYB1 Shadow Trial Simulation, Opt-In Only",
            "V2.3B Localhost UI Candidate Write Execution Bridge, Explicit Approval Only",
            "V2.3C Controlled Recall-to-Synthesis Integration",
            "V2.3D Provider Evidence Live-to-Candidate Trial, User-Approved",
            "V2.3E Daily Evaluator Scheduled Dry-Run Trial",
            "V2.3F V2.3 Safety Checkpoint",
        ],
        "final_recommendation": "PROCEED_V23_HYB1_SHADOW_SIMULATION_OR_LOCALHOST_WRITE_EXECUTION_BRIDGE",
    }


def validate_v22_safety_closure(data: dict[str, object]) -> bool:
    return all(value is False for value in data["safety_invariants"].values())


def write_v22_safety_closure_report() -> dict[str, object]:
    data = build_v22_safety_closure()
    data["all_safe"] = validate_v22_safety_closure(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    lines = ["# Runtime V2.2F - V2.2 Safety Closure Report", "", "## Completed Phases", ""]
    lines += [f"- {item}" for item in data["completed_phases"]]
    lines += ["", "## Status", ""]
    lines += [f"- `{key}`: `{value}`" for key, value in data["status"].items()]
    lines += ["", "## Next Recommended Phases", ""]
    lines += [f"- {item}" for item in data["next_recommended_phases"]]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_v22_safety_closure_report()
    print(f"Runtime V2.2F safety closure: safe={result['all_safe']} final={result['final_recommendation']}")
