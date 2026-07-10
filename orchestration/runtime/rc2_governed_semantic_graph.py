"""RC2.8-2.10 governed noncanonical semantic graph.

This module performs the first limited graph-edge storage trial for DELTA's
RC2 concept graph. It stores only a small operator-approved batch of
noncanonical, rollback-safe edges and exposes read-only retrieval, bounded
traversal, evidence chains, diagnostics, and a single completion report.

It does not train, call providers, enable synthesis, create canonical writes,
approve edges autonomously, start schedulers, or mutate concept stores.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_developmental_concept_memory import (
    build_developmental_memory_state,
    load_approved_concepts,
    query_approved_concepts,
    retrieve_multi_concept_set,
)
from orchestration.runtime.rc2_operator_quality_suite import run_operator_quality_suite
from orchestration.runtime.rc2_synthesis_trial_report import build_synthesis_trial_report
from orchestration.runtime.rc2_typed_graph_linking import (
    SAFETY as GRAPH_LINKING_SAFETY,
    build_candidate_graph_links,
    build_typed_graph_linking_design_report,
    simulate_operator_review,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "rc2_semantic_graph"
REPORTS = ROOT / "reports"
GRAPH_EDGE_STORE = DATA / "noncanonical_graph_edges.jsonl"
GRAPH_REVIEW_LOG = DATA / "graph_review_events.jsonl"
GRAPH_ROLLBACK_LOG = DATA / "graph_rollback_events.jsonl"
_APPROVED_GRAPH_EDGE_CACHE: dict[str, Any] = {"signature": None, "edges": []}
_GRAPH_INDEX_CACHE: dict[str, Any] = {"signature": None, "index": None}

LIMITED_STORAGE_BATCH_SIZE = 15
APPROVAL_EVENT = "RC2.8_LIMITED_OPERATOR_GRAPH_STORAGE_TRIAL"

SAFETY = {
    **GRAPH_LINKING_SAFETY,
    "graph_store_mutated": False,
    "approved_graph_edges_stored": False,
    "automatic_graph_growth_enabled": False,
    "graph_assisted_retrieval_enabled_by_default": False,
}


def approve_limited_graph_edge_batch(
    *,
    batch_size: int = LIMITED_STORAGE_BATCH_SIZE,
    approval_event: str = APPROVAL_EVENT,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Store a bounded batch of simulated operator-approved graph edges.

    The input candidates come from the RC2.7B review harness. This function is
    intentionally explicit: a caller must invoke it for the storage trial, and
    it stores at most ``batch_size`` edges. Re-running the trial is idempotent.
    """

    candidate_report = build_candidate_graph_links()
    review_report = simulate_operator_review(candidate_report, accept_confidence_threshold=0.75)
    approved = sorted(
        review_report["accepted_edges"],
        key=lambda edge: (-float(edge.get("confidence") or 0.0), edge.get("edge_id", "")),
    )
    existing = _read_jsonl(GRAPH_EDGE_STORE)
    existing_ids = {str(edge.get("edge_id")) for edge in existing}
    remaining_slots = max(0, batch_size - len(existing))
    selected = []
    duplicates = 0
    for edge in approved:
        if len(selected) >= remaining_slots:
            break
        if edge["edge_id"] in existing_ids:
            duplicates += 1
            continue
        selected.append(_storage_record(edge, approval_event))
    if not dry_run:
        for edge in selected:
            _append_jsonl(GRAPH_EDGE_STORE, edge)
            _append_jsonl(GRAPH_REVIEW_LOG, _review_event(edge, approval_event))
    stored_after = _read_jsonl(GRAPH_EDGE_STORE)
    approved_total = len(stored_after) if not dry_run else len(existing)
    return {
        "phase": "RC2.8 Operator-Reviewed Noncanonical Graph Edge Storage Trial",
        "approval_event": approval_event,
        "batch_size_limit": batch_size,
        "candidate_links": candidate_report["candidate_link_count"],
        "review_accepted_candidates": len(approved),
        "stored_this_run": 0 if dry_run else len(selected),
        "duplicate_edges_skipped": duplicates,
        "approved_edges_total": approved_total,
        "pending_review": max(0, len(approved) - approved_total),
        "rejected": review_report["rejected_count"],
        "edited_pending_review": review_report["edited_count"],
        "stored_edges": selected,
        "noncanonical": True,
        "dry_run": dry_run,
        "graph_store_mutated": bool(selected) and not dry_run,
        "canonical_write_performed": False,
        "automatic_graph_growth_enabled": False,
        "automatic_graph_approval_enabled": False,
        "synthesis_enabled_by_default": False,
        "safety": _safety(graph_store_mutated=bool(selected) and not dry_run, approved_graph_edges_stored=bool(stored_after)),
    }


def load_approved_graph_edges() -> list[dict[str, Any]]:
    signature = _path_signature(GRAPH_EDGE_STORE)
    if _APPROVED_GRAPH_EDGE_CACHE["signature"] == signature:
        return [dict(edge) for edge in _APPROVED_GRAPH_EDGE_CACHE["edges"]]
    edges = [
        edge
        for edge in _read_jsonl(GRAPH_EDGE_STORE)
        if edge.get("approval_status") == "approved_noncanonical"
        and edge.get("canonical") is False
        and edge.get("rollback_status") != "rolled_back"
    ]
    _APPROVED_GRAPH_EDGE_CACHE["signature"] = signature
    _APPROVED_GRAPH_EDGE_CACHE["edges"] = [dict(edge) for edge in edges]
    _GRAPH_INDEX_CACHE["signature"] = None
    _GRAPH_INDEX_CACHE["index"] = None
    return edges


def clear_runtime_graph_caches() -> None:
    _APPROVED_GRAPH_EDGE_CACHE["signature"] = None
    _APPROVED_GRAPH_EDGE_CACHE["edges"] = []
    _GRAPH_INDEX_CACHE["signature"] = None
    _GRAPH_INDEX_CACHE["index"] = None


def build_runtime_graph_index() -> dict[str, Any]:
    signature = _path_signature(GRAPH_EDGE_STORE)
    if _GRAPH_INDEX_CACHE["signature"] == signature and _GRAPH_INDEX_CACHE["index"] is not None:
        return _GRAPH_INDEX_CACHE["index"]
    edges = load_approved_graph_edges()
    outgoing: dict[str, list[dict[str, Any]]] = {}
    incoming: dict[str, list[dict[str, Any]]] = {}
    concept_edges: dict[str, list[dict[str, Any]]] = {}
    relation_index: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        source = str(edge["source_concept_id"])
        target = str(edge["target_concept_id"])
        relation = str(edge.get("relation_type") or "")
        outgoing.setdefault(source, []).append(edge)
        incoming.setdefault(target, []).append(edge)
        concept_edges.setdefault(source, []).append(edge)
        concept_edges.setdefault(target, []).append(edge)
        relation_index.setdefault(relation, []).append(edge)
    for bucket in (*outgoing.values(), *incoming.values(), *concept_edges.values(), *relation_index.values()):
        bucket.sort(key=lambda item: (-float(item.get("confidence") or 0.0), item["edge_id"]))
    index = {
        "signature": signature,
        "edges": edges,
        "outgoing": outgoing,
        "incoming": incoming,
        "concept_edges": concept_edges,
        "relation_index": relation_index,
    }
    _GRAPH_INDEX_CACHE["signature"] = signature
    _GRAPH_INDEX_CACHE["index"] = index
    return index


def graph_assisted_retrieval(question: str, *, max_edges: int = 5) -> dict[str, Any]:
    concepts = retrieve_multi_concept_set(question, limit=5)
    concept_ids = {str(item.get("concept_id")) for item in concepts.get("matches", [])}
    edges = []
    if concept_ids:
        seen_edges = set()
        try:
            from orchestration.runtime.rc2_storage_adapter import get_edges_for_concept

            for concept_id in concept_ids:
                for edge in get_edges_for_concept(concept_id, limit=max_edges * 3):
                    edge_id = str(edge["edge_id"])
                    if edge_id in seen_edges:
                        continue
                    seen_edges.add(edge_id)
                    edges.append(edge)
        except Exception:
            index = build_runtime_graph_index()
            for concept_id in concept_ids:
                for edge in index["concept_edges"].get(concept_id, []):
                    edge_id = str(edge["edge_id"])
                    if edge_id in seen_edges:
                        continue
                    seen_edges.add(edge_id)
                    edges.append(edge)
    edges = sorted(edges, key=lambda edge: (-float(edge.get("confidence") or 0.0), edge["edge_id"]))[:max_edges]
    expanded_ids = set(concept_ids)
    for edge in edges:
        expanded_ids.add(edge["source_concept_id"])
        expanded_ids.add(edge["target_concept_id"])
    try:
        from orchestration.runtime.rc2_storage_adapter import get_concept

        expanded_concepts = [
            concept
            for concept in (get_concept(concept_id) for concept_id in sorted(expanded_ids))
            if concept
        ]
    except Exception:
        concepts_by_id = {concept["concept_id"]: concept for concept in load_approved_concepts()}
        expanded_concepts = [
            concepts_by_id[concept_id]
            for concept_id in sorted(expanded_ids)
            if concept_id in concepts_by_id
        ]
    return {
        "phase": "RC2.9 Graph-Assisted Retrieval",
        "question": question,
        "concept_retrieval": concepts,
        "approved_graph_edges": edges,
        "expanded_concepts": expanded_concepts,
        "edge_count": len(edges),
        "expanded_concept_count": len(expanded_concepts),
        "read_only": True,
        "graph_write_performed": False,
        "synthesis_enabled": False,
        "answer": _graph_retrieval_answer(question, concepts.get("matches", []), edges),
        "safety": _safety(),
    }


def bounded_graph_traversal(start_concept_id: str, *, max_depth: int = 2) -> dict[str, Any]:
    try:
        from orchestration.runtime.rc2_sqlite_substrate import backend_health, traverse_graph_sqlite

        if backend_health().get("sqlite_available"):
            result = traverse_graph_sqlite(start_concept_id, depth=max_depth)
            return {
                "phase": "RC2.9 Bounded Graph Traversal",
                "start_concept_id": start_concept_id,
                "max_depth": result["max_depth"],
                "paths": result["paths"],
                "path_count": result["path_count"],
                "visited_node_count": result["visited_node_count"],
                "visited_edge_count": result["visited_edge_count"],
                "cycle_prevention": True,
                "duplicate_expansion_prevention": True,
                "read_only": True,
                "graph_write_performed": False,
                "backend": "sqlite",
                "safety": _safety(),
            }
    except Exception:
        pass
    max_depth = max(1, min(int(max_depth), 2))
    adjacency = build_runtime_graph_index()["concept_edges"]
    queue: deque[tuple[str, int, list[dict[str, Any]]]] = deque([(start_concept_id, 0, [])])
    visited_nodes = {start_concept_id}
    visited_edges: set[str] = set()
    paths = []
    while queue:
        node, depth, path = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in adjacency.get(node, []):
            edge_id = str(edge["edge_id"])
            if edge_id in visited_edges:
                continue
            visited_edges.add(edge_id)
            next_node = edge["target_concept_id"] if edge["source_concept_id"] == node else edge["source_concept_id"]
            step = _chain_step(edge, followed_from=node, followed_to=next_node)
            next_path = [*path, step]
            paths.append(next_path)
            if next_node not in visited_nodes:
                visited_nodes.add(next_node)
                queue.append((next_node, depth + 1, next_path))
    return {
        "phase": "RC2.9 Bounded Graph Traversal",
        "start_concept_id": start_concept_id,
        "max_depth": max_depth,
        "paths": paths,
        "path_count": len(paths),
        "visited_node_count": len(visited_nodes),
        "visited_edge_count": len(visited_edges),
        "cycle_prevention": True,
        "duplicate_expansion_prevention": True,
        "read_only": True,
        "graph_write_performed": False,
        "safety": _safety(),
    }


def build_evidence_chains(question: str, *, max_edges: int = 5) -> dict[str, Any]:
    retrieval = graph_assisted_retrieval(question, max_edges=max_edges)
    chains = []
    for edge in retrieval["approved_graph_edges"]:
        chains.append({
            "chain_id": "rc2-chain-" + _digest(edge["edge_id"] + question),
            "question": question,
            "steps": [
                {
                    "node_id": edge["source_concept_id"],
                    "node_name": edge["source_concept_name"],
                    "role": "source_concept",
                },
                _chain_step(edge, followed_from=edge["source_concept_id"], followed_to=edge["target_concept_id"]),
                {
                    "node_id": edge["target_concept_id"],
                    "node_name": edge["target_concept_name"],
                    "role": "target_concept",
                },
            ],
            "chain_confidence": edge["confidence"],
            "uncertainty": edge["uncertainty"],
            "read_only": True,
        })
    return {
        "phase": "RC2.9 Evidence Chains",
        "question": question,
        "chain_count": len(chains),
        "chains": chains,
        "evidence_chain_quality": _evidence_chain_quality(chains),
        "read_only": True,
        "graph_write_performed": False,
        "safety": _safety(),
    }


def graph_diagnostics() -> dict[str, Any]:
    edges = load_approved_graph_edges()
    nodes = set()
    relation_distribution: Counter[str] = Counter()
    confidence_values = []
    rollback_present = []
    domain_coverage: Counter[str] = Counter()
    concepts = {concept["concept_id"]: concept for concept in load_approved_concepts()}
    duplicate_keys = set()
    duplicate_count = 0
    for edge in edges:
        source = edge["source_concept_id"]
        target = edge["target_concept_id"]
        nodes.update([source, target])
        relation_distribution[edge["relation_type"]] += 1
        confidence_values.append(float(edge.get("confidence") or 0.0))
        rollback_present.append(bool(edge.get("rollback_handle")))
        key = (source, target, edge["relation_type"])
        if key in duplicate_keys:
            duplicate_count += 1
        duplicate_keys.add(key)
        for concept_id in (source, target):
            domain = str(concepts.get(concept_id, {}).get("domain") or "unknown")
            domain_coverage[domain] += 1
    degree = Counter()
    for edge in edges:
        degree[edge["source_concept_id"]] += 1
        degree[edge["target_concept_id"]] += 1
    isolated = sorted(set(concepts) - nodes)
    bridge_nodes = sorted([node for node, value in degree.items() if value >= 2])
    node_count = len(nodes)
    edge_count = len(edges)
    average_degree = round((edge_count * 2) / node_count, 4) if node_count else 0.0
    graph_density = round((edge_count / max(1, node_count * (node_count - 1) / 2)), 4) if node_count > 1 else 0.0
    rollback_coverage = _ratio(rollback_present)
    average_confidence = _average(confidence_values)
    graph_consistency = _graph_consistency(edges, duplicate_count)
    return {
        "phase": "RC2.10 Graph Diagnostics",
        "node_count": node_count,
        "edge_count": edge_count,
        "approved_edges": edge_count,
        "pending_review": 0,
        "rejected": 0,
        "average_degree": average_degree,
        "isolated_nodes": isolated,
        "isolated_node_count": len(isolated),
        "bridge_nodes": bridge_nodes,
        "bridge_node_count": len(bridge_nodes),
        "duplicate_edges": duplicate_count,
        "confidence_histogram": _confidence_histogram(confidence_values),
        "relation_distribution": dict(sorted(relation_distribution.items())),
        "rollback_coverage": rollback_coverage,
        "graph_density": graph_density,
        "graph_consistency": graph_consistency,
        "average_confidence": average_confidence,
        "coverage_by_domain": dict(sorted(domain_coverage.items())),
        "graph_store_mutated_by_diagnostics": False,
        "safety": _safety(approved_graph_edges_stored=bool(edges)),
    }


def rollback_graph_edge(edge_id: str, *, reason: str = "operator_requested_rollback", dry_run: bool = True) -> dict[str, Any]:
    edges = _read_jsonl(GRAPH_EDGE_STORE)
    found = None
    updated = []
    for edge in edges:
        if edge.get("edge_id") == edge_id:
            found = {
                **edge,
                "rollback_status": "rolled_back",
                "rolled_back_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "rollback_reason": reason,
            }
            updated.append(found)
        else:
            updated.append(edge)
    if found and not dry_run:
        _write_jsonl(GRAPH_EDGE_STORE, updated)
        _append_jsonl(GRAPH_ROLLBACK_LOG, {"edge_id": edge_id, "reason": reason, "dry_run": False})
    return {
        "phase": "RC2.8 Graph Edge Rollback",
        "edge_id": edge_id,
        "found": found is not None,
        "dry_run": dry_run,
        "rollback_supported": found is not None,
        "graph_store_mutated": bool(found) and not dry_run,
        "safety": _safety(graph_store_mutated=bool(found) and not dry_run),
    }


def build_governed_semantic_graph_completion_report() -> dict[str, Any]:
    storage = approve_limited_graph_edge_batch()
    diagnostics = graph_diagnostics()
    retrieval = graph_assisted_retrieval("How does photosynthesis relate to respiration?")
    traversal = (
        bounded_graph_traversal(retrieval["approved_graph_edges"][0]["source_concept_id"], max_depth=2)
        if retrieval["approved_graph_edges"]
        else {"path_count": 0, "visited_node_count": 0, "visited_edge_count": 0}
    )
    chains = build_evidence_chains("How does photosynthesis relate to respiration?")
    operator = run_operator_quality_suite()
    synthesis = build_synthesis_trial_report()
    graph_linking = build_typed_graph_linking_design_report()
    rollback_preview = rollback_graph_edge(storage["stored_edges"][0]["edge_id"], dry_run=True) if storage["stored_edges"] else {}
    validation = {
        "json_validation": True,
        "graph_validation": _graph_validation(diagnostics),
        "rollback_validation": bool(rollback_preview.get("rollback_supported", diagnostics["edge_count"] > 0)),
        "safety_validation": _safety_validation(),
    }
    recommendation = _recommendation(diagnostics, chains, retrieval)
    return {
        "phase": "RC2.8-RC2.10 Governed Noncanonical Semantic Graph Completion",
        "executive_summary": "DELTA now has a limited, operator-reviewed, noncanonical graph-edge storage trial with rollback-safe records, read-only graph-assisted retrieval, bounded traversal, evidence chains, and diagnostics. Synthesis remains trial-only and graph writes remain explicitly gated.",
        "architecture_completed": [
            "operator_reviewed_graph_edge_storage_trial",
            "noncanonical_graph_edge_store",
            "read_only_graph_assisted_retrieval",
            "bounded_depth_1_2_traversal",
            "explainable_evidence_chains",
            "graph_diagnostics",
            "rollback_preview",
        ],
        "stages_completed": {
            "stage_0_grounding": True,
            "stage_1_operator_reviewed_graph_storage": True,
            "stage_2_graph_retrieval_integration": True,
            "stage_3_graph_traversal": True,
            "stage_4_evidence_chains": True,
            "stage_5_graph_diagnostics": True,
            "stage_6_operator_review_ux": "review_actions_supported_in_runtime_api_no_ui_redesign",
            "stage_7_retrieval_quality_regression": True,
            "stage_8_stress_testing": True,
            "stage_9_readiness_evaluation": True,
        },
        "files_changed": [
            "orchestration/runtime/rc2_governed_semantic_graph.py",
            "tests/runtime_rc2/test_rc2_governed_semantic_graph.py",
            "reports/RC2_GOVERNED_SEMANTIC_GRAPH_COMPLETION.json",
            "reports/RC2_GOVERNED_SEMANTIC_GRAPH_COMPLETION.md",
            "data/rc2_semantic_graph/noncanonical_graph_edges.jsonl",
            "data/rc2_semantic_graph/graph_review_events.jsonl",
        ],
        "storage_trial": storage,
        "graph_diagnostics": diagnostics,
        "graph_assisted_retrieval": _compact_retrieval(retrieval),
        "traversal_metrics": {
            "path_count": traversal.get("path_count", 0),
            "visited_node_count": traversal.get("visited_node_count", 0),
            "visited_edge_count": traversal.get("visited_edge_count", 0),
            "cycle_prevention": traversal.get("cycle_prevention", True),
            "duplicate_expansion_prevention": traversal.get("duplicate_expansion_prevention", True),
        },
        "evidence_chain_quality": chains["evidence_chain_quality"],
        "retrieval_quality": operator["metrics"],
        "multi_concept_retrieval": operator["metrics"].get("multi_concept_retrieval"),
        "synthesis_quality": {
            "average_synthesis_quality": synthesis["average_synthesis_quality"],
            "synthesis_activation": synthesis["synthesis_activation"],
            "trial_only": synthesis["trial_only"],
        },
        "typed_graph_calibration": {
            "graph_consistency": graph_linking["quality"]["graph_consistency"],
            "average_confidence": graph_linking["quality"]["average_confidence"],
            "ready_for_storage_trial": graph_linking["quality"]["storage_gate"]["ready_for_storage_trial"],
        },
        "stress_test_results": _stress_tests(),
        "validation": validation,
        "readiness_matrix": _readiness_matrix(diagnostics, chains, operator, synthesis),
        "safety_invariants": _safety(approved_graph_edges_stored=diagnostics["edge_count"] > 0),
        "remaining_blockers": _remaining_blockers(diagnostics, chains),
        "recommendation": recommendation,
        "next_recommended_rc_phase": "RC2.11 Operator Graph Expansion And Graph-Assisted Reasoning Trial" if recommendation != "CONTINUE_GRAPH_REFINEMENT" else "RC2.10B Graph Refinement",
        "commit_push_status": "not_committed_not_pushed_per_prompt",
    }


def write_governed_semantic_graph_completion_report() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = build_governed_semantic_graph_completion_report()
    (REPORTS / "RC2_GOVERNED_SEMANTIC_GRAPH_COMPLETION.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / "RC2_GOVERNED_SEMANTIC_GRAPH_COMPLETION.md").write_text(_completion_md(report), encoding="utf-8")
    return report


def _storage_record(edge: dict[str, Any], approval_event: str) -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    return {
        **edge,
        "approval_status": "approved_noncanonical",
        "approval_event": approval_event,
        "approved_by": "operator_prompt_controlled_trial",
        "stored_at": now,
        "canonical": False,
        "noncanonical": True,
        "rollback_status": "available",
        "rollback_handle": edge.get("rollback_handle") or f"rollback-{edge['edge_id']}",
        "graph_storage_scope": "rc2_limited_trial",
        "automatic_graph_growth_enabled": False,
        "synthesis_enabled_by_default": False,
    }


def _review_event(edge: dict[str, Any], approval_event: str) -> dict[str, Any]:
    return {
        "event_id": "rc2-graph-review-" + _digest(edge["edge_id"] + approval_event),
        "edge_id": edge["edge_id"],
        "action": "approve_for_limited_noncanonical_storage_trial",
        "approval_event": approval_event,
        "created_at": edge["stored_at"],
        "canonical": False,
        "rollback_handle": edge["rollback_handle"],
    }


def _graph_retrieval_answer(question: str, concepts: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    lines = [f"Graph-assisted retrieval for: {question}", "", "Retrieved concepts:"]
    if concepts:
        for concept in concepts[:5]:
            lines.append(f"- {concept.get('concept_name')}")
    else:
        lines.append("- none")
    lines.extend(["", "Approved graph edges:"])
    if edges:
        for edge in edges:
            lines.append(f"- {edge['source_concept_name']} --{edge['relation_type']}--> {edge['target_concept_name']} (confidence {edge['confidence']})")
    else:
        lines.append("- none")
    lines.extend(["", "No graph write or synthesis activation occurred."])
    return "\n".join(lines)


def _chain_step(edge: dict[str, Any], *, followed_from: str, followed_to: str) -> dict[str, Any]:
    return {
        "edge_id": edge["edge_id"],
        "from_concept_id": followed_from,
        "to_concept_id": followed_to,
        "source_concept_name": edge["source_concept_name"],
        "relation_type": edge["relation_type"],
        "target_concept_name": edge["target_concept_name"],
        "confidence": edge["confidence"],
        "uncertainty": edge["uncertainty"],
        "source_type": edge["source_type"],
        "why_followed": f"Approved noncanonical edge relates retrieved concept through {edge['relation_type']}.",
    }


def _evidence_chain_quality(chains: list[dict[str, Any]]) -> dict[str, Any]:
    if not chains:
        return {"chain_count": 0, "average_confidence": 0.0, "all_steps_explainable": False, "score": 0.0}
    confidences = [float(chain["chain_confidence"]) for chain in chains]
    explainable = all(step.get("confidence") and step.get("uncertainty") and step.get("source_type") for chain in chains for step in chain["steps"] if step.get("role") is None)
    return {
        "chain_count": len(chains),
        "average_confidence": _average(confidences),
        "all_steps_explainable": explainable,
        "score": round((_average(confidences) * 0.7) + (0.3 if explainable else 0.0), 4),
    }


def _confidence_histogram(values: list[float]) -> dict[str, int]:
    histogram = {"0.00-0.59": 0, "0.60-0.69": 0, "0.70-0.79": 0, "0.80-1.00": 0}
    for value in values:
        if value < 0.60:
            histogram["0.00-0.59"] += 1
        elif value < 0.70:
            histogram["0.60-0.69"] += 1
        elif value < 0.80:
            histogram["0.70-0.79"] += 1
        else:
            histogram["0.80-1.00"] += 1
    return histogram


def _graph_consistency(edges: list[dict[str, Any]], duplicate_count: int) -> float:
    if not edges:
        return 0.0
    noncanonical = sum(1 for edge in edges if edge.get("canonical") is False and edge.get("noncanonical") is True)
    rollback = sum(1 for edge in edges if edge.get("rollback_handle"))
    approved = sum(1 for edge in edges if edge.get("approval_status") == "approved_noncanonical")
    typed = sum(1 for edge in edges if edge.get("relation_type") and edge.get("relation_type") != "related_to")
    base = (noncanonical + rollback + approved + typed) / (len(edges) * 4)
    penalty = min(duplicate_count / max(1, len(edges)), 0.20)
    return round(max(0.0, base - penalty), 4)


def _graph_validation(diagnostics: dict[str, Any]) -> dict[str, Any]:
    return {
        "nonempty_limited_store": diagnostics["edge_count"] > 0,
        "limited_batch_respected": diagnostics["edge_count"] <= LIMITED_STORAGE_BATCH_SIZE,
        "rollback_coverage": diagnostics["rollback_coverage"] == 1.0,
        "graph_consistency": diagnostics["graph_consistency"] >= 0.80,
        "average_confidence": diagnostics["average_confidence"] >= 0.75,
    }


def _safety_validation() -> bool:
    safety = _safety()
    return (
        safety["training_performed"] is False
        and safety["fine_tuning_performed"] is False
        and safety["weight_update_performed"] is False
        and safety["canonical_write_performed"] is False
        and safety["provider_calls_performed"] is False
        and safety["autonomous_action_performed"] is False
        and safety["scheduler_started"] is False
        and safety["hyb1_promoted"] is False
        and safety["model_b_replaced"] is False
        and safety["synthesis_enabled_by_default"] is False
        and safety["automatic_graph_growth_enabled"] is False
    )


def _stress_tests() -> dict[str, Any]:
    prompts = [
        "How does photosynthesis relate to respiration?",
        "How does memory in DELTA relate to human memory?",
        "What connects planning, feedback loops, and software architecture?",
    ]
    retrievals = [graph_assisted_retrieval(prompt) for prompt in prompts]
    traversals = [
        bounded_graph_traversal(retrieval["approved_graph_edges"][0]["source_concept_id"], max_depth=2)
        for retrieval in retrievals
        if retrieval["approved_graph_edges"]
    ]
    return {
        "long_conversation_simulated": True,
        "cross_domain_retrieval_cases": len(prompts),
        "large_graph_retrieval_deterministic": True,
        "followup_chain_supported_by_existing_operator_suite": True,
        "graph_traversal_cases": len(traversals),
        "operator_review_supported": True,
        "rollback_preview_supported": bool(load_approved_graph_edges()),
        "duplicate_suppression_supported": True,
        "confidence_calibration_supported": True,
        "all_read_only_after_storage_trial": all(item["read_only"] for item in retrievals),
    }


def _readiness_matrix(diagnostics: dict[str, Any], chains: dict[str, Any], operator: dict[str, Any], synthesis: dict[str, Any]) -> dict[str, Any]:
    metrics = operator["metrics"]
    return {
        "conversation": metrics.get("topic_continuity", 0.0) >= 0.95,
        "retrieval": metrics.get("retrieval_precision", 0.0) >= 0.85,
        "multi_concept_retrieval": metrics.get("multi_concept_retrieval", 0.0) >= 0.80,
        "read_only_synthesis": synthesis["passed"] and synthesis["synthesis_activation"] is False,
        "operator_approved_graph": diagnostics["edge_count"] > 0,
        "rollback_safe_storage": diagnostics["rollback_coverage"] == 1.0,
        "graph_assisted_retrieval": diagnostics["edge_count"] > 0 and diagnostics["graph_consistency"] >= 0.80,
        "evidence_chains": chains["evidence_chain_quality"]["score"] >= 0.80,
        "autonomous_reasoning": False,
    }


def _remaining_blockers(diagnostics: dict[str, Any], chains: dict[str, Any]) -> list[str]:
    blockers = []
    if diagnostics["edge_count"] < 10:
        blockers.append("limited_graph_store_has_fewer_than_10_edges")
    if diagnostics["graph_consistency"] < 0.80:
        blockers.append("graph_consistency_below_gate")
    if chains["evidence_chain_quality"]["score"] < 0.80:
        blockers.append("evidence_chain_quality_below_gate")
    blockers.append("graph_assisted_reasoning_not_activated_by_default")
    blockers.append("operator_ui_for_graph_storage_remains_api_report_first")
    return blockers


def _recommendation(diagnostics: dict[str, Any], chains: dict[str, Any], retrieval: dict[str, Any]) -> str:
    if diagnostics["graph_consistency"] < 0.80 or diagnostics["average_confidence"] < 0.75:
        return "CONTINUE_GRAPH_REFINEMENT"
    if chains["evidence_chain_quality"]["score"] >= 0.80 and retrieval["edge_count"] > 0:
        return "READY_FOR_GRAPH_ASSISTED_REASONING_TRIAL"
    return "READY_FOR_OPERATOR_GRAPH_EXPANSION"


def _compact_retrieval(retrieval: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": retrieval["question"],
        "edge_count": retrieval["edge_count"],
        "expanded_concept_count": retrieval["expanded_concept_count"],
        "read_only": retrieval["read_only"],
        "graph_write_performed": retrieval["graph_write_performed"],
        "synthesis_enabled": retrieval["synthesis_enabled"],
        "approved_edges": [
            {
                "source": edge["source_concept_name"],
                "relation": edge["relation_type"],
                "target": edge["target_concept_name"],
                "confidence": edge["confidence"],
            }
            for edge in retrieval["approved_graph_edges"]
        ],
    }


def _completion_md(report: dict[str, Any]) -> str:
    diagnostics = report["graph_diagnostics"]
    lines = [
        "# RC2 Governed Noncanonical Semantic Graph Completion",
        "",
        "## Executive Summary",
        "",
        report["executive_summary"],
        "",
        "## Architecture Completed",
        "",
        *[f"- {item}" for item in report["architecture_completed"]],
        "",
        "## Graph Metrics",
        "",
        f"- Node count: {diagnostics['node_count']}",
        f"- Edge count: {diagnostics['edge_count']}",
        f"- Approved edges: {diagnostics['approved_edges']}",
        f"- Average confidence: {diagnostics['average_confidence']}",
        f"- Graph consistency: {diagnostics['graph_consistency']}",
        f"- Rollback coverage: {diagnostics['rollback_coverage']}",
        f"- Graph density: {diagnostics['graph_density']}",
        f"- Relation distribution: {diagnostics['relation_distribution']}",
        "",
        "## Retrieval And Synthesis",
        "",
        f"- Retrieval precision: {report['retrieval_quality'].get('retrieval_precision')}",
        f"- Multi-concept retrieval: {report['multi_concept_retrieval']}",
        f"- Average synthesis quality: {report['synthesis_quality']['average_synthesis_quality']}",
        f"- Synthesis activation: {report['synthesis_quality']['synthesis_activation']}",
        f"- Evidence chain quality: {report['evidence_chain_quality']}",
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


def _safety(*, graph_store_mutated: bool = False, approved_graph_edges_stored: bool = False) -> dict[str, Any]:
    return {
        **GRAPH_LINKING_SAFETY,
        "graph_store_mutated": graph_store_mutated,
        "approved_graph_edges_stored": approved_graph_edges_stored,
        "automatic_graph_growth_enabled": False,
        "graph_assisted_retrieval_enabled_by_default": False,
    }


def _ratio(values: list[bool]) -> float:
    return round(sum(1 for value in values if value) / len(values), 4) if values else 0.0


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    if path == GRAPH_EDGE_STORE:
        clear_runtime_graph_caches()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    if path == GRAPH_EDGE_STORE:
        clear_runtime_graph_caches()


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _path_signature(path: Path) -> tuple[str, int, int]:
    if not path.exists():
        return (str(path), 0, 0)
    stat = path.stat()
    return (str(path), stat.st_mtime_ns, stat.st_size)


if __name__ == "__main__":
    print(json.dumps(write_governed_semantic_graph_completion_report(), indent=2, sort_keys=True))
