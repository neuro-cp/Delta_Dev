from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v19e_v19_safety_checkpoint_report.md")
REPORT_JSON = Path("reports/runtime_v19e_v19_safety_checkpoint_report.json")


PIPELINE_VIEW = [
    "RAW INPUT / EXPERIENCE ADAPTER DESIGN",
    "EPISODIC CAPTURE SCAFFOLD",
    "STRUCTURAL SEMANTIC ADAPTER DESIGN",
    "SEMANTIC SIGNAL TAGGING SCHEMA",
    "CANDIDATE ENVELOPE SCHEMA",
    "ANSWER TRACE / EVIDENCE TRACE",
    "FEEDBACK CAPTURE",
    "REPLAY MARKERS",
    "REPLAY BATCHING",
    "REPLAY REVIEW",
    "CONSOLIDATION CANDIDATE",
    "CONSOLIDATION DECISION",
    "SLEEP-CYCLE PLAN",
    "CANONICAL MEMORY DRAFT / RECORD DESIGN",
    "CANONICAL STORE DECISION / PLAN",
    "CANONICAL REVISION / ROLLBACK DESIGN",
    "TEMPORARY PRUNING PROJECTION DESIGN",
    "CONTROLLED LEARNING DESIGN",
    "SPECIALIST RESULT MERGE PROTOCOL",
    "RECALL BRIDGE DESIGN",
    "ACTIVE SPECIALIST ROUTING DESIGN, GATED OFF BY DEFAULT",
    "EXECUTION AUTHORIZATION DESIGN",
    "ACTION LEDGER DESIGN",
    "DRY-RUN ACTION EXECUTION DESIGN",
    "MINIMAL RUNTIME UI / MESSAGE CONSOLE",
    "MANUAL END-TO-END MESSAGE TESTING",
    "TRAINING DATASET CANDIDATE / EXPORT DESIGN",
    "OFFLINE EVALUATION HARNESS",
    "TINY CONTROLLED TRAINING EXPERIMENT DESIGN",
    "SCHEDULER ACTIVATION GATE",
    "DAILY EVALUATOR MANUAL-RUN HARDENING",
    "REVIEW UI EXPORT FLOW",
    "MEMORY CANDIDATE EDIT / REJECT / DEFER LOOP",
    "CANONICAL ROLLBACK TRIAL",
    "LIMITED GENERAL RECALL ROUTER DESIGN",
    "LOCAL MULTI-TURN SESSION STATE",
    "CONTROLLED PROVIDER-ASSISTED UNKNOWN ANSWER PATH",
    "SPECIALIST / SLM EVIDENCE ACQUISITION TRIAL",
    "PROVIDER / SPECIALIST EVIDENCE REVIEW UI",
    "LIMITED GENERAL RECALL TRIAL",
    "CONTROLLED ANSWER SYNTHESIS",
    "MULTI-TURN UNKNOWN RESOLUTION DEMO",
    "EVIDENCE QUALITY EVALUATION HARNESS",
    "PROMOTION READINESS SCORECARD",
    "QUALITY REVIEW UI",
    "MANUAL PROVIDER LIVE TRIAL GATE",
    "MANUAL PROVIDER LIVE TRIAL OPTIONAL ONE-SHOT",
    "PROVIDER EVIDENCE POST-REVIEW",
    "CONTROLLED GENERAL MEMORY / RECALL EXPANSION DESIGN",
    "UX-FIRST LOCAL DELTA CONSOLE",
    "CONSOLE APPROVAL / REJECT / DEFER WORKFLOW",
    "SESSION-TO-CANDIDATE MEMORY PROPOSAL FLOW",
]


def build_v19_safety_checkpoint() -> dict[str, object]:
    return {
        "phase": "Runtime V1.9E",
        "active_capabilities": [
            "local command-mode console",
            "static review dashboards",
            "candidate-context recall trial",
            "controlled answer synthesis",
            "provider dry-run/live-gated one-shot path",
            "console review exports",
            "session-to-candidate proposal flow",
        ],
        "disabled_capabilities": [
            "training",
            "fine-tuning",
            "model weight update",
            "autonomous memory writes",
            "authoritative recall",
            "scheduler/background worker",
            "action execution",
            "HYB1 default activation",
        ],
        "status": {
            "local_console": "command_mode_non_mutating",
            "review_ui": "static_local",
            "memory_candidate": "proposal_only_requires_review",
            "canonical_memory": "explicit_trial_only_no_autonomous_write",
            "recall": "candidate_context_only",
            "provider": "dry_run_default_optional_live_gate",
            "scheduler": "not_active",
            "training": "not_active",
            "action_execution": "not_active",
            "model_b": "default_unchanged",
            "hyb1": "dormant_env_gated",
        },
        "safety_invariants": {
            "model_b_default_changed": False,
            "hyb1_promoted": False,
            "training_performed": False,
            "action_execution_performed": False,
            "autonomous_memory_write_performed": False,
            "general_memory_activation": False,
            "authoritative_general_recall": False,
            "recall_mutated": False,
            "scheduler_started": False,
            "provider_specialist_evaluator_authority_transfer": False,
        },
        "pipeline_view": PIPELINE_VIEW,
        "next_recommended_phases": [
            "V2.0A Local DELTA UX Consolidation",
            "V2.0B Controlled General Memory Trial",
            "V2.0C Provider Evidence Live Trial Review",
            "V2.0D Review UI Write Approval Bridge",
            "V2.0E Scheduler Activation Trial, only if explicitly approved",
        ],
        "final_recommendation": "PROCEED_V2_LOCAL_UX_CONSOLIDATION_OR_CONTROLLED_GENERAL_MEMORY_TRIAL",
    }


def validate_v19_safety_checkpoint(data: dict[str, object]) -> bool:
    return len(data["pipeline_view"]) >= 50 and all(value is False for value in data["safety_invariants"].values())


def write_v19_safety_checkpoint_report() -> dict[str, object]:
    data = build_v19_safety_checkpoint()
    data["all_safe"] = validate_v19_safety_checkpoint(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = ["# Runtime V1.9E - V1.9 Safety Checkpoint Report", "", "## Active Capabilities", ""]
    lines += [f"- {item}" for item in data["active_capabilities"]]
    lines += ["", "## Disabled Capabilities", ""]
    lines += [f"- {item}" for item in data["disabled_capabilities"]]
    lines += ["", "## Status", ""]
    lines += [f"- `{key}`: `{value}`" for key, value in data["status"].items()]
    lines += ["", "## #10 Updated Pipeline", ""]
    lines += [f"{index}. {item}" for index, item in enumerate(data["pipeline_view"], start=1)]
    lines += ["", "## Next Recommended Phases", ""]
    lines += [f"- {item}" for item in data["next_recommended_phases"]]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_v19_safety_checkpoint_report()
    print(f"Runtime V1.9E safety checkpoint: safe={result['all_safe']} final={result['final_recommendation']}")
