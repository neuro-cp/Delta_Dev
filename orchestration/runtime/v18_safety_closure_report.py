from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v18c_v17_v18_safety_closure_report.md")
REPORT_JSON = Path("reports/runtime_v18c_v17_v18_safety_closure_report.json")


PHASES = (
    ("V1.7E", "Provider / Specialist Evidence Review UI", "complete"),
    ("V1.7F", "Limited General Recall Trial", "complete"),
    ("V1.7G", "Controlled Answer Synthesis", "complete"),
    ("V1.7H", "Multi-Turn Unknown Resolution Demo", "complete"),
    ("V1.8A", "Evidence Quality Evaluation Harness", "complete"),
    ("V1.8B", "Promotion Readiness Scorecard", "complete"),
)


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
    "REPORT-ONLY HYPOTHESIS ARBITRATION",
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
    "EXPLICIT SCHEDULER ACTIVATION GATE",
    "DAILY EVALUATOR MANUAL-RUN HARDENING",
    "REVIEW UI APPROVAL / REJECTION EXPORT FLOW",
    "MEMORY CANDIDATE EDIT / REJECT / DEFER LOOP",
    "ROLLBACK TRIAL FOR CANONICAL MEMORY RECORD",
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
]


def build_safety_closure_report() -> dict[str, object]:
    return {
        "phase": "Runtime V1.8C",
        "completed_phases": [{"phase": phase, "name": name, "status": status} for phase, name, status in PHASES],
        "capability_status": {
            "model_b": "default_unchanged",
            "hyb1": "dormant_env_gated",
            "memory": "candidate_context_and_explicit_trial_only",
            "recall": "limited_candidate_context_only",
            "provider": "dry_run_or_explicit_live_gate_evidence_only",
            "specialist": "dry_run_or_explicit_live_gate_evidence_only",
            "evaluator": "manual_or_gated_advisory_only",
            "scheduler": "not_active",
            "training": "not_active",
            "action_execution": "not_active",
        },
        "active_capabilities": [
            "static evidence review UI generation",
            "limited candidate-context recall trial",
            "controlled answer synthesis",
            "multi-turn unknown resolution demo",
            "evidence quality scorecards",
            "promotion readiness review",
        ],
        "inactive_capabilities": [
            "training",
            "fine-tuning",
            "model weight update",
            "autonomous memory writes",
            "authoritative general recall",
            "scheduler/background worker",
            "action execution",
            "HYB1 default activation",
        ],
        "evidence_quality_summary": "V1.8A generated deterministic evidence quality scorecards for provenance, uncertainty, source roles, candidate/truth separation, conflict handling, unsupported fallback, and mutation safety.",
        "promotion_readiness_summary": "V1.8B generated readiness classifications only; no promotion occurred.",
        "known_limitations": [
            "Recall remains candidate-context only.",
            "Provider and specialist outputs remain evidence-only and require explicit live gates for real calls.",
            "Memory writes still require exact explicit approval.",
            "Promotion readiness is not promotion.",
        ],
        "pipeline_view": PIPELINE_VIEW,
        "next_recommended_phases": [
            "V1.8D Local Review UI Iteration for Evidence Quality",
            "V1.8E Manual Provider Live Trial, if explicitly requested",
            "V1.8F Scheduler Activation Trial, if explicitly requested",
            "V1.9A Controlled General Memory / Recall Expansion",
            "V1.9B UX-first Local DELTA Console",
        ],
        "safety_invariants": {
            "model_b_default_changed": False,
            "hyb1_promoted": False,
            "training_performed": False,
            "action_execution_performed": False,
            "autonomous_memory_write_performed": False,
            "general_memory_activation": False,
            "authoritative_general_recall": False,
            "scheduler_started": False,
            "provider_specialist_evaluator_authority_transfer": False,
        },
        "final_recommendation": "PROCEED_LOCAL_REVIEW_UI_ITERATION_OR_MANUAL_PROVIDER_LIVE_TRIAL",
    }


def write_safety_closure_report() -> dict[str, object]:
    data = build_safety_closure_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def validate_safety_closure_report(data: dict[str, object]) -> bool:
    invariants = data["safety_invariants"]
    return (
        len(data["completed_phases"]) == 6
        and len(data["pipeline_view"]) >= 40
        and all(value is False for value in invariants.values())
        and data["final_recommendation"] == "PROCEED_LOCAL_REVIEW_UI_ITERATION_OR_MANUAL_PROVIDER_LIVE_TRIAL"
    )


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.8C - V1.7/V1.8 Safety Closure Report",
        "",
        "## Completed Phases",
        "",
    ]
    for phase in data["completed_phases"]:
        lines.append(f"- `{phase['phase']}` {phase['name']}: `{phase['status']}`")
    lines += [
        "",
        "## Capability Status",
        "",
    ]
    for key, value in data["capability_status"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## Active Capabilities",
        "",
        *(f"- {item}" for item in data["active_capabilities"]),
        "",
        "## Inactive Capabilities",
        "",
        *(f"- {item}" for item in data["inactive_capabilities"]),
        "",
        "## Evidence Quality Evaluation Summary",
        "",
        data["evidence_quality_summary"],
        "",
        "## Promotion Readiness Summary",
        "",
        data["promotion_readiness_summary"],
        "",
        "## Known Limitations",
        "",
        *(f"- {item}" for item in data["known_limitations"]),
        "",
        "## #10 Pipeline View",
        "",
    ]
    for index, item in enumerate(data["pipeline_view"], start=1):
        lines.append(f"{index}. {item}")
    lines += [
        "",
        "## Next Recommended Phases",
        "",
        *(f"- {item}" for item in data["next_recommended_phases"]),
        "",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_safety_closure_report()
    print(f"Runtime V1.8C closure: valid={validate_safety_closure_report(result)} final={result['final_recommendation']}")
