"""Runtime V3.1 local answers for controlled learning readiness questions."""

from __future__ import annotations

from orchestration.runtime.v31_gated_integration import build_gated_integration_report
from orchestration.runtime.v31_learning_explainability import explain_learning_proposal
from orchestration.runtime.v31_learning_opportunity import detect_learning_opportunities
from orchestration.runtime.v31_learning_proposal import build_learning_proposals


def is_v31_learning_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    triggers = (
        "what should delta learn",
        "corrected this preference",
        "approve this learning proposal",
        "what has delta learned",
        "learning proposal",
        "review/proposal state",
        "proposal state",
    )
    return any(trigger in normalized for trigger in triggers)


def run_v31_learning_answer(query: str) -> dict[str, object]:
    normalized = " ".join(str(query).lower().split())
    if "what has delta learned" in normalized:
        answer = "No durable learned knowledge exists from V3.1. DELTA can stage reviewable opportunities and gated integration events, but no live integration write, training, or memory mutation has occurred."
        opportunities = []
        proposals = []
        gated = None
    elif "approve this learning proposal" in normalized:
        proposals = [item.as_dict() for item in build_learning_proposals(query, review_status="admin_approved")]
        gated = build_gated_integration_report()
        answer = "A proposal may enter admin_approved state, which makes it eligible for gated integration. It is not integrated unless overwatch allows it or the owner override gate is explicit, and V3.1 still performs no live write."
        opportunities = []
    else:
        opportunities = [item.as_dict() for item in detect_learning_opportunities(query)]
        proposals = [item.as_dict() for item in build_learning_proposals(query, review_status="review")]
        gated = None
        if proposals:
            explanation = explain_learning_proposal(build_learning_proposals(query, review_status="review")[0])
            answer = f"Learning Opportunity detected. A review-only proposal was generated: {explanation['why_proposed']}. It remains blocked by {', '.join(explanation['why_blocked'])}."
        else:
            answer = "No specific learning opportunity was detected. No learning, memory write, or integration occurred."
    return {
        "phase": "Runtime V3.1",
        "query": query,
        "answer_text": answer,
        "learning_opportunities": opportunities,
        "learning_proposals": proposals,
        "gated_integration": gated,
        "safety": {
            "learning_performed": False,
            "training_performed": False,
            "integration_write_performed": False,
            "memory_mutation_performed": False,
            "provider_call_performed": False,
            "recall_mutation_performed": False,
            "scheduler_started": False,
            "action_execution_performed": False,
        },
        "final_recommendation": "PROCEED_CONTROLLED_LEARNING_REVIEW_WORKFLOW_OR_MANUAL_DEMO",
    }
