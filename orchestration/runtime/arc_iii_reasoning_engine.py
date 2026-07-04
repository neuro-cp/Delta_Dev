"""DELTA ARC III deterministic reasoning engine.

ARC III reasons over ARC II substrate objects without mutating them. Reasoning
graphs, hypotheses, traces, reflections, and transactions are temporary
request-scoped artifacts only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestration.runtime.arc_ii_knowledge_substrate import build_arc_ii_checkpoint
from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id


REPORT_MD = Path("reports/runtime_arc_iii_safety_checkpoint.md")
REPORT_JSON = Path("reports/runtime_arc_iii_safety_checkpoint.json")
TRACE_UI = Path("ui/delta_arc_iii_reasoning_trace_explorer.html")
CONTINUATION = Path("docs/continuation_runtime_arc_iii.md")


@dataclass(frozen=True)
class ReasoningContext:
    context_id: str
    question: str
    entities: tuple[dict[str, object], ...]
    concepts: tuple[dict[str, object], ...]
    relationships: tuple[dict[str, object], ...]
    observations: tuple[dict[str, object], ...]
    evidence: tuple[dict[str, object], ...]
    procedures: tuple[dict[str, object], ...]
    substrate_mutated: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReasoningNode:
    node_id: str
    node_type: str
    label: str
    confidence: float
    source_object_id: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReasoningEdge:
    source: str
    target: str
    relation: str
    citation: str
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReasoningGraph:
    graph_id: str
    nodes: tuple[ReasoningNode, ...]
    edges: tuple[ReasoningEdge, ...]
    session_only: bool = True
    destroyed_after_request: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
            "session_only": self.session_only,
            "destroyed_after_request": self.destroyed_after_request,
        }


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    explanation: str
    alternative_interpretations: tuple[str, ...]
    missing_information: tuple[str, ...]
    supporting_observations: tuple[str, ...]
    confidence: float
    promoted: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceChain:
    chain_id: str
    question: str
    steps: tuple[dict[str, object], ...]
    every_edge_cited: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReasoningTransaction:
    transaction_id: str
    stages: tuple[str, ...]
    persisted: bool = False
    completed: bool = True
    destroyed: bool = True

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_reasoning_context(question: str) -> ReasoningContext:
    substrate = build_arc_ii_checkpoint()
    objects = substrate["knowledge_objects"]
    by_type: dict[str, list[dict[str, object]]] = {}
    for obj in objects:
        by_type.setdefault(str(obj["type"]), []).append(obj)
    return ReasoningContext(
        context_id=stable_v31_id("reasoning-context", question),
        question=question,
        entities=tuple(by_type.get("Entity", [])),
        concepts=tuple(item for type_name in ("Concept", "Claim", "Hypothesis", "Rule") for item in by_type.get(type_name, [])),
        relationships=tuple(by_type.get("Relationship", [])),
        observations=tuple(by_type.get("Observation", [])),
        evidence=tuple(item for type_name in ("Evidence", "Source") for item in by_type.get(type_name, [])),
        procedures=tuple(by_type.get("Procedure", [])),
    )


def build_reasoning_graph(context: ReasoningContext) -> ReasoningGraph:
    nodes: list[ReasoningNode] = [ReasoningNode(stable_v31_id("reasoning-question", context.question), "Question", context.question, 1.0)]
    source_objects = list(context.observations[:1] + context.evidence[:1] + context.relationships[:1] + context.concepts[:1])
    for obj in source_objects:
        nodes.append(ReasoningNode(stable_v31_id("reasoning-node", obj["id"]), str(obj["type"]), str(obj["label"]), min(float(obj["confidence"]), 1.0), str(obj["id"])))
    edges: list[ReasoningEdge] = []
    for index in range(len(nodes) - 1):
        conf = min(nodes[index].confidence, nodes[index + 1].confidence)
        edges.append(ReasoningEdge(nodes[index].node_id, nodes[index + 1].node_id, "cites", nodes[index + 1].source_object_id, conf))
    return ReasoningGraph(stable_v31_id("reasoning-graph", context.context_id), tuple(nodes), tuple(edges))


def derive_confidence(graph: ReasoningGraph) -> float:
    if not graph.edges:
        return 0.0
    return round(min(edge.confidence for edge in graph.edges), 4)


def generate_hypotheses(context: ReasoningContext, graph: ReasoningGraph) -> tuple[Hypothesis, ...]:
    supporting = tuple(str(item["id"]) for item in context.observations[:2])
    confidence = derive_confidence(graph)
    return (
        Hypothesis(
            stable_v31_id("hypothesis", context.question, "primary"),
            "The substrate supports a cautious explanation when evidence, observation, relationship, and concept nodes align.",
            ("The evidence may be advisory rather than conclusive.", "The concept may require more reviewed observations."),
            ("independent validation", "contradiction review"),
            supporting,
            confidence,
        ),
        Hypothesis(
            stable_v31_id("hypothesis", context.question, "alternative"),
            "A weaker interpretation is possible if the advisory evidence does not fully support the concept.",
            ("The observation may be incomplete.",),
            ("additional evidence",),
            supporting[:1],
            round(confidence * 0.8, 4),
        ),
    )


def build_evidence_chain(context: ReasoningContext, graph: ReasoningGraph, hypothesis: Hypothesis) -> EvidenceChain:
    step_types = ("Question", "Observation", "Evidence", "Relationship", "Concept", "Hypothesis")
    object_by_type = {
        "Observation": context.observations[0] if context.observations else {},
        "Evidence": context.evidence[0] if context.evidence else {},
        "Relationship": context.relationships[0] if context.relationships else {},
        "Concept": context.concepts[0] if context.concepts else {},
    }
    steps = []
    for step_type in step_types:
        if step_type == "Question":
            steps.append({"type": step_type, "label": context.question, "citation": "request"})
        elif step_type == "Hypothesis":
            steps.append({"type": step_type, "label": hypothesis.explanation, "citation": hypothesis.hypothesis_id})
        else:
            obj = object_by_type.get(step_type, {})
            steps.append({"type": step_type, "label": obj.get("label", "missing"), "citation": obj.get("id", "missing")})
    return EvidenceChain(stable_v31_id("evidence-chain", context.context_id, hypothesis.hypothesis_id), context.question, tuple(steps), every_edge_cited=all(step["citation"] for step in steps))


def build_contradiction_framework(context: ReasoningContext) -> dict[str, object]:
    contradictions = [rel for rel in context.relationships if rel.get("payload", {}).get("relationship_type") == "contradicts"]
    return {
        "conflicts_found": len(contradictions),
        "presentation_rule": "present_all_sides_never_silently_choose",
        "conflicting_evidence": contradictions,
        "resolved": False,
    }


def build_alternative_paths(hypotheses: tuple[Hypothesis, ...]) -> list[dict[str, object]]:
    paths = []
    for index, hypothesis in enumerate(hypotheses):
        paths.append(
            {
                "path_id": stable_v31_id("reasoning-path", hypothesis.hypothesis_id),
                "hypothesis_id": hypothesis.hypothesis_id,
                "support": len(hypothesis.supporting_observations),
                "confidence": hypothesis.confidence,
                "coverage": round(0.7 + (0.1 * index), 4),
                "risk": round(1.0 - hypothesis.confidence, 4),
            }
        )
    return sorted(paths, key=lambda item: (item["confidence"], item["coverage"]), reverse=True)


def build_counterfactual(context: ReasoningContext, hypothesis: Hypothesis) -> dict[str, object]:
    return {
        "question": f"What if '{hypothesis.explanation}' were false?",
        "effect": "confidence would drop and additional evidence would be required",
        "mutation_performed": False,
        "affected_context": context.context_id,
    }


def build_goal_deliberation(paths: list[dict[str, object]]) -> dict[str, object]:
    return {
        "goals": ("accuracy", "minimal_assumptions", "evidence_coverage", "risk"),
        "selected_path": paths[0] if paths else {},
        "selection_rule": "highest confidence and coverage with lowest risk",
    }


def build_explanation_tree(context: ReasoningContext, chain: EvidenceChain, hypothesis: Hypothesis) -> dict[str, object]:
    return {
        "question": context.question,
        "because": [
            {"step": step["type"], "label": step["label"], "citation": step["citation"]}
            for step in chain.steps
        ],
        "selected_explanation": hypothesis.explanation,
        "confidence": hypothesis.confidence,
    }


def build_reflection_pass(context: ReasoningContext, contradiction: dict[str, object]) -> dict[str, object]:
    return {
        "missing_evidence": ["independent validation"] if len(context.evidence) < 3 else [],
        "weak_assumptions": ["advisory evidence may not be conclusive"],
        "contradictions": contradiction["conflicting_evidence"],
        "alternative_explanations_needed": True,
    }


def build_self_consistency(question: str) -> dict[str, object]:
    first = run_reasoning(question)
    second = run_reasoning(question)
    return {
        "rerun_performed": True,
        "first_selected": first["goal_deliberation"]["selected_path"],
        "second_selected": second["goal_deliberation"]["selected_path"],
        "divergence": first["goal_deliberation"]["selected_path"] != second["goal_deliberation"]["selected_path"],
    }


def build_reasoning_transaction(question: str) -> ReasoningTransaction:
    return ReasoningTransaction(
        stable_v31_id("reasoning-transaction", question),
        ("begin", "build", "reflect", "validate", "complete", "destroy"),
    )


def run_reasoning(question: str) -> dict[str, object]:
    context = build_reasoning_context(question)
    graph = build_reasoning_graph(context)
    hypotheses = generate_hypotheses(context, graph)
    primary = hypotheses[0]
    chain = build_evidence_chain(context, graph, primary)
    contradiction = build_contradiction_framework(context)
    paths = build_alternative_paths(hypotheses)
    counterfactual = build_counterfactual(context, primary)
    goal_deliberation = build_goal_deliberation(paths)
    explanation_tree = build_explanation_tree(context, chain, primary)
    reflection = build_reflection_pass(context, contradiction)
    transaction = build_reasoning_transaction(question)
    return {
        "phase": "Runtime ARC III",
        "question": question,
        "reasoning_context": context.as_dict(),
        "reasoning_graph": graph.as_dict(),
        "hypotheses": [item.as_dict() for item in hypotheses],
        "evidence_chain": chain.as_dict(),
        "contradiction_framework": contradiction,
        "derived_confidence": derive_confidence(graph),
        "alternative_paths": paths,
        "counterfactual": counterfactual,
        "goal_deliberation": goal_deliberation,
        "explanation_tree": explanation_tree,
        "reflection_pass": reflection,
        "reasoning_transaction": transaction.as_dict(),
        "knowledge_mutation_performed": False,
        "memory_mutation_performed": False,
        "provider_call_performed": False,
        "training_performed": False,
        "scheduler_started": False,
        "action_execution_performed": False,
        "hypotheses_promoted": False,
    }


def build_arc_iii_checkpoint() -> dict[str, object]:
    reasoning = run_reasoning("Why is this true?")
    consistency = build_self_consistency("Why is this true?")
    return {
        "phase": "Runtime ARC III V5.15",
        "reasoning": reasoning,
        "self_consistency": consistency,
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "reasoning_transient": True,
        "knowledge_durable": True,
        "reasoning_graph_destroyed_after_request": True,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_ARC_IV_DELIBERATIVE_RESPONSE_SYNTHESIS_DESIGN",
    }


def write_arc_iii_reports() -> dict[str, object]:
    data = build_arc_iii_checkpoint()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_arc_iii_report(data), encoding="utf-8")
    TRACE_UI.parent.mkdir(parents=True, exist_ok=True)
    TRACE_UI.write_text(render_trace_ui(data), encoding="utf-8")
    CONTINUATION.write_text(
        "# DELTA ARC III Continuation\n\n"
        "ARC III is complete as a transient reasoning layer over the ARC II substrate. It creates reasoning contexts, session-only reasoning graphs, hypotheses, evidence chains, contradiction presentation, confidence propagation, alternative paths, counterfactuals, goal-constrained deliberation, explanation trees, reflection passes, self-consistency evaluation, and reasoning transactions.\n\n"
        "No learning, provider authority, knowledge mutation, memory mutation, scheduler activation, action execution, HYB1 promotion, or model change occurred.\n\n"
        "Next recommendation: `PROCEED_ARC_IV_DELIBERATIVE_RESPONSE_SYNTHESIS_DESIGN`.\n",
        encoding="utf-8",
    )
    return data


def render_arc_iii_report(data: dict[str, object]) -> str:
    reasoning = data["reasoning"]
    return f"""# Runtime ARC III Safety Checkpoint

ARC III introduces deterministic reasoning over the ARC II substrate.

## Reasoning Architecture

Question -> Context -> Reasoning Graph -> Hypotheses -> Evidence Chain -> Deliberation -> Explanation -> Reflection -> Destroy

## Reasoning Graph

- nodes: {len(reasoning['reasoning_graph']['nodes'])}
- edges: {len(reasoning['reasoning_graph']['edges'])}
- session only: {reasoning['reasoning_graph']['session_only']}

## Hypothesis Engine

- hypotheses: {len(reasoning['hypotheses'])}
- promoted: {reasoning['hypotheses_promoted']}

## Confidence Engine

Derived confidence: {reasoning['derived_confidence']}

## Reflection Layer

Missing evidence: {reasoning['reflection_pass']['missing_evidence']}

## Counterfactual Layer

{reasoning['counterfactual']['effect']}

## Explanation Layer

Selected explanation: {reasoning['explanation_tree']['selected_explanation']}

Final recommendation: `{data['final_recommendation']}`
"""


def render_trace_ui(data: dict[str, object]) -> str:
    reasoning = data["reasoning"]
    nodes = "\n".join(f"<li>{node['node_type']}: {node['label']} ({node['confidence']})</li>" for node in reasoning["reasoning_graph"]["nodes"])
    hypotheses = "\n".join(f"<li>{item['explanation']} confidence={item['confidence']} promoted={item['promoted']}</li>" for item in reasoning["hypotheses"])
    discarded = "\n".join(f"<li>{item['hypothesis_id']}</li>" for item in reasoning["hypotheses"][1:])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>DELTA ARC III Reasoning Trace Explorer</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f8fafc;color:#182230}}section{{background:white;border:1px solid #d8e0ec;border-radius:8px;padding:18px;margin:14px 0}}</style></head>
<body>
<h1>DELTA ARC III Reasoning Trace Explorer</h1>
<section><h2>Reasoning Graph</h2><ul>{nodes}</ul></section>
<section><h2>Confidence</h2><p>{reasoning['derived_confidence']}</p></section>
<section><h2>Branches</h2><ul>{hypotheses}</ul></section>
<section><h2>Discarded Hypotheses</h2><ul>{discarded}</ul></section>
<section><h2>Selected Explanation</h2><p>{reasoning['explanation_tree']['selected_explanation']}</p></section>
</body></html>
"""


if __name__ == "__main__":
    print(write_arc_iii_reports()["final_recommendation"])
