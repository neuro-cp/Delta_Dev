"""Runtime V2.9 current-state knowledge inventory.

This inventory describes DELTA's repo-local runtime state. It is deterministic
and read-only: no provider calls, memory writes, recall mutation, action
execution, scheduler activation, training, or HYB1 promotion.
"""

from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v29a_current_state_knowledge_inventory.md")
REPORT_JSON = Path("reports/runtime_v29a_current_state_knowledge_inventory.json")


def safety_invariants() -> dict[str, bool]:
    return {
        "model_b_default_changed": False,
        "hyb1_promoted": False,
        "hyb1_enabled_by_default": False,
        "training_performed": False,
        "fine_tuning_performed": False,
        "model_weights_updated": False,
        "model_artifact_created": False,
        "provider_call_performed": False,
        "provider_authority_granted": False,
        "action_execution_performed": False,
        "scheduler_started": False,
        "background_worker_started": False,
        "autonomous_memory_write_performed": False,
        "canonical_memory_write_performed": False,
        "recall_mutated": False,
        "authoritative_recall_enabled": False,
        "secret_printed": False,
    }


def build_current_state_inventory() -> dict[str, object]:
    return {
        "phase": "Runtime V2.9",
        "current_runtime_state": "V2.8/V2.9 scaffolded local validation state",
        "current_default": "Model B",
        "hyb1_status": "dormant_env_gated_shadow_only",
        "training_status": "disabled",
        "memory_status": "candidate_context_and_review_scaffolds_only_no_autonomous_writes",
        "recall_status": "candidate_context_only_not_authoritative_no_mutation",
        "provider_status": "disabled_unless_future_explicit_gate_provider_outputs_advisory_only",
        "scheduler_status": "disabled_no_background_workers_no_os_tasks",
        "action_execution_status": "disabled_dry_run_design_only",
        "active_local_capabilities": [
            "manual local console questions",
            "deterministic current-state self-description",
            "repo-local report and scaffold inspection",
            "candidate-context recall when explicitly requested",
            "static review console and dashboard artifacts",
            "safety status and provenance reporting",
            "deterministic validation/hardening reports",
        ],
        "disabled_capabilities": [
            "training and fine-tuning",
            "model weight updates",
            "model artifact creation",
            "provider calls and provider authority",
            "tool calls and action execution",
            "autonomous memory writes",
            "canonical memory writes",
            "authoritative recall",
            "recall mutation",
            "HYB1 default activation or promotion",
            "scheduler/background worker activation",
        ],
        "phase_summaries": {
            "V2.4": "localhost full review console UX and controlled memory/recall/provider/evaluator UX trials",
            "V2.5": "training readiness audit, feature activation readiness matrix, controlled export/shadow/scheduler gates",
            "V2.6": "dataset review UI, redaction trial, training job plan, artifact registry, feature gate console",
            "V2.7": "feature activation dry-run, UX polish, HYB1 dashboard, evaluator dashboard, full local demo, handoff",
            "V2.8": "pipeline validation, failure injection, stress test, observability, architecture audit, documentation consolidation",
            "V2.9": "current-state self-description and natural local interaction",
        },
        "known_blockers": [
            "No approved training execution path.",
            "No authoritative recall path.",
            "No HYB1 default promotion path.",
            "No live scheduler activation path.",
            "Natural interaction was previously behind the runtime state; V2.9 addresses that local interface gap.",
        ],
        "recommended_next_phase": "PROCEED_MANUAL_LOCAL_DEMO_AND_SELECTED_CLEANUP_REVIEW",
        "provenance": [
            "docs/ARCHITECTURE.md",
            "docs/INVARIANTS.md",
            "docs/ROADMAP.md",
            "docs/UPDATE.md",
            "reports/runtime_v25a_v27f_extended_overage_marathon_summary.md",
            "reports/runtime_v28_master_validation.md",
        ],
        "safety_invariants": safety_invariants(),
    }


def validate_current_state_inventory_safe(data: dict[str, object]) -> bool:
    return (
        data["phase"] == "Runtime V2.9"
        and data["current_default"] == "Model B"
        and data["hyb1_status"] == "dormant_env_gated_shadow_only"
        and all(value is False for value in data["safety_invariants"].values())
    )


def write_current_state_inventory_report() -> dict[str, object]:
    data = build_current_state_inventory()
    if not validate_current_state_inventory_safe(data):
        raise RuntimeError("Unsafe V2.9 inventory state")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(render_inventory_report(data), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def render_inventory_report(data: dict[str, object]) -> str:
    active = "\n".join(f"- {item}" for item in data["active_local_capabilities"])
    disabled = "\n".join(f"- {item}" for item in data["disabled_capabilities"])
    blockers = "\n".join(f"- {item}" for item in data["known_blockers"])
    return f"""# Runtime V2.9A Current-State Knowledge Inventory

Current runtime state: {data['current_runtime_state']}

Current default: {data['current_default']}

HYB1: {data['hyb1_status']}

## Active Local Capabilities

{active}

## Disabled Capabilities

{disabled}

## Known Blockers

{blockers}

Recommended next phase: `{data['recommended_next_phase']}`
"""


if __name__ == "__main__":
    print(write_current_state_inventory_report()["recommended_next_phase"])
