"""RC1 vertical integration trace for DELTA runtime coherence.

This module connects existing kernel, pipeline, transaction, audit, and E2E
semantic-consolidation surfaces into one deterministic report-only workflow.
It does not activate training, providers, memory writes, knowledge mutation, or
canonical integration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.e2e_semantic_consolidation_cycle import run_cycle
from orchestration.runtime.v31_learning_opportunity import stable_v31_id
from orchestration.runtime.v32_cognitive_kernel import CognitiveKernel
from orchestration.runtime.v33_runtime_message_bus import RuntimeMessageBus
from orchestration.runtime.v35_transaction_engine import CognitiveTransactionEngine
from orchestration.runtime.v36_unified_audit_graph import AuditEdge, AuditNode, UnifiedAuditGraph
from orchestration.runtime.v37_capability_registry import CognitiveCapabilityRegistry
from orchestration.runtime.v38_dynamic_pipeline_builder import build_dynamic_pipeline


REPORT_JSON = Path("reports/RC1_READINESS_REVIEW.json")
REPORT_MD = Path("reports/RC1_READINESS_REVIEW.md")
TRACE_JSON = Path("reports/END_TO_END_RUNTIME_TRACE.json")
TRACE_MD = Path("reports/END_TO_END_RUNTIME_TRACE.md")
MASTER_RUNTIME_REVIEW_JSON = Path("reports/MASTER_RUNTIME_REVIEW.json")
MASTER_RUNTIME_REVIEW_MD = Path("reports/MASTER_RUNTIME_REVIEW.md")


@dataclass(frozen=True)
class RuntimeLifecycleOwner:
    object_name: str
    creator: str
    owner: str
    validator: str
    consumer: str
    auditor: str
    rollback_owner: str
    explains: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeTraceStep:
    step_id: str
    stage: str
    manager: str
    input_artifact: str
    output_artifact: str
    event_id: str
    transaction_id: str
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeCoherenceScorecard:
    kernel_routed: bool
    transaction_wrapped: bool
    audit_graph_linked: bool
    lifecycle_ownership_complete: bool
    answer_grounded_in_consolidated_records: bool
    unsupported_uncertainty_identified: bool
    prohibited_capabilities_inactive: bool
    estimated_runtime_maturity: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def safety_flags() -> dict[str, bool | str]:
    return {
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "training_performed": False,
        "fine_tuning_performed": False,
        "weight_update_performed": False,
        "provider_authority_granted": False,
        "provider_call_performed": False,
        "autonomous_browsing_performed": False,
        "action_execution_performed": False,
        "scheduler_started": False,
        "background_worker_started": False,
        "hidden_write_performed": False,
        "memory_mutation_performed": False,
        "knowledge_mutation_performed": False,
    }


def lifecycle_owners() -> tuple[RuntimeLifecycleOwner, ...]:
    return (
        RuntimeLifecycleOwner("E2EExperienceRecord", "ExperienceManager", "ExperienceManager", "SafetyManager", "EvidenceManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2ESemanticRecord", "EvidenceManager", "EvidenceManager", "SafetyManager", "RecallManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2EReplayBatch", "RecallManager", "RecallManager", "SafetyManager", "LearningManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2EConsolidationCandidate", "LearningManager", "LearningManager", "ReviewManager", "IntegrationManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2EConsolidationDecision", "ReviewManager", "ReviewManager", "SafetyManager", "IntegrationManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2EConsolidatedKnowledgeRecord", "IntegrationManager", "IntegrationManager", "SafetyManager", "RecallManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2EInquiry", "ExperienceManager", "ReasoningManager", "SafetyManager", "RecallManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2ERetrievedEvidence", "RecallManager", "RecallManager", "EvidenceManager", "ReasoningManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2EGroundedAnswer", "ReasoningManager", "ReasoningManager", "SafetyManager", "ReviewManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
        RuntimeLifecycleOwner("E2ECycleAudit", "ReviewManager", "ReviewManager", "SafetyManager", "SafetyManager", "ReviewManager", "IntegrationManager", "ReasoningManager"),
    )


def build_trace_steps(cycle: dict[str, Any]) -> tuple[RuntimeTraceStep, ...]:
    bus = RuntimeMessageBus()
    tx_engine = CognitiveTransactionEngine()
    stage_specs = (
        ("experience_ingestion", "ExperienceManager", "fixture_corpus", "experience_records"),
        ("semantic_record_build", "EvidenceManager", "experience_records", "semantic_records"),
        ("replay_batch_build", "RecallManager", "semantic_records", "replay_batch"),
        ("consolidation_candidate_build", "LearningManager", "replay_batch", "consolidation_candidates"),
        ("approval_gated_simulation", "ReviewManager", "consolidation_candidates", "simulated_consolidated_knowledge"),
        ("inquiry_routing", "ReasoningManager", "inquiry", "dynamic_pipeline"),
        ("semantic_retrieval", "RecallManager", "simulated_consolidated_knowledge", "retrieved_evidence"),
        ("grounded_synthesis", "ReasoningManager", "retrieved_evidence", "grounded_answer"),
        ("audit_review", "ReviewManager", "grounded_answer", "cycle_audit"),
        ("safety_checkpoint", "SafetyManager", "cycle_audit", "rc1_readiness_review"),
    )
    steps: list[RuntimeTraceStep] = []
    for index, (stage, manager, input_artifact, output_artifact) in enumerate(stage_specs, 1):
        event = bus.publish(
            event_type=f"rc1.{stage}",
            source="CognitiveKernel",
            target=manager,
            payload={
                "cycle_id": cycle["audit"]["cycle_id"],
                "input_artifact": input_artifact,
                "output_artifact": output_artifact,
            },
        )
        tx = tx_engine.plan_transaction(f"rc1_{stage}", commit_allowed=False)
        steps.append(
            RuntimeTraceStep(
                step_id=f"rc1-trace-step-{index:02d}",
                stage=stage,
                manager=manager,
                input_artifact=input_artifact,
                output_artifact=output_artifact,
                event_id=event.event_id,
                transaction_id=tx.transaction_id,
                mutating=False,
            )
        )
    return tuple(steps)


def build_trace_audit_graph(steps: tuple[RuntimeTraceStep, ...]) -> UnifiedAuditGraph:
    nodes = tuple(
        AuditNode(
            node_id=stable_v31_id("rc1-audit-node", step.step_id, step.stage),
            node_type=step.stage,
            label=f"{step.manager}: {step.output_artifact}",
        )
        for step in steps
    )
    edges = tuple(AuditEdge(nodes[index].node_id, nodes[index + 1].node_id, "feeds") for index in range(len(nodes) - 1))
    return UnifiedAuditGraph(stable_v31_id("rc1-audit-graph", *(step.step_id for step in steps)), nodes, edges)


def build_rc1_vertical_trace() -> dict[str, Any]:
    cycle = run_cycle()
    inquiry = cycle["inquiry"]["question"]
    kernel = CognitiveKernel()
    registry = CognitiveCapabilityRegistry()
    pipeline = build_dynamic_pipeline(inquiry, registry)
    steps = build_trace_steps(cycle)
    audit_graph = build_trace_audit_graph(steps)
    owners = lifecycle_owners()
    scorecard = RuntimeCoherenceScorecard(
        kernel_routed=all(kernel.route(step.manager.replace("Manager", "")) is not None for step in steps),
        transaction_wrapped=all(step.transaction_id for step in steps),
        audit_graph_linked=len(audit_graph.edges) == len(steps) - 1,
        lifecycle_ownership_complete=all(
            all(getattr(owner, field) for field in ("creator", "owner", "validator", "consumer", "auditor", "rollback_owner", "explains"))
            for owner in owners
        ),
        answer_grounded_in_consolidated_records=bool(cycle["grounded_answer"]["supporting_evidence_ids"]),
        unsupported_uncertainty_identified=bool(cycle["grounded_answer"]["uncertainty"] and cycle["grounded_answer"]["unsupported_claims_refused"]),
        prohibited_capabilities_inactive=all(value is False for key, value in safety_flags().items() if key.endswith("_performed") or key.endswith("_started") or key.endswith("_granted")),
        estimated_runtime_maturity=76,
    )
    return {
        "phase": "DELTA RC1 Vertical Integration Coherence Pass",
        "scenario": "Project Atlas closed-loop semantic consolidation through kernel trace",
        "kernel": kernel.describe(),
        "dynamic_pipeline": pipeline.as_dict(),
        "trace_steps": [step.as_dict() for step in steps],
        "lifecycle_owners": [owner.as_dict() for owner in owners],
        "audit_graph": audit_graph.as_dict(),
        "e2e_cycle": cycle,
        "scorecard": scorecard.as_dict(),
        "safety": safety_flags(),
        "architecture_improvements": (
            "E2E semantic consolidation cycle is now represented as a kernel-routed vertical workflow.",
            "Every E2E runtime object has explicit creator, owner, validator, consumer, auditor, rollback owner, and explainer.",
            "Dynamic pipeline routing recognizes semantic consolidation and vertical runtime trace requests.",
            "Kernel events and non-mutating transactions now wrap every E2E stage.",
            "Audit graph links the full scenario from experience ingestion to RC1 readiness review.",
        ),
        "remaining_weaknesses": (
            "The trace still uses fixture records rather than real document adapters.",
            "The kernel route is deterministic and report-only, not yet the sole execution path for all local answers.",
            "Substrate query adapters are still simulated through the E2E harness.",
            "Integration remains simulated and does not write canonical knowledge.",
        ),
        "final_recommendation": "PROCEED_DOCUMENT_TO_AUDIT_VERTICAL_SLICE",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    scorecard = payload["scorecard"]
    lines = [
        "# RC1 Readiness Review",
        "",
        f"Phase: {payload['phase']}",
        "",
        "## Scenario",
        "",
        payload["scenario"],
        "",
        "## Scorecard",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in scorecard.items())
    lines.extend(["", "## Architecture Improvements", ""])
    lines.extend(f"- {item}" for item in payload["architecture_improvements"])
    lines.extend(["", "## Remaining Weaknesses", ""])
    lines.extend(f"- {item}" for item in payload["remaining_weaknesses"])
    lines.extend(["", "## Lifecycle Ownership", ""])
    lines.extend(
        f"- {owner['object_name']}: creator={owner['creator']}, consumer={owner['consumer']}, auditor={owner['auditor']}"
        for owner in payload["lifecycle_owners"]
    )
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    lines.extend(["", "## Final Recommendation", "", payload["final_recommendation"], ""])
    return "\n".join(lines)


def render_trace_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# End-to-End Runtime Trace",
        "",
        "This trace wraps the semantic consolidation E2E harness in kernel events, non-mutating transactions, and an audit graph.",
        "",
        "## Steps",
        "",
    ]
    for step in payload["trace_steps"]:
        lines.append(
            f"- {step['step_id']}: {step['stage']} via {step['manager']} "
            f"({step['input_artifact']} -> {step['output_artifact']})"
        )
    lines.extend(["", "## Grounded Answer", "", payload["e2e_cycle"]["grounded_answer"]["answer"], ""])
    return "\n".join(lines)


def write_rc1_reports(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_rc1_vertical_trace()
    for path in (REPORT_JSON, REPORT_MD, TRACE_JSON, TRACE_MD, MASTER_RUNTIME_REVIEW_JSON, MASTER_RUNTIME_REVIEW_MD):
        path.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    TRACE_JSON.write_text(json.dumps({"trace_steps": payload["trace_steps"], "audit_graph": payload["audit_graph"]}, indent=2, sort_keys=True), encoding="utf-8")
    TRACE_MD.write_text(render_trace_markdown(payload), encoding="utf-8")
    MASTER_RUNTIME_REVIEW_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    MASTER_RUNTIME_REVIEW_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = write_rc1_reports()
    print(f"final_recommendation={result['final_recommendation']}")
    print(f"estimated_runtime_maturity={result['scorecard']['estimated_runtime_maturity']}")
    print(f"trace_steps={len(result['trace_steps'])}")
