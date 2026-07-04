"""Local ARC IV knowledge evolution answers."""

from __future__ import annotations

from orchestration.runtime.arc_iv_knowledge_evolution import build_arc_iv_checkpoint


def is_arc_iv_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    return any(
        trigger in normalized
        for trigger in (
            "show evolution candidate",
            "should delta evolve",
            "why should this evolve",
            "explain why this should evolve",
            "show impact",
            "show rollback",
            "show version graph",
            "show approval chain",
            "show simulation",
            "what changes",
            "what conflicts",
            "who must approve",
        )
    )


def run_arc_iv_answer(query: str) -> dict[str, object]:
    data = build_arc_iv_checkpoint()
    normalized = " ".join(str(query).lower().split())
    if (
        "evolution candidate" in normalized
        or "should delta evolve" in normalized
        or "why should this evolve" in normalized
        or "why this should evolve" in normalized
    ):
        answer = "DELTA can stage a KnowledgeIntegrationCandidate for review. It is simulation-only and performs no live write."
        payload = {"integration_candidate": data["integration_candidate"]}
    elif "impact" in normalized or "what changes" in normalized:
        answer = "Impact is estimated as affected observations, entities, procedures, reasoning paths, and confidence delta."
        payload = {"impact_analysis": data["impact_analysis"], "knowledge_diff": data["knowledge_diff"]}
    elif "conflicts" in normalized:
        answer = "Conflicts are bundled for review and never auto-resolved."
        payload = {"contradiction_workflow": data["contradiction_workflow"]}
    elif "who must approve" in normalized or "approval chain" in normalized:
        answer = "Technical review, evidence review, overwatch, and optional owner review are recorded independently."
        payload = {"multi_reviewer_workflow": data["multi_reviewer_workflow"]}
    elif "rollback" in normalized:
        answer = "Every candidate produces a rollback plan with dependencies and restoration steps."
        payload = {"rollback_plan": data["rollback_plan"]}
    elif "version graph" in normalized:
        answer = "The version graph represents current and candidate versions, parents, branches, superseded nodes, and rollback targets."
        payload = {"version_graph": data["version_graph"]}
    else:
        answer = "The integration simulator shows graph, confidence, relationship, and concept changes without writing them."
        payload = {"integration_simulation": data["integration_simulation"]}
    return {
        "phase": "Runtime ARC IV",
        "query": query,
        "answer_text": answer,
        **payload,
        "safety": {
            "training_performed": False,
            "provider_authority_granted": False,
            "knowledge_mutation_performed": False,
            "integration_write_performed": False,
            "scheduler_started": False,
            "action_execution_performed": False,
            "hyb1_promoted": False,
        },
        "final_recommendation": "PROCEED_ARC_V_MEMORY_ACTIVATION_AND_RECALL_GOVERNANCE_DESIGN",
    }
