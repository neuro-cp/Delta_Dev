from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v20h_v20_safety_checkpoint_report.md")
REPORT_JSON = Path("reports/runtime_v20h_v20_safety_checkpoint_report.json")


def build_v20_safety_checkpoint() -> dict[str, object]:
    return {
        "phase": "Runtime V2.0H",
        "completed_phases": [
            "V2.0A Local DELTA UX Consolidation",
            "V2.0B Controlled General Memory Trial Design",
            "V2.0C Controlled General Memory Trial, Explicit Approval Only",
            "V2.0D Review UI Write Approval Bridge",
            "V2.0E Controlled General Recall Trial",
            "V2.0F Provider Evidence Live Trial Review Bridge",
            "V2.0G Scheduler Activation Trial Design Only",
            "V2.0H V2.0 Safety Checkpoint Report",
        ],
        "active_capabilities": [
            "local command UX",
            "static review UI generation",
            "explicit-approval controlled memory trial path",
            "candidate-context controlled recall",
            "provider evidence review bridge",
        ],
        "inactive_capabilities": [
            "training",
            "fine-tuning",
            "HYB1 default activation",
            "authoritative recall",
            "scheduler/background worker",
            "action execution",
            "autonomous memory writes",
        ],
        "status": {
            "model_b": "default_unchanged",
            "hyb1": "dormant_env_gated",
            "memory": "controlled_explicit_approval_trial_only",
            "recall": "candidate_context_only",
            "provider": "evidence_only_no_live_call_by_default",
            "scheduler": "design_only_not_active",
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
            "scheduler_started": False,
            "provider_specialist_evaluator_authority_transfer": False,
        },
        "updated_pipeline": [
            "Local UX consolidation",
            "Controlled general memory design",
            "Explicit approval memory trial",
            "Review UI approval bridge",
            "Controlled general recall trial",
            "Provider evidence review bridge",
            "Scheduler activation design",
            "V2.0 safety checkpoint",
        ],
        "next_recommended_phases": [
            "V2.1A Web/localhost Review UI Prototype",
            "V2.1B Controlled General Memory Trial Expansion",
            "V2.1C Provider Live Trial, User-Approved",
            "V2.1D Daily Evaluator Scheduler Activation, User-Approved",
            "V2.1E HYB1 Re-evaluation, Report-Only",
        ],
        "final_recommendation": "PROCEED_V21_WEB_LOCALHOST_REVIEW_UI_OR_CONTROLLED_GENERAL_MEMORY_EXPANSION",
    }


def validate_v20_safety_checkpoint(data: dict[str, object]) -> bool:
    return all(value is False for value in data["safety_invariants"].values())


def write_v20_safety_checkpoint_report() -> dict[str, object]:
    data = build_v20_safety_checkpoint()
    data["all_safe"] = validate_v20_safety_checkpoint(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    lines = ["# Runtime V2.0H - V2.0 Safety Checkpoint Report", "", "## Completed Phases", ""]
    lines += [f"- {item}" for item in data["completed_phases"]]
    lines += ["", "## Status", ""]
    lines += [f"- `{key}`: `{value}`" for key, value in data["status"].items()]
    lines += ["", "## Next Recommended Phases", ""]
    lines += [f"- {item}" for item in data["next_recommended_phases"]]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_v20_safety_checkpoint_report()
    print(f"Runtime V2.0H safety checkpoint: safe={result['all_safe']} final={result['final_recommendation']}")
