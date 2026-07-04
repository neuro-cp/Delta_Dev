"""DELTA ARC VI executive cognition and goal-oriented orchestration.

The executive layer coordinates cognition. It does not reason, execute, train,
start schedulers, mutate memory/knowledge, call providers, or bypass safety.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id
from orchestration.runtime.v37_capability_registry import CognitiveCapabilityRegistry


REPORT_MD = Path("reports/runtime_arc_vi_safety_checkpoint.md")
REPORT_JSON = Path("reports/runtime_arc_vi_safety_checkpoint.json")
DASHBOARD_HTML = Path("ui/delta_arc_vi_executive_dashboard.html")
CONTINUATION = Path("docs/continuation_runtime_arc_vi.md")


@dataclass(frozen=True)
class ExecutiveGoal:
    goal_id: str
    title: str
    description: str
    priority: int
    owner: str
    requested_by: str
    deadline: str
    constraints: tuple[str, ...]
    status: str
    risk: str
    dependencies: tuple[str, ...]
    execution_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutiveTask:
    task_id: str
    objective: str
    task: str
    subtasks: tuple[str, ...]
    dependencies: tuple[str, ...]
    status: str = "planned_only"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutiveDecisionNode:
    node_id: str
    node_type: str
    label: str
    risk: str = "low"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutiveDecisionGraph:
    graph_id: str
    nodes: tuple[ExecutiveDecisionNode, ...]
    edges: tuple[dict[str, str], ...]
    transient: bool = True

    def as_dict(self) -> dict[str, object]:
        return {"graph_id": self.graph_id, "nodes": [n.as_dict() for n in self.nodes], "edges": list(self.edges), "transient": self.transient}


@dataclass(frozen=True)
class ExecutiveTransaction:
    transaction_id: str
    stages: tuple[str, ...]
    completed_planning_only: bool
    persistent_execution: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def create_executive_goal(topic: str = "topic X") -> ExecutiveGoal:
    return ExecutiveGoal(
        goal_id=stable_v31_id("executive-goal", topic),
        title=f"Understand {topic}",
        description=f"Create a safe, evidence-aware plan to understand {topic}.",
        priority=5,
        owner="admin",
        requested_by="user",
        deadline="none",
        constraints=("no_provider_authority", "no_execution", "no_memory_mutation", "review_required"),
        status="planning_only",
        risk="bounded_if_not_executed",
        dependencies=("knowledge_query", "reasoning_trace", "review_gate"),
    )


def decompose_goal(goal: ExecutiveGoal) -> tuple[ExecutiveTask, ...]:
    objectives = (
        ("scope_topic", "Define the topic boundary", ("identify terms", "list unknowns")),
        ("gather_evidence", "Identify required evidence", ("query substrate", "list provenance")),
        ("reason_over_evidence", "Plan reasoning strategy", ("build reasoning context", "reflect on assumptions")),
        ("review_result", "Prepare review package", ("summarize blockers", "request admin review")),
    )
    tasks = []
    previous = ""
    for objective, task, subtasks in objectives:
        task_id = stable_v31_id("executive-task", goal.goal_id, objective)
        tasks.append(ExecutiveTask(task_id, objective, task, subtasks, (previous,) if previous else ()))
        previous = task_id
    return tuple(tasks)


def plan_capabilities(tasks: tuple[ExecutiveTask, ...]) -> dict[str, object]:
    registry = CognitiveCapabilityRegistry()
    capabilities = {
        "reasoning_required": True,
        "knowledge_required": True,
        "review_required": True,
        "learning_required": False,
        "provider_eligibility": "disabled_without_future_explicit_gate",
        "handlers": {
            "reasoning": registry.resolve("pipeline_explanation").handler,
            "knowledge": "KnowledgeSubstrate",
            "review": registry.resolve("learning_review").handler,
        },
        "task_count": len(tasks),
    }
    return capabilities


def plan_resources(tasks: tuple[ExecutiveTask, ...]) -> dict[str, object]:
    return {
        "reasoning_complexity": "moderate",
        "knowledge_scope": "bounded_substrate_query",
        "expected_evidence": "provenance-bearing substrate objects",
        "estimated_review_load": len(tasks),
        "expected_confidence": "bounded_by_evidence_quality",
    }


def build_deliberation_plan() -> dict[str, object]:
    return {
        "strategy": ("simple_lookup", "graph_traversal", "multi_hop_reasoning", "hypothesis_generation", "reflection", "review"),
        "planner_only": True,
    }


def build_decision_graph(goal: ExecutiveGoal, tasks: tuple[ExecutiveTask, ...]) -> ExecutiveDecisionGraph:
    nodes = [ExecutiveDecisionNode(goal.goal_id, "goal", goal.title, goal.risk)]
    nodes.extend(ExecutiveDecisionNode(task.task_id, "task", task.task, "low") for task in tasks)
    nodes.append(ExecutiveDecisionNode(stable_v31_id("executive-risk", goal.goal_id), "risk", "execution blocked without approval", "medium"))
    edges = []
    for task in tasks:
        edges.append({"source": goal.goal_id, "target": task.task_id, "relation": "decomposes_to"})
    return ExecutiveDecisionGraph(stable_v31_id("executive-decision-graph", goal.goal_id), tuple(nodes), tuple(edges))


def evaluate_constraints(goal: ExecutiveGoal) -> dict[str, object]:
    blockers = ["provider_authority_disabled", "autonomous_execution_disabled", "scheduler_disabled", "memory_mutation_disabled"]
    return {
        "policy": "satisfied_if_planning_only",
        "safety": "blocked_for_execution",
        "resource": "bounded",
        "knowledge": "requires_substrate_query",
        "confidence": "requires_evidence_chain",
        "time": "no_deadline",
        "review_requirements": ("admin_review", "safety_review"),
        "blockers": blockers,
    }


def decide_escalation(constraints: dict[str, object]) -> dict[str, object]:
    return {
        "decision": "request_review",
        "options": ("continue_planning", "pause", "request_review", "request_more_evidence", "request_owner_approval", "request_overwatch"),
        "automatic_bypass": False,
        "blockers": constraints["blockers"],
    }


def simulate_multi_goal_schedule(goals: tuple[ExecutiveGoal, ...]) -> dict[str, object]:
    ordered = sorted(goals, key=lambda goal: goal.priority, reverse=True)
    return {
        "ordered_goals": [goal.goal_id for goal in ordered],
        "resource_conflicts": [],
        "os_scheduler_started": False,
        "background_workers_started": False,
        "simulation_only": True,
    }


def reflect_on_plan(tasks: tuple[ExecutiveTask, ...], constraints: dict[str, object]) -> dict[str, object]:
    return {
        "better_strategy": "keep planning bounded and evidence-first",
        "less_risky_strategy": "defer execution until explicit approval path exists",
        "lower_cost_strategy": "use local substrate before providers",
        "missing_evidence": ("topic-specific evidence",),
        "alternative_decomposition": "split review from reasoning if risk increases",
        "blockers": constraints["blockers"],
    }


def build_executive_audit(goal: ExecutiveGoal, tasks: tuple[ExecutiveTask, ...], graph: ExecutiveDecisionGraph, reflection: dict[str, object]) -> dict[str, object]:
    return {
        "goal_creation": goal.as_dict(),
        "planning": [task.as_dict() for task in tasks],
        "resource_analysis": plan_resources(tasks),
        "decision_graph": graph.as_dict(),
        "reflection": reflection,
        "constraint_checks": evaluate_constraints(goal),
        "execution_performed": False,
    }


def explain_executive_decision(question: str, checkpoint: dict[str, object]) -> str:
    normalized = question.lower()
    if "why did you choose" in normalized:
        return "The plan was chosen because it preserves evidence-first reasoning, review, and safety validation before any execution."
    if "why is this blocked" in normalized or "what blocks" in normalized:
        return "Execution is blocked because provider authority, autonomous execution, scheduler activation, and memory mutation remain disabled."
    if "review requested" in normalized:
        return "Review is requested because executive decisions are planning artifacts and cannot bypass safety gates."
    if "more evidence" in normalized or "evidence would" in normalized:
        return "More evidence is needed when substrate support is insufficient to bound confidence and risk."
    if "can't you execute" in normalized or "cannot execute" in normalized:
        return "ARC VI can plan and audit, but action execution remains disabled and requires a future explicit execution authority path."
    return "The executive layer decomposes goals, selects capabilities, estimates resources, checks constraints, and requests review without executing."


def build_executive_transaction(goal: ExecutiveGoal) -> ExecutiveTransaction:
    return ExecutiveTransaction(
        transaction_id=stable_v31_id("executive-transaction", goal.goal_id),
        stages=("begin", "plan", "validate", "review", "approved", "completed_planning_only", "destroy"),
        completed_planning_only=True,
        persistent_execution=False,
    )


def build_arc_vi_checkpoint(topic: str = "topic X") -> dict[str, object]:
    goal = create_executive_goal(topic)
    tasks = decompose_goal(goal)
    capabilities = plan_capabilities(tasks)
    resources = plan_resources(tasks)
    deliberation = build_deliberation_plan()
    graph = build_decision_graph(goal, tasks)
    constraints = evaluate_constraints(goal)
    escalation = decide_escalation(constraints)
    schedule = simulate_multi_goal_schedule((goal,))
    reflection = reflect_on_plan(tasks, constraints)
    audit = build_executive_audit(goal, tasks, graph, reflection)
    transaction = build_executive_transaction(goal)
    return {
        "phase": "Runtime ARC VI V8.15",
        "executive_goal": goal.as_dict(),
        "goal_decomposition": [task.as_dict() for task in tasks],
        "capability_plan": capabilities,
        "resource_plan": resources,
        "deliberation_plan": deliberation,
        "executive_decision_graph": graph.as_dict(),
        "constraint_engine": constraints,
        "escalation_framework": escalation,
        "multi_goal_scheduler_simulation": schedule,
        "executive_reflection": reflection,
        "executive_audit": audit,
        "executive_transaction": transaction.as_dict(),
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "training_performed": False,
        "provider_authority_granted": False,
        "autonomous_execution_performed": False,
        "scheduler_started": False,
        "action_execution_performed": False,
        "memory_mutation_performed": False,
        "knowledge_mutation_performed": False,
        "hidden_write_performed": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_ARC_VII_EXECUTION_AUTHORITY_AND_ACTION_SANDBOX_DESIGN",
    }


def write_arc_vi_reports() -> dict[str, object]:
    data = build_arc_vi_checkpoint()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_arc_vi_report(data), encoding="utf-8")
    DASHBOARD_HTML.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_HTML.write_text(render_executive_dashboard(data), encoding="utf-8")
    CONTINUATION.write_text(
        "# DELTA ARC VI Continuation\n\n"
        "ARC VI is complete as a non-executing executive cognition layer. It creates executive goals, decomposes tasks, plans capabilities/resources/deliberation, builds transient decision graphs, checks constraints, simulates multi-goal ordering, reflects, audits, explains decisions, and records planning-only executive transactions.\n\n"
        "No autonomous execution, scheduler activation, provider authority, memory mutation, knowledge mutation, training, HYB1 promotion, or hidden write occurred.\n\n"
        "Next recommendation: `PROCEED_ARC_VII_EXECUTION_AUTHORITY_AND_ACTION_SANDBOX_DESIGN`.\n",
        encoding="utf-8",
    )
    return data


def render_arc_vi_report(data: dict[str, object]) -> str:
    return f"""# Runtime ARC VI Safety Checkpoint

ARC VI introduces executive cognition and goal-oriented orchestration.

## Executive Architecture

Goal -> Task Analysis -> Capability Selection -> Reasoning Plan -> Execution Plan -> Review Plan -> Safety Validation -> Kernel Dispatch -> Result Review -> Executive Summary

## Goal Engine

Goal: {data['executive_goal']['title']}

## Planning Engine

Tasks: {len(data['goal_decomposition'])}

## Constraint Engine

Blockers: {', '.join(data['constraint_engine']['blockers'])}

## Executive Decision Graph

Nodes: {len(data['executive_decision_graph']['nodes'])}

## Executive Audit

Execution performed: {data['executive_audit']['execution_performed']}

Safety: no training, provider authority, autonomous execution, scheduler, action execution, memory mutation, hidden writes, HYB1 promotion, or knowledge mutation.

Final recommendation: `{data['final_recommendation']}`
"""


def render_executive_dashboard(data: dict[str, object]) -> str:
    tasks = "".join(f"<li>{task['task']} ({task['status']})</li>" for task in data["goal_decomposition"])
    blockers = "".join(f"<li>{blocker}</li>" for blocker in data["constraint_engine"]["blockers"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>DELTA ARC VI Executive Dashboard</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f8fafc;color:#182230}}section{{background:white;border:1px solid #d8e0ec;border-radius:8px;padding:18px;margin:14px 0}}</style></head>
<body>
<h1>DELTA ARC VI Executive Dashboard</h1>
<section><h2>Goal</h2><pre>{json.dumps(data['executive_goal'], indent=2)}</pre></section>
<section><h2>Plans</h2><ul>{tasks}</ul></section>
<section><h2>Constraints</h2><ul>{blockers}</ul></section>
<section><h2>Decision Graph</h2><pre>{json.dumps(data['executive_decision_graph'], indent=2)}</pre></section>
<section><h2>Resource Estimates</h2><pre>{json.dumps(data['resource_plan'], indent=2)}</pre></section>
<section><h2>Review State</h2><pre>{json.dumps(data['escalation_framework'], indent=2)}</pre></section>
</body></html>
"""


if __name__ == "__main__":
    print(write_arc_vi_reports()["final_recommendation"])
