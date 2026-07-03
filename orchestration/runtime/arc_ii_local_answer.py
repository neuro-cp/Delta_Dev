"""Local ARC II knowledge substrate answers."""

from __future__ import annotations

from orchestration.runtime.arc_ii_knowledge_substrate import build_arc_ii_checkpoint


def is_arc_ii_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    return any(
        trigger in normalized
        for trigger in (
            "show entity registry",
            "show concept registry",
            "show observation registry",
            "show evidence registry",
            "show knowledge graph",
            "show provenance tree",
            "explain knowledge transaction",
            "observation is not truth",
            "evidence is advisory",
        )
    )


def run_arc_ii_answer(query: str) -> dict[str, object]:
    data = build_arc_ii_checkpoint()
    normalized = " ".join(str(query).lower().split())
    if "entity registry" in normalized:
        answer = "Entity Registry is available as a kernel-accessible, reviewable substrate registry. It is not live persistence."
        payload = {"registry": data["registries"]["entity_registry"]}
    elif "concept registry" in normalized:
        answer = "Concept Registry contains reviewable concepts, claims, hypotheses, procedures, rules, and events. No autonomous abstraction occurs."
        payload = {"registry": data["registries"]["concept_registry"]}
    elif "observation registry" in normalized:
        answer = "Observation Registry contains atomic observations. Observation is not truth and always references evidence."
        payload = {"registry": data["registries"]["observation_registry"]}
    elif "evidence registry" in normalized:
        answer = "Evidence Registry contains advisory evidence objects with source, provenance, confidence, and support references. No provider authority is granted."
        payload = {"registry": data["registries"]["evidence_registry"]}
    elif "knowledge graph" in normalized:
        answer = "Knowledge Graph contains deterministic object nodes and auditable relationship edges. It is graph-only and non-mutating."
        payload = {"knowledge_graph": data["knowledge_graph"]}
    elif "provenance tree" in normalized:
        answer = "Provenance Tree shows where a knowledge object came from, including confidence, review state, and support chain."
        payload = {"provenance_tree": data["provenance_tree"]}
    elif "knowledge transaction" in normalized:
        answer = "Knowledge Transaction records draft, review, approved, future integrated, and rolled-back stages. ARC II ends before integrated live writes."
        payload = {"knowledge_transaction": data["knowledge_transaction"]}
    elif "observation is not truth" in normalized:
        answer = "An observation is a recorded claim about experience, not truth. It must reference evidence and remain reviewable."
        payload = {"observations": data["semantic_queries"]["observations"]}
    else:
        answer = "Evidence is advisory because it supports review and reasoning but does not become provider authority, memory truth, or canonical knowledge by itself."
        payload = {"supporting_evidence": data["semantic_queries"]["supporting_evidence"]}
    return {
        "phase": "Runtime ARC II",
        "query": query,
        "answer_text": answer,
        **payload,
        "safety": {
            "training_performed": False,
            "provider_authority_granted": False,
            "memory_mutation_performed": False,
            "recall_mutation_performed": False,
            "scheduler_started": False,
            "action_execution_performed": False,
            "live_knowledge_integration": False,
            "authoritative_substrate": False,
        },
        "final_recommendation": "PROCEED_ARC_III_REASONING_LAYER_DESIGN",
    }
