"""Runtime ARC I V3.9 kernel safety checkpoint and report generation."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v32_cognitive_kernel import CognitiveKernel
from orchestration.runtime.v33_runtime_message_bus import build_sample_event_flow
from orchestration.runtime.v34_cognitive_state import build_runtime_state_snapshot
from orchestration.runtime.v35_transaction_engine import build_transaction_lifecycle
from orchestration.runtime.v36_unified_audit_graph import build_sample_audit_graph
from orchestration.runtime.v37_capability_registry import CognitiveCapabilityRegistry
from orchestration.runtime.v38_dynamic_pipeline_builder import build_dynamic_pipeline


REPORT_JSON = Path("reports/runtime_v39_kernel_safety_checkpoint.json")
REPORT_MD = Path("reports/runtime_v39_kernel_safety_checkpoint.md")
CONTINUATION = Path("docs/continuation_runtime_arc_i.md")


def build_kernel_safety_checkpoint() -> dict[str, object]:
    kernel = CognitiveKernel()
    registry = CognitiveCapabilityRegistry()
    return {
        "phase": "Runtime V3.9",
        "arc": "ARC I cognitive kernel runtime orchestration",
        "kernel": kernel.describe(),
        "event_flow": build_sample_event_flow(),
        "runtime_state": build_runtime_state_snapshot("What should DELTA learn?").as_dict(),
        "transaction_lifecycle": build_transaction_lifecycle(),
        "audit_graph": build_sample_audit_graph().as_dict(),
        "capability_registry": registry.as_dict(),
        "dynamic_pipeline": build_dynamic_pipeline("What should DELTA learn and explain routing?", registry).as_dict(),
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated_shadow_only",
        "provider_authority": "disabled",
        "training": "disabled",
        "integration_writes": "disabled",
        "scheduler": "disabled",
        "actions": "disabled",
        "hidden_memory": "disabled",
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_ARC_II_KNOWLEDGE_SUBSTRATE_DESIGN",
    }


def write_kernel_safety_checkpoint() -> dict[str, object]:
    data = build_kernel_safety_checkpoint()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_kernel_report(data), encoding="utf-8")
    CONTINUATION.write_text(
        "# DELTA Runtime ARC I Continuation\n\n"
        "ARC I V3.2-V3.9 is complete. DELTA now has an orchestration-only Cognitive Kernel, event bus, unified runtime state snapshot, transaction lifecycle scaffold, unified audit graph, capability registry, dynamic pipeline builder, and kernel safety checkpoint.\n\n"
        "No training, provider authority, action execution, scheduler activation, hidden writes, autonomous memory, recall mutation, HYB1 promotion, or Model B default change occurred.\n\n"
        "Next recommendation: `PROCEED_ARC_II_KNOWLEDGE_SUBSTRATE_DESIGN`.\n",
        encoding="utf-8",
    )
    return data


def render_kernel_report(data: dict[str, object]) -> str:
    managers = "\n".join(f"- {item['name']}: {item['responsibility']}" for item in data["kernel"]["managers"])
    registry = "\n".join(f"- {item['capability']} -> {item['handler']} (active={item['active']})" for item in data["capability_registry"]["records"])
    return f"""# Runtime V3.9 Kernel Safety Checkpoint

ARC: {data['arc']}

## Kernel Components

{managers}

## Kernel Event Flow

Experience -> Kernel Event -> Dispatcher -> Manager -> Review/Audit event.

## Kernel Registry

{registry}

## Runtime State Diagram

ExperienceState -> MemoryState -> EvidenceState -> ReasoningState -> ReviewState -> LearningState

## Transaction Lifecycle

Begin -> Validate -> Execute -> Review -> Commit -> Rollback

## Audit Graph Diagram

Experience -> Proposal -> Review -> Integration Candidate -> Rollback -> Reasoning

## Future Knowledge Substrate Design

ARC II should design the Knowledge Substrate behind the kernel. It should not begin by enabling training, autonomous memory, provider authority, schedulers, or action execution.

Final recommendation: `{data['final_recommendation']}`
"""


if __name__ == "__main__":
    print(write_kernel_safety_checkpoint()["final_recommendation"])
