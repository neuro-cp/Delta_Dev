"""Runtime ARC I local kernel answers for manual smoke prompts."""

from __future__ import annotations

from orchestration.runtime.v34_cognitive_state import build_runtime_state_snapshot
from orchestration.runtime.v38_dynamic_pipeline_builder import build_dynamic_pipeline
from orchestration.runtime.v39_kernel_safety_checkpoint import build_kernel_safety_checkpoint


def is_kernel_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    return any(
        trigger in normalized
        for trigger in (
            "show runtime state",
            "explain kernel routing",
            "what would happen if this were approved",
            "explain your reasoning",
        )
    )


def run_kernel_answer(query: str) -> dict[str, object]:
    normalized = " ".join(str(query).lower().split())
    if "show runtime state" in normalized:
        state = build_runtime_state_snapshot(query).as_dict()
        answer = "RuntimeState is available as a single non-mutating snapshot. No memory, recall, provider, scheduler, training, or action state was mutated."
        payload = {"runtime_state": state}
    elif "explain kernel routing" in normalized:
        pipeline = build_dynamic_pipeline(query).as_dict()
        answer = "Kernel routing resolves requested capabilities through the capability registry and assembles a non-mutating dynamic pipeline."
        payload = {"dynamic_pipeline": pipeline}
    elif "what would happen if this were approved" in normalized:
        checkpoint = build_kernel_safety_checkpoint()
        answer = "Approval would create or advance gated review metadata only. Any future integration still requires transaction validation, overwatch/override gates, audit graph linkage, rollback handle, and a live write gate that remains disabled here."
        payload = {"transaction_lifecycle": checkpoint["transaction_lifecycle"], "audit_graph": checkpoint["audit_graph"]}
    else:
        pipeline = build_dynamic_pipeline(query).as_dict()
        answer = "Reasoning is coordinated through the kernel pipeline: route the request, select handlers, inspect evidence/provenance, check safety gates, and synthesize a local response without provider calls or mutation."
        payload = {"dynamic_pipeline": pipeline}
    return {
        "phase": "Runtime ARC I V3.9",
        "query": query,
        "answer_text": answer,
        **payload,
        "safety": {
            "training_performed": False,
            "provider_call_performed": False,
            "memory_mutation_performed": False,
            "recall_mutation_performed": False,
            "scheduler_started": False,
            "action_execution_performed": False,
            "hyb1_promoted": False,
            "model_b_default_changed": False,
        },
        "final_recommendation": "PROCEED_ARC_II_KNOWLEDGE_SUBSTRATE_DESIGN",
    }
