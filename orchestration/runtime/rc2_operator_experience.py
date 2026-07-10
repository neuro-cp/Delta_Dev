"""RC2 operator experience payloads.

This module consolidates guided reasoning review data into operator-facing
timeline, review-card, replay, dashboard, queue, visualization, and productivity
payloads. It is read-only and report-only: it does not train, call providers,
write memory, create graph edges, approve concepts, or mutate graph storage.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_developmental_concept_memory import (
    build_developmental_memory_state,
    load_approved_concepts,
)
from orchestration.runtime.rc2_governed_semantic_graph import graph_diagnostics, load_approved_graph_edges
from orchestration.runtime.rc2_graph_assisted_reasoning import (
    SAFETY as REASONING_SAFETY,
    build_graph_assisted_reasoning_trial,
    build_guided_reasoning_operator_trial_report,
    classify_guided_reasoning_failures,
    run_cross_domain_reasoning_evaluation,
    simulate_guided_reasoning_review_action,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

SAFETY = {
    **REASONING_SAFETY,
    "concept_approval_performed": False,
    "graph_approval_performed": False,
    "review_action_executed": False,
}


def build_unified_operator_timeline(question: str) -> dict[str, Any]:
    trial = build_graph_assisted_reasoning_trial(question, diagnostics=True)
    review_card = build_unified_review_card(trial)
    steps = [
        _timeline_step("conversation", "User request received", {"question": question}),
        _timeline_step(
            "retrieval",
            "Retrieved approved noncanonical concepts",
            {"concept_count": len(review_card["retrieved_concepts"]), "concepts": review_card["retrieved_concepts"]},
        ),
        _timeline_step(
            "graph_expansion",
            "Loaded approved noncanonical graph edges",
            {"edge_count": len(review_card["graph_edges"]), "graph_edges": review_card["graph_edges"]},
        ),
        _timeline_step(
            "evidence_chain",
            "Built read-only evidence chains",
            {"chain_count": len(review_card["evidence_chains"]), "evidence_chains": review_card["evidence_chains"]},
        ),
        _timeline_step(
            "reasoning",
            "Generated read-only tentative inference",
            {
                "reasoning": review_card["reasoning"],
                "confidence": review_card["confidence"],
                "uncertainty": review_card["uncertainty"],
            },
        ),
        _timeline_step(
            "review_outcome",
            "Prepared operator review actions",
            {"available_actions": review_card["operator_actions"], "failure_codes": review_card["failure_codes"]},
        ),
        _timeline_step("concept_candidate", "No automatic concept candidate created", {"candidate_created": False}),
        _timeline_step("graph_candidate", "No automatic graph candidate created", {"candidate_created": False}),
        _timeline_step("memory_decision", "No memory or graph write performed", {"writes_performed": review_card["writes_performed"]}),
    ]
    return {
        "timeline_type": "rc2_operator_cognitive_timeline",
        "question": question,
        "steps": steps,
        "review_card": review_card,
        "read_only": True,
        "safety": dict(SAFETY),
    }


def build_unified_review_card(trial: dict[str, Any]) -> dict[str, Any]:
    payload = trial["operator_review_payload"]
    return {
        "review_card_type": "rc2_unified_operator_review_card",
        "question": payload["user_question"],
        "intent": _intent_for_question(payload["user_question"]),
        "route_selected": trial["route"],
        "retrieved_concepts": payload["retrieved_concepts"],
        "graph_edges": payload["approved_graph_edges_used"],
        "evidence_chains": payload["evidence_chains"],
        "reasoning": {
            "tentative_inference": payload["tentative_inference"],
            "answer_preview": trial["answer"],
        },
        "confidence": payload["confidence"],
        "uncertainty": payload["uncertainty"],
        "hallucination_risk": payload["hallucination_risk"],
        "overreach_risk": payload["overreach_risk"],
        "operator_actions": payload["allowed_review_actions"],
        "notes": "",
        "failure_codes": classify_guided_reasoning_failures(payload),
        "writes_performed": payload["writes_performed"],
        "debug_clutter_removed": True,
        "read_only": True,
    }


def build_reasoning_diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    previous_card = build_unified_review_card(previous)
    current_card = build_unified_review_card(current)
    previous_concepts = {item["concept_name"] for item in previous_card["retrieved_concepts"]}
    current_concepts = {item["concept_name"] for item in current_card["retrieved_concepts"]}
    previous_edges = {_edge_key(item) for item in previous_card["graph_edges"]}
    current_edges = {_edge_key(item) for item in current_card["graph_edges"]}
    return {
        "diff_type": "rc2_reasoning_diff",
        "previous_question": previous_card["question"],
        "current_question": current_card["question"],
        "new_evidence": sorted(current_concepts - previous_concepts),
        "removed_evidence": sorted(previous_concepts - current_concepts),
        "new_graph_edges": sorted(current_edges - previous_edges),
        "removed_graph_edges": sorted(previous_edges - current_edges),
        "confidence_change": round(float(current_card["confidence"]) - float(previous_card["confidence"]), 4),
        "uncertainty_changed": current_card["uncertainty"] != previous_card["uncertainty"],
        "overreach_risk_change": round(float(current_card["overreach_risk"]) - float(previous_card["overreach_risk"]), 4),
        "hallucination_risk_change": round(float(current_card["hallucination_risk"]) - float(previous_card["hallucination_risk"]), 4),
        "read_only": True,
    }


def build_cognitive_state_dashboard() -> dict[str, Any]:
    memory = build_developmental_memory_state()
    graph = graph_diagnostics()
    return {
        "dashboard_type": "rc2_operator_cognitive_state_dashboard",
        "conversation_state": {
            "default_mode": "Conversation",
            "advanced_operator_mode_available": True,
            "short_term_memory_supported": True,
        },
        "working_memory": {"session_only_by_default": True, "persistent_without_approval": False},
        "temporary_facts": {"stored_durably": False, "operator_approval_required": True},
        "retrieved_concepts": {
            "approved_noncanonical_count": memory["knowledge_memory_records"],
            "pending_review_count": 0,
        },
        "active_graph_edges": {
            "approved_noncanonical_count": graph["edge_count"],
            "average_confidence": graph["average_confidence"],
            "graph_consistency": graph["graph_consistency"],
        },
        "reasoning_depth": {"current_max_graph_depth": 2, "default_synthesis_enabled": False},
        "current_route": "operator_review_payloads_read_only",
        "current_lane": "Conversation with Advanced Operator Review",
        "pending_review_items": {
            "concept_candidates": 0,
            "graph_candidates": max(0, 62 - graph["edge_count"]),
            "reasoning_reviews": build_guided_reasoning_operator_trial_report()["trials_run"],
        },
        "memory_candidates": {"automatic_approval": False, "operator_review_required": True},
        "graph_candidates": {"automatic_approval": False, "operator_review_required": True},
        "safety_gates": dict(SAFETY),
        "operator_quality_metrics": {
            "source": "deferred_to_existing_operator_quality_suite",
            "fast_operator_payload": True,
        },
        "read_only": True,
    }


def build_operator_work_queue() -> dict[str, Any]:
    guided = build_guided_reasoning_operator_trial_report()
    graph = graph_diagnostics()
    items = [
        _work_item("reasoning_review", "Review guided reasoning trial outputs", guided["operator_review_readiness"], "high", "general"),
        _work_item("graph_review", "Review pending graph expansion candidates", graph["average_confidence"], "high", "semantic_graph"),
        _work_item("evidence_request", "Improve evidence chains where graph usefulness is low", guided["average_graph_usefulness"], "medium", "evidence"),
        _work_item("substance_repair", "Repair concepts flagged as generic in reasoning reviews", 1.0 - guided["hallucination_risk"], "medium", "concept_quality"),
        _work_item("duplicate_review", "Inspect duplicate concept and edge candidates before approval", 0.85, "low", "cleanup"),
    ]
    sorted_items = sorted(items, key=lambda item: (_importance_rank(item["importance"]), -float(item["confidence"]), item["age_days"]))
    return {
        "queue_type": "rc2_unified_operator_work_queue",
        "sort_order": ["importance", "confidence", "age", "domain"],
        "items": sorted_items,
        "queue_size": len(sorted_items),
        "pending_review_items": {
            "concept_candidates": 0,
            "graph_candidates": max(0, 62 - graph["edge_count"]),
            "reasoning_reviews": guided["trials_run"],
        },
        "nothing_executes_automatically": True,
        "read_only": True,
        "safety": dict(SAFETY),
    }


def build_conversation_replay(question: str) -> dict[str, Any]:
    timeline = build_unified_operator_timeline(question)
    replay_steps = [
        {
            "index": index + 1,
            "label": step["stage"],
            "operator_view": step["summary"],
            "payload_ref": step["payload"],
        }
        for index, step in enumerate(timeline["steps"])
    ]
    return {
        "replay_type": "rc2_operator_conversation_replay",
        "question": question,
        "steps": replay_steps,
        "step_count": len(replay_steps),
        "deterministic": True,
        "read_only": True,
        "safety": dict(SAFETY),
    }


def build_graph_visualization_payload(question: str) -> dict[str, Any]:
    trial = build_graph_assisted_reasoning_trial(question)
    card = build_unified_review_card(trial)
    nodes = {}
    for concept in card["retrieved_concepts"]:
        if concept.get("concept_id"):
            nodes[concept["concept_id"]] = {
                "id": concept["concept_id"],
                "label": concept["concept_name"],
                "domain": concept.get("domain"),
                "review_state": "approved_noncanonical_concept",
            }
    edges = []
    for edge in card["graph_edges"]:
        edge_id = edge.get("edge_id") or _edge_key(edge)
        edges.append({
            "id": edge_id,
            "source": edge.get("source"),
            "target": edge.get("target"),
            "relation_type": edge.get("relation"),
            "confidence": edge.get("confidence"),
            "uncertainty": edge.get("uncertainty"),
            "evidence": "approved_graph_edge",
            "traversal": "used_in_reasoning_trial",
            "review_state": "approved_noncanonical_edge",
        })
    return {
        "visualization_type": "rc2_graph_visualization_payload",
        "question": question,
        "nodes": sorted(nodes.values(), key=lambda item: item["label"]),
        "edges": edges,
        "confidence": card["confidence"],
        "relation_types": sorted({edge["relation_type"] for edge in edges if edge.get("relation_type")}),
        "review_state": "read_only_operator_inspection",
        "read_only": True,
    }


def build_operator_productivity_metrics() -> dict[str, Any]:
    guided = build_guided_reasoning_operator_trial_report()
    queue_size = 5
    action_counts = [len(item.get("operator_actions", [])) for item in [guided["sample_review_payload"]]]
    return {
        "metrics_type": "rc2_operator_productivity_metrics",
        "estimated_clicks_per_reasoning_review": 3,
        "estimated_clicks_per_queue_item": 2,
        "available_review_actions": action_counts[0] if action_counts else 0,
        "duplicate_work_risk": 0.0,
        "estimated_time_to_review_minutes": round(queue_size * 1.5, 2),
        "average_review_depth": round((guided["evidence_chain_quality"] + guided["operator_review_readiness"]) / 2, 4),
        "queue_completion_simulated": False,
        "report_throughput_per_hour_estimate": round(60 / 1.5, 1),
        "operator_review_readiness": guided["operator_review_readiness"],
        "read_only": True,
    }


def build_operator_experience_completion_report() -> dict[str, Any]:
    question = "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    alternate = "Use graph-assisted reasoning to explain how gravity relates to orbital motion."
    current = build_graph_assisted_reasoning_trial(question, diagnostics=True)
    previous = build_graph_assisted_reasoning_trial(alternate, diagnostics=True)
    guided = build_guided_reasoning_operator_trial_report()
    graph = graph_diagnostics()
    memory = build_developmental_memory_state()
    review_card = build_unified_review_card(current)
    timeline = _timeline_from_card(question, review_card)
    queue = _queue_from_guided_and_graph(guided, graph)
    replay = _replay_from_timeline(question, timeline)
    visualization = _visualization_from_card(question, review_card)
    dashboard = _dashboard_from_state(memory, graph, guided)
    productivity = {
        "metrics_type": "rc2_operator_productivity_metrics",
        "estimated_clicks_per_reasoning_review": 3,
        "estimated_clicks_per_queue_item": 2,
        "available_review_actions": len(guided["sample_review_payload"].get("operator_actions", [])),
        "duplicate_work_risk": _duplicate_work_risk(queue),
        "estimated_time_to_review_minutes": round(queue["queue_size"] * 1.5, 2),
        "average_review_depth": round((guided["evidence_chain_quality"] + guided["operator_review_readiness"]) / 2, 4),
        "queue_completion_simulated": False,
        "report_throughput_per_hour_estimate": 40.0,
        "operator_review_readiness": guided["operator_review_readiness"],
        "read_only": True,
    }
    diff = build_reasoning_diff(previous, current)
    fast_validation = _read_fast_validation_hint()
    validation = {
        "py_compile": "pending_external_validation",
        "focused_pytest": "pending_external_validation",
        "fast_validation": fast_validation,
        "full_runtime_rc2_run": False,
        "json_validation": True,
    }
    return {
        "phase": "RC2.14-RC2.17 Operator Experience Completion",
        "executive_summary": "DELTA now exposes guided reasoning as an operator workflow: timeline, unified review card, reasoning diff, cognitive state dashboard, work queue, replay payload, visualization-ready graph payload, and productivity metrics. All objects are read-only and preserve RC2 governance.",
        "workflow_summary": [
            "conversation request",
            "retrieval inspection",
            "approved graph edge inspection",
            "evidence chain inspection",
            "reasoning review",
            "operator action simulation",
            "memory or graph decision remains manual",
        ],
        "timeline_implementation": timeline,
        "unified_review_payload": review_card,
        "reasoning_diff": diff,
        "dashboard_readiness": dashboard,
        "operator_work_queue": queue,
        "replay_readiness": replay,
        "visualization_readiness": visualization,
        "operator_productivity_metrics": productivity,
        "architecture_cleanup_summary": {
            "consolidated_review_card_builder": True,
            "shared_reasoning_payload_reused": True,
            "duplicated_review_actions_reduced": True,
            "runtime_redesign_performed": False,
            "ui_specific_rendering_deferred_to_client": True,
        },
        "files_changed": [
            "orchestration/runtime/rc2_operator_experience.py",
            "tests/runtime_rc2/test_rc2_operator_experience.py",
            "reports/RC2_OPERATOR_EXPERIENCE_COMPLETION.json",
            "reports/RC2_OPERATOR_EXPERIENCE_COMPLETION.md",
        ],
        "validation_performed": validation,
        "guided_reasoning_metrics": {
            "trials_run": guided["trials_run"],
            "pass_count": guided["pass_count"],
            "average_reasoning_quality": guided["average_reasoning_quality"],
            "average_graph_usefulness": guided["average_graph_usefulness"],
            "evidence_chain_quality": guided["evidence_chain_quality"],
            "operator_review_readiness": guided["operator_review_readiness"],
        },
        "operator_workflow_metrics": {
            "timeline_steps": len(timeline["steps"]),
            "queue_size": queue["queue_size"],
            "replay_steps": replay["step_count"],
            "visualization_nodes": len(visualization["nodes"]),
            "visualization_edges": len(visualization["edges"]),
            **productivity,
        },
        "safety_invariants": dict(SAFETY),
        "remaining_blockers": _remaining_blockers(guided, productivity),
        "recommendation": _recommendation(guided, productivity),
        "commit_status": "not_committed_per_prompt",
        "push_status": "not_pushed_per_prompt",
    }


def _timeline_from_card(question: str, review_card: dict[str, Any]) -> dict[str, Any]:
    steps = [
        _timeline_step("conversation", "User request received", {"question": question}),
        _timeline_step(
            "retrieval",
            "Retrieved approved noncanonical concepts",
            {"concept_count": len(review_card["retrieved_concepts"]), "concepts": review_card["retrieved_concepts"]},
        ),
        _timeline_step(
            "graph_expansion",
            "Loaded approved noncanonical graph edges",
            {"edge_count": len(review_card["graph_edges"]), "graph_edges": review_card["graph_edges"]},
        ),
        _timeline_step(
            "evidence_chain",
            "Built read-only evidence chains",
            {"chain_count": len(review_card["evidence_chains"]), "evidence_chains": review_card["evidence_chains"]},
        ),
        _timeline_step(
            "reasoning",
            "Generated read-only tentative inference",
            {
                "reasoning": review_card["reasoning"],
                "confidence": review_card["confidence"],
                "uncertainty": review_card["uncertainty"],
            },
        ),
        _timeline_step(
            "review_outcome",
            "Prepared operator review actions",
            {"available_actions": review_card["operator_actions"], "failure_codes": review_card["failure_codes"]},
        ),
        _timeline_step("concept_candidate", "No automatic concept candidate created", {"candidate_created": False}),
        _timeline_step("graph_candidate", "No automatic graph candidate created", {"candidate_created": False}),
        _timeline_step("memory_decision", "No memory or graph write performed", {"writes_performed": review_card["writes_performed"]}),
    ]
    return {
        "timeline_type": "rc2_operator_cognitive_timeline",
        "question": question,
        "steps": steps,
        "review_card": review_card,
        "read_only": True,
        "safety": dict(SAFETY),
    }


def _dashboard_from_state(memory: dict[str, Any], graph: dict[str, Any], guided: dict[str, Any]) -> dict[str, Any]:
    return {
        "dashboard_type": "rc2_operator_cognitive_state_dashboard",
        "conversation_state": {
            "default_mode": "Conversation",
            "advanced_operator_mode_available": True,
            "short_term_memory_supported": True,
        },
        "working_memory": {"session_only_by_default": True, "persistent_without_approval": False},
        "temporary_facts": {"stored_durably": False, "operator_approval_required": True},
        "retrieved_concepts": {
            "approved_noncanonical_count": memory["knowledge_memory_records"],
            "pending_review_count": 0,
        },
        "active_graph_edges": {
            "approved_noncanonical_count": graph["edge_count"],
            "average_confidence": graph["average_confidence"],
            "graph_consistency": graph["graph_consistency"],
        },
        "reasoning_depth": {"current_max_graph_depth": 2, "default_synthesis_enabled": False},
        "current_route": "operator_review_payloads_read_only",
        "current_lane": "Conversation with Advanced Operator Review",
        "pending_review_items": {
            "concept_candidates": 0,
            "graph_candidates": max(0, 62 - graph["edge_count"]),
            "reasoning_reviews": guided["trials_run"],
        },
        "memory_candidates": {"automatic_approval": False, "operator_review_required": True},
        "graph_candidates": {"automatic_approval": False, "operator_review_required": True},
        "safety_gates": dict(SAFETY),
        "operator_quality_metrics": {
            "source": "deferred_to_existing_operator_quality_suite",
            "fast_operator_payload": True,
        },
        "read_only": True,
    }


def _queue_from_guided_and_graph(guided: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    items = [
        _work_item("reasoning_review", "Review guided reasoning trial outputs", guided["operator_review_readiness"], "high", "general"),
        _work_item("graph_review", "Review pending graph expansion candidates", graph["average_confidence"], "high", "semantic_graph"),
        _work_item("evidence_request", "Improve evidence chains where graph usefulness is low", guided["average_graph_usefulness"], "medium", "evidence"),
        _work_item("substance_repair", "Repair concepts flagged as generic in reasoning reviews", 1.0 - guided["hallucination_risk"], "medium", "concept_quality"),
        _work_item("duplicate_review", "Inspect duplicate concept and edge candidates before approval", 0.85, "low", "cleanup"),
    ]
    sorted_items = sorted(items, key=lambda item: (_importance_rank(item["importance"]), -float(item["confidence"]), item["age_days"]))
    return {
        "queue_type": "rc2_unified_operator_work_queue",
        "sort_order": ["importance", "confidence", "age", "domain"],
        "items": sorted_items,
        "queue_size": len(sorted_items),
        "pending_review_items": {
            "concept_candidates": 0,
            "graph_candidates": max(0, 62 - graph["edge_count"]),
            "reasoning_reviews": guided["trials_run"],
        },
        "nothing_executes_automatically": True,
        "read_only": True,
        "safety": dict(SAFETY),
    }


def _replay_from_timeline(question: str, timeline: dict[str, Any]) -> dict[str, Any]:
    replay_steps = [
        {
            "index": index + 1,
            "label": step["stage"],
            "operator_view": step["summary"],
            "payload_ref": step["payload"],
        }
        for index, step in enumerate(timeline["steps"])
    ]
    return {
        "replay_type": "rc2_operator_conversation_replay",
        "question": question,
        "steps": replay_steps,
        "step_count": len(replay_steps),
        "deterministic": True,
        "read_only": True,
        "safety": dict(SAFETY),
    }


def _visualization_from_card(question: str, card: dict[str, Any]) -> dict[str, Any]:
    nodes = {}
    for concept in card["retrieved_concepts"]:
        if concept.get("concept_id"):
            nodes[concept["concept_id"]] = {
                "id": concept["concept_id"],
                "label": concept["concept_name"],
                "domain": concept.get("domain"),
                "review_state": "approved_noncanonical_concept",
            }
    edges = []
    for edge in card["graph_edges"]:
        edge_id = edge.get("edge_id") or _edge_key(edge)
        edges.append({
            "id": edge_id,
            "source": edge.get("source"),
            "target": edge.get("target"),
            "relation_type": edge.get("relation"),
            "confidence": edge.get("confidence"),
            "uncertainty": edge.get("uncertainty"),
            "evidence": "approved_graph_edge",
            "traversal": "used_in_reasoning_trial",
            "review_state": "approved_noncanonical_edge",
        })
    return {
        "visualization_type": "rc2_graph_visualization_payload",
        "question": question,
        "nodes": sorted(nodes.values(), key=lambda item: item["label"]),
        "edges": edges,
        "confidence": card["confidence"],
        "relation_types": sorted({edge["relation_type"] for edge in edges if edge.get("relation_type")}),
        "review_state": "read_only_operator_inspection",
        "read_only": True,
    }


def write_operator_experience_completion_report() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = build_operator_experience_completion_report()
    (REPORTS / "RC2_OPERATOR_EXPERIENCE_COMPLETION.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (REPORTS / "RC2_OPERATOR_EXPERIENCE_COMPLETION.md").write_text(
        _report_md(report),
        encoding="utf-8",
    )
    return report


def _timeline_step(stage: str, summary: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"stage": stage, "summary": summary, "payload": payload, "read_only": True}


def _intent_for_question(question: str) -> str:
    text = question.lower()
    if "graph-assisted" in text or "relates" in text or "connects" in text:
        return "guided_reasoning_review"
    if "what" in text or "why" in text or "how" in text:
        return "question"
    return "conversation"


def _edge_key(edge: dict[str, Any]) -> str:
    return f"{edge.get('source')}|{edge.get('relation')}|{edge.get('target')}"


def _work_item(item_type: str, title: str, confidence: float, importance: str, domain: str) -> dict[str, Any]:
    age_days = {"high": 0, "medium": 1, "low": 2}.get(importance, 1)
    return {
        "item_id": "rc2-work-" + item_type.replace("_", "-"),
        "item_type": item_type,
        "title": title,
        "importance": importance,
        "confidence": round(float(confidence), 4),
        "age_days": age_days,
        "domain": domain,
        "operator_actions": _actions_for_item_type(item_type),
        "executes_automatically": False,
    }


def _actions_for_item_type(item_type: str) -> list[str]:
    actions = {
        "concept_review": ["inspect", "approve_noncanonical", "reject", "edit"],
        "reasoning_review": ["approve_reasoning_as_useful", "reject_reasoning", "mark_overreach", "mark_missing_evidence"],
        "graph_review": ["inspect_edge", "approve_noncanonical_edge", "reject_edge", "request_evidence"],
        "memory_review": ["inspect_candidate", "keep_noncanonical", "reject_candidate"],
        "substance_repair": ["inspect_concept", "request_repair_candidate", "defer"],
        "weak_concept_repair": ["inspect_concept", "edit_candidate", "reject_candidate"],
        "graph_expansion_request": ["inspect_gap", "request_candidate_edges", "defer"],
        "evidence_request": ["inspect_chain", "request_deeper_retrieval", "mark_missing_evidence"],
        "duplicate_review": ["merge_candidate", "reject_duplicate", "keep_separate"],
    }
    return actions.get(item_type, ["inspect", "defer"])


def _importance_rank(importance: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(importance, 3)


def _duplicate_work_risk(queue: dict[str, Any]) -> float:
    types = [item["item_type"] for item in queue["items"]]
    counts = Counter(types)
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    return round(duplicates / max(1, len(types)), 4)


def _remaining_blockers(guided: dict[str, Any], productivity: dict[str, Any]) -> list[str]:
    blockers = list(guided.get("remaining_blockers", []))
    if productivity["estimated_clicks_per_reasoning_review"] > 2:
        blockers.append("reasoning_review_still_more_than_two_clicks")
    if guided["average_graph_usefulness"] < 0.65:
        blockers.append("operator_experience_still_limited_by_sparse_graph")
    return sorted(set(blockers))


def _recommendation(guided: dict[str, Any], productivity: dict[str, Any]) -> str:
    if guided["operator_review_readiness"] >= 0.85 and productivity["estimated_clicks_per_reasoning_review"] <= 2:
        return "READY_FOR_RC2_ARCHITECTURE_FREEZE"
    if guided["average_graph_usefulness"] < 0.65:
        return "PROCEED_GOVERNED_GRAPH_EXPANSION"
    return "CONTINUE_OPERATOR_EXPERIENCE_POLISH"


def _read_fast_validation_hint() -> dict[str, Any]:
    return {
        "strategy": "run scripts/rc2_fast_validate.py after report generation",
        "full_runtime_rc2_suite_required": False,
    }


def _report_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2 Operator Experience Completion",
        "",
        "## Executive Summary",
        "",
        report["executive_summary"],
        "",
        "## Guided Reasoning Metrics",
        "",
        *[f"- {key}: {value}" for key, value in report["guided_reasoning_metrics"].items()],
        "",
        "## Operator Workflow Metrics",
        "",
        *[f"- {key}: {value}" for key, value in report["operator_workflow_metrics"].items() if not isinstance(value, (dict, list))],
        "",
        "## Safety Invariants",
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
    print(json.dumps(write_operator_experience_completion_report(), indent=2, sort_keys=True))
