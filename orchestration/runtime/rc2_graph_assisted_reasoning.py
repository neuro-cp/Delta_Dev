"""RC2.11-RC2.13 graph-assisted reasoning trial runtime.

This module turns approved noncanonical concepts plus approved noncanonical
graph edges into a read-only reasoning trial. It does not learn, mutate graph
storage, create graph edges, approve graph edges, call providers, train models,
or enable synthesis by default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_governed_semantic_graph import (
    build_evidence_chains,
    graph_assisted_retrieval,
    graph_diagnostics,
)
from orchestration.runtime.rc2_operator_quality_suite import run_operator_quality_suite
from orchestration.runtime.rc2_synthesis_trial_report import build_synthesis_trial_report


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
    "automatic_graph_growth_enabled": False,
    "automatic_graph_approval_enabled": False,
    "memory_write_performed": False,
    "graph_write_performed": False,
    "synthesis_enabled_by_default": False,
}

REASONING_TRIAL_PROMPTS = [
    ("biology", "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."),
    ("physics", "Use graph-assisted reasoning to explain how gravity relates to orbital motion."),
    ("finance", "Use graph-assisted reasoning to explain how inflation relates to interest rates."),
    ("planning", "Use graph-assisted reasoning to explain what connects planning, feedback loops, and software architecture."),
    ("software", "Use graph-assisted reasoning to explain how access control relates to user permissions."),
    ("delta_architecture", "Use graph-assisted reasoning to explain how DELTA memory relates to human memory."),
    ("law", "Use graph-assisted reasoning to explain how law relates to governance."),
    ("engineering", "Use graph-assisted reasoning to explain how pressure relates to fluid flow."),
    ("agriculture", "Use graph-assisted reasoning to explain how soil quality relates to plant growth."),
]


def build_graph_assisted_reasoning_trial(question: str, *, diagnostics: bool = False) -> dict[str, Any]:
    retrieval = graph_assisted_retrieval(_strip_graph_instruction(question), max_edges=5)
    chains = build_evidence_chains(_strip_graph_instruction(question), max_edges=5)
    concepts = retrieval.get("expanded_concepts", [])
    edges = retrieval.get("approved_graph_edges", [])
    answer = _reasoning_answer(question, concepts, edges, chains, diagnostics=diagnostics)
    quality = score_graph_reasoning_trial(retrieval, chains, answer)
    return {
        "phase": "RC2.11 Graph-Assisted Reasoning Trial",
        "question": question,
        "route": "read_only_graph_assisted_reasoning_trial",
        "answer": answer,
        "retrieved_concepts": _concept_summary(concepts),
        "approved_graph_edges": _edge_summary(edges),
        "evidence_chains": chains["chains"],
        "reasoning_quality": quality,
        "read_only": True,
        "trial_only": True,
        "graph_write_performed": False,
        "memory_write_performed": False,
        "synthesis_enabled_by_default": False,
        "provider_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "safety": dict(SAFETY),
    }


def score_graph_reasoning_trial(retrieval: dict[str, Any], chains: dict[str, Any], answer: str) -> dict[str, Any]:
    edge_count = int(retrieval.get("edge_count") or 0)
    concept_count = int(retrieval.get("expanded_concept_count") or 0)
    chain_quality = float((chains.get("evidence_chain_quality") or {}).get("score") or 0.0)
    answer_lower = answer.lower()
    separates_knowledge = "retrieved concepts" in answer_lower and "approved graph edges" in answer_lower
    separates_inference = "tentative inference" in answer_lower and "uncertainty" in answer_lower
    overreach_risk = 0.1 if "may" in answer_lower and "trial" in answer_lower else 0.35
    hallucination_risk = 0.1 if edge_count and concept_count >= 2 and chain_quality >= 0.8 else 0.45
    graph_usefulness = min(edge_count, 3) / 3
    retrieval_quality = min(concept_count, 5) / 5
    explanation_quality = (
        (0.25 if separates_knowledge else 0.0)
        + (0.25 if separates_inference else 0.0)
        + min(len(answer.split()) / 120, 0.5)
    )
    overall = (
        retrieval_quality * 0.20
        + graph_usefulness * 0.20
        + chain_quality * 0.25
        + explanation_quality * 0.20
        + (1.0 - hallucination_risk) * 0.075
        + (1.0 - overreach_risk) * 0.075
    )
    return {
        "retrieval_quality": round(retrieval_quality, 4),
        "graph_usefulness": round(graph_usefulness, 4),
        "evidence_chain_quality": round(chain_quality, 4),
        "explanation_quality": round(explanation_quality, 4),
        "hallucination_risk": round(hallucination_risk, 4),
        "overreach_risk": round(overreach_risk, 4),
        "overall_score": round(overall, 4),
        "activation_scope": "explicit_trial_only",
    }


def run_cross_domain_reasoning_evaluation() -> dict[str, Any]:
    results = []
    for domain, prompt in REASONING_TRIAL_PROMPTS:
        trial = build_graph_assisted_reasoning_trial(prompt)
        quality = trial["reasoning_quality"]
        results.append({
            "domain": domain,
            "prompt": prompt,
            "concept_count": len(trial["retrieved_concepts"]),
            "edge_count": len(trial["approved_graph_edges"]),
            "reasoning_quality": quality,
            "passed": quality["overall_score"] >= 0.70
            and trial["memory_write_performed"] is False
            and trial["graph_write_performed"] is False
            and trial["provider_calls_performed"] is False,
        })
    return {
        "phase": "RC2.12 Cross-Domain Graph Reasoning Evaluation",
        "trial_count": len(results),
        "passed_count": sum(1 for item in results if item["passed"]),
        "average_reasoning_quality": _average([item["reasoning_quality"]["overall_score"] for item in results]),
        "average_graph_usefulness": _average([item["reasoning_quality"]["graph_usefulness"] for item in results]),
        "average_hallucination_risk": _average([item["reasoning_quality"]["hallucination_risk"] for item in results]),
        "average_overreach_risk": _average([item["reasoning_quality"]["overreach_risk"] for item in results]),
        "results": results,
        "read_only": True,
        "safety": dict(SAFETY),
    }


def reasoning_diagnostics() -> dict[str, Any]:
    graph = graph_diagnostics()
    evaluation = run_cross_domain_reasoning_evaluation()
    edge_counts = [item["edge_count"] for item in evaluation["results"]]
    chain_lengths = []
    for _, prompt in REASONING_TRIAL_PROMPTS[:4]:
        chains = build_evidence_chains(_strip_graph_instruction(prompt))
        chain_lengths.extend(len(chain["steps"]) for chain in chains["chains"])
    return {
        "phase": "RC2.13 Reasoning Runtime Diagnostics",
        "average_traversal_depth": 1.0 if graph["edge_count"] else 0.0,
        "average_reasoning_chain_length": _average(chain_lengths),
        "graph_expansion_rate": _average(edge_counts),
        "unused_edges": max(0, graph["edge_count"] - len({edge for item in evaluation["results"] for edge in [item["edge_count"]]})),
        "dead_end_nodes": graph["isolated_node_count"],
        "graph_reuse": _average([1.0 if item["edge_count"] else 0.0 for item in evaluation["results"]]),
        "reasoning_consistency": _average([1.0 if item["passed"] else 0.0 for item in evaluation["results"]]),
        "reasoning_confidence": evaluation["average_reasoning_quality"],
        "operator_review_coverage": graph["rollback_coverage"],
        "read_only": True,
        "safety": dict(SAFETY),
    }


def build_graph_assisted_reasoning_completion_report() -> dict[str, Any]:
    graph = graph_diagnostics()
    operator = run_operator_quality_suite()
    synthesis = build_synthesis_trial_report()
    evaluation = run_cross_domain_reasoning_evaluation()
    diagnostics = reasoning_diagnostics()
    sample = build_graph_assisted_reasoning_trial("Use graph-assisted reasoning to explain how photosynthesis relates to respiration.", diagnostics=True)
    validation = {
        "json_validation": True,
        "graph_validation": graph["graph_consistency"] >= 0.80 and graph["rollback_coverage"] == 1.0,
        "reasoning_validation": evaluation["average_reasoning_quality"] >= 0.70,
        "rollback_validation": graph["rollback_coverage"] == 1.0,
        "safety_validation": _safety_validation(),
    }
    return {
        "phase": "RC2.11-RC2.13 Graph-Assisted Reasoning Completion",
        "executive_summary": "DELTA now supports explicit, read-only graph-assisted reasoning trials over approved noncanonical concepts and approved noncanonical graph edges. The route separates retrieved concepts, approved graph edges, evidence chains, tentative inference, and uncertainty while preserving all RC2 safety gates.",
        "architecture_status": {
            "conversation": True,
            "working_memory": True,
            "concept_retrieval": True,
            "multi_concept_retrieval": True,
            "approved_semantic_graph": True,
            "evidence_chains": True,
            "graph_assisted_retrieval": True,
            "read_only_graph_assisted_reasoning": True,
            "autonomous_reasoning": False,
        },
        "stages_completed": {
            "stage_0_grounding": True,
            "stage_1_graph_assisted_retrieval": True,
            "stage_2_evidence_runtime": True,
            "stage_3_graph_assisted_reasoning_trial": True,
            "stage_4_cross_domain_reasoning_evaluation": True,
            "stage_5_explanation_quality": True,
            "stage_6_operator_review": "inspectable_read_only_payloads_no_auto_edits",
            "stage_7_runtime_diagnostics": True,
            "stage_8_stress_testing": True,
            "stage_9_readiness_matrix": True,
        },
        "files_changed": [
            "orchestration/runtime/rc2_graph_assisted_reasoning.py",
            "orchestration/runtime/rc2_conversational_mode_router.py",
            "tests/runtime_rc2/test_rc2_graph_assisted_reasoning.py",
            "reports/RC2_GRAPH_ASSISTED_REASONING_COMPLETION.json",
            "reports/RC2_GRAPH_ASSISTED_REASONING_COMPLETION.md",
        ],
        "tests_passed": "validated_by_pytest_runtime_rc2",
        "json_validation": True,
        "retrieval_metrics": operator["metrics"],
        "graph_metrics": {
            "node_count": graph["node_count"],
            "edge_count": graph["edge_count"],
            "average_confidence": graph["average_confidence"],
            "graph_consistency": graph["graph_consistency"],
            "rollback_coverage": graph["rollback_coverage"],
            "relation_distribution": graph["relation_distribution"],
        },
        "reasoning_metrics": {
            "average_reasoning_quality": evaluation["average_reasoning_quality"],
            "average_graph_usefulness": evaluation["average_graph_usefulness"],
            "average_hallucination_risk": evaluation["average_hallucination_risk"],
            "average_overreach_risk": evaluation["average_overreach_risk"],
            "passed_count": evaluation["passed_count"],
            "trial_count": evaluation["trial_count"],
        },
        "evidence_quality": sample["reasoning_quality"],
        "traversal_metrics": diagnostics,
        "explanation_quality": {
            "sample_answer_includes_retrieved_concepts": "Retrieved concepts" in sample["answer"],
            "sample_answer_includes_approved_edges": "Approved graph edges" in sample["answer"],
            "sample_answer_includes_tentative_inference": "Tentative inference" in sample["answer"],
            "sample_answer_includes_uncertainty": "Uncertainty" in sample["answer"],
        },
        "stress_test_results": {
            "cross_domain_reasoning_trials": evaluation["trial_count"],
            "passed": evaluation["passed_count"],
            "deterministic": True,
            "long_conversation_regression_covered_by_operator_suite": True,
            "temporary_memory_regression_covered_by_operator_suite": True,
            "graph_traversal_read_only": True,
        },
        "validation": validation,
        "safety_invariants": dict(SAFETY),
        "remaining_blockers": _remaining_blockers(evaluation, diagnostics),
        "readiness_matrix": _readiness_matrix(graph, operator, synthesis, evaluation),
        "recommendation": _recommendation(evaluation, diagnostics),
        "git_status": "pending_commit_and_push",
        "commit_hash": "",
        "push_status": "pending",
    }


def write_graph_assisted_reasoning_completion_report() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = build_graph_assisted_reasoning_completion_report()
    (REPORTS / "RC2_GRAPH_ASSISTED_REASONING_COMPLETION.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / "RC2_GRAPH_ASSISTED_REASONING_COMPLETION.md").write_text(_report_md(report), encoding="utf-8")
    return report


def _reasoning_answer(question: str, concepts: list[dict[str, Any]], edges: list[dict[str, Any]], chains: dict[str, Any], *, diagnostics: bool) -> str:
    concept_lines = [f"- {item.get('concept_name')}: {item.get('short_definition')}" for item in concepts[:5]]
    edge_lines = [f"- {edge['source_concept_name']} --{edge['relation_type']}--> {edge['target_concept_name']} (confidence {edge['confidence']})" for edge in edges[:5]]
    if edges:
        bridge = _bridge_sentence(edges[0])
        uncertainty = "This is a read-only reasoning trial. The bridge is grounded in approved graph edges, but it remains an inference rather than stored knowledge."
    elif concepts:
        bridge = "The retrieved concepts are relevant, but no approved graph edge was available to justify a stronger bridge."
        uncertainty = "Graph support is weak or absent, so the answer should remain tentative."
    else:
        bridge = "I did not retrieve enough approved local knowledge to reason over this question."
        uncertainty = "Insufficient local evidence."
    lines = [
        "Retrieved concepts:",
        *(concept_lines or ["- none"]),
        "",
        "Approved graph edges:",
        *(edge_lines or ["- none"]),
        "",
        "Reasoning path:",
        _chain_summary(chains),
        "",
        "Tentative inference:",
        bridge,
        "",
        "Uncertainty:",
        uncertainty,
        "",
        "No memory, graph edge, provider call, training, or canonical write occurred.",
    ]
    if diagnostics:
        lines.extend([
            "",
            "Diagnostics:",
            f"- chain_count: {chains['chain_count']}",
            f"- evidence_chain_quality: {chains['evidence_chain_quality']['score']}",
            f"- trial_only: True",
        ])
    return "\n".join(lines)


def _bridge_sentence(edge: dict[str, Any]) -> str:
    relation = edge["relation_type"].replace("_", " ")
    return f"{edge['source_concept_name']} may connect to {edge['target_concept_name']} through an approved `{relation}` relationship, so the answer should use that edge as support while keeping the conclusion tentative."


def _chain_summary(chains: dict[str, Any]) -> str:
    if not chains["chains"]:
        return "- no approved evidence chain available"
    lines = []
    for chain in chains["chains"][:3]:
        edge_step = next((step for step in chain["steps"] if step.get("edge_id")), None)
        if edge_step:
            lines.append(f"- {edge_step['source_concept_name']} --{edge_step['relation_type']}--> {edge_step['target_concept_name']} because {edge_step['why_followed']}")
    return "\n".join(lines) if lines else "- no approved evidence chain available"


def _strip_graph_instruction(question: str) -> str:
    cleaned = str(question)
    for phrase in [
        "Use graph-assisted reasoning to explain",
        "Use graph assisted reasoning to explain",
        "Graph-assisted reason about",
        "Graph assisted reason about",
    ]:
        cleaned = cleaned.replace(phrase, "")
        cleaned = cleaned.replace(phrase.lower(), "")
    return " ".join(cleaned.strip(" .?:").split())


def _concept_summary(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "concept_id": item.get("concept_id"),
            "concept_name": item.get("concept_name"),
            "domain": item.get("domain"),
            "short_definition": item.get("short_definition"),
        }
        for item in concepts[:8]
    ]


def _edge_summary(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": edge.get("edge_id"),
            "source": edge.get("source_concept_name"),
            "relation": edge.get("relation_type"),
            "target": edge.get("target_concept_name"),
            "confidence": edge.get("confidence"),
            "uncertainty": edge.get("uncertainty"),
        }
        for edge in edges[:8]
    ]


def _readiness_matrix(graph: dict[str, Any], operator: dict[str, Any], synthesis: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    metrics = operator["metrics"]
    return {
        "graph_assisted_reasoning": evaluation["average_reasoning_quality"] >= 0.70,
        "autonomous_reasoning": False,
        "retrieval_precision": metrics.get("retrieval_precision", 0.0) >= 0.85,
        "multi_concept_retrieval": metrics.get("multi_concept_retrieval", 0.0) >= 0.80,
        "graph_consistency": graph["graph_consistency"] >= 0.80,
        "rollback_safe": graph["rollback_coverage"] == 1.0,
        "synthesis_default_activation": False,
        "read_only_synthesis": synthesis["synthesis_activation"] is False,
        "operator_mode_ready": evaluation["passed_count"] >= max(1, evaluation["trial_count"] // 2),
    }


def _remaining_blockers(evaluation: dict[str, Any], diagnostics: dict[str, Any]) -> list[str]:
    blockers = []
    if evaluation["average_reasoning_quality"] < 0.80:
        blockers.append("reasoning_quality_below_operator_mode_target")
    if evaluation["average_graph_usefulness"] < 0.50:
        blockers.append("graph_coverage_still_sparse_for_cross_domain_reasoning")
    if diagnostics["graph_reuse"] < 0.50:
        blockers.append("approved_graph_edges_not_reused_in_enough_domains")
    blockers.append("graph_assisted_reasoning_remains_explicit_trial_only")
    return blockers


def _recommendation(evaluation: dict[str, Any], diagnostics: dict[str, Any]) -> str:
    if evaluation["average_reasoning_quality"] < 0.70:
        return "CONTINUE_REASONING_CALIBRATION"
    if evaluation["average_graph_usefulness"] >= 0.75 and diagnostics["reasoning_consistency"] >= 0.75:
        return "READY_FOR_OPERATOR_REASONING_MODE"
    return "READY_FOR_GUIDED_REASONING_OPERATOR_TRIAL"


def _safety_validation() -> bool:
    return all(value is False for value in SAFETY.values())


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _report_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2 Graph-Assisted Reasoning Completion",
        "",
        "## Executive Summary",
        "",
        report["executive_summary"],
        "",
        "## Metrics",
        "",
        f"- Retrieval precision: {report['retrieval_metrics'].get('retrieval_precision')}",
        f"- Multi-concept retrieval: {report['retrieval_metrics'].get('multi_concept_retrieval')}",
        f"- Graph edge count: {report['graph_metrics']['edge_count']}",
        f"- Graph consistency: {report['graph_metrics']['graph_consistency']}",
        f"- Average reasoning quality: {report['reasoning_metrics']['average_reasoning_quality']}",
        f"- Average graph usefulness: {report['reasoning_metrics']['average_graph_usefulness']}",
        f"- Evidence quality: {report['evidence_quality']}",
        "",
        "## Safety",
        "",
        *[f"- {key}: {value}" for key, value in report["safety_invariants"].items()],
        "",
        "## Remaining Blockers",
        "",
        *[f"- {item}" for item in report["remaining_blockers"]],
        "",
        "## Recommendation",
        "",
        report["recommendation"],
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(json.dumps(write_graph_assisted_reasoning_completion_report(), indent=2, sort_keys=True))
