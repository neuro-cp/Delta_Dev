"""Local ARC VI executive cognition answers."""

from __future__ import annotations

from orchestration.runtime.arc_vi_executive_cognition import build_arc_vi_checkpoint, explain_executive_decision


def is_arc_vi_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    return any(
        trigger in normalized
        for trigger in (
            "create a goal",
            "break this goal",
            "why did you choose",
            "what evidence would you require",
            "what capabilities would be used",
            "what blocks execution",
            "why can't you execute",
            "show decision graph",
            "show constraints",
            "show blockers",
            "show review chain",
        )
    )


def run_arc_vi_answer(query: str) -> dict[str, object]:
    data = build_arc_vi_checkpoint("topic X")
    normalized = " ".join(str(query).lower().split())
    if "create a goal" in normalized:
        answer = "Created an ExecutiveGoal as a planning-only object. No execution was performed."
        payload = {"executive_goal": data["executive_goal"]}
    elif "break this goal" in normalized:
        answer = "The goal was decomposed into objectives, tasks, subtasks, and dependencies."
        payload = {"goal_decomposition": data["goal_decomposition"]}
    elif "capabilities" in normalized:
        answer = "The executive capability plan uses local reasoning, knowledge query, and review handlers; provider eligibility remains disabled."
        payload = {"capability_plan": data["capability_plan"]}
    elif "evidence" in normalized:
        answer = "Required evidence includes provenance-bearing substrate objects and evidence chains sufficient to bound confidence."
        payload = {"resource_plan": data["resource_plan"]}
    elif "blocks" in normalized or "can't you execute" in normalized:
        answer = explain_executive_decision(query, data)
        payload = {"constraint_engine": data["constraint_engine"]}
    elif "decision graph" in normalized:
        answer = "The executive decision graph is transient and represents goal, task, constraint, risk, review, and approval nodes."
        payload = {"executive_decision_graph": data["executive_decision_graph"]}
    elif "constraints" in normalized or "blockers" in normalized:
        answer = "Constraints identify policy, safety, resource, knowledge, confidence, time, and review requirements."
        payload = {"constraint_engine": data["constraint_engine"]}
    elif "review chain" in normalized:
        answer = "The executive review chain requests review and does not bypass safety."
        payload = {"escalation_framework": data["escalation_framework"]}
    else:
        answer = explain_executive_decision(query, data)
        payload = {"executive_reflection": data["executive_reflection"]}
    return {
        "phase": "Runtime ARC VI",
        "query": query,
        "answer_text": answer,
        **payload,
        "safety": {
            "training_performed": False,
            "provider_authority_granted": False,
            "autonomous_execution_performed": False,
            "scheduler_started": False,
            "action_execution_performed": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
            "hidden_write_performed": False,
            "hyb1_promoted": False,
        },
        "final_recommendation": "PROCEED_ARC_VII_EXECUTION_AUTHORITY_AND_ACTION_SANDBOX_DESIGN",
    }
