"""RC2 DCM scalability readiness instrumentation.

This module measures and reports indexes, caches, graph analytics, retrieval
latency, graph traversal latency, and future scale readiness for the expanded
RC2 substrate. It is read-only and behavior-preserving.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any, Callable

from orchestration.runtime.rc2_developmental_concept_memory import (
    KNOWLEDGE_MEMORY_LOG,
    build_runtime_concept_index,
    load_approved_concepts,
    retrieve_multi_concept_set,
    retrieval_query_profile,
)
from orchestration.runtime.rc2_governed_semantic_graph import (
    GRAPH_EDGE_STORE,
    bounded_graph_traversal,
    build_runtime_graph_index,
    graph_assisted_retrieval,
    graph_diagnostics,
    load_approved_graph_edges,
)
from orchestration.runtime.rc2_graph_assisted_reasoning import run_cross_domain_reasoning_evaluation


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
    "synthesis_enabled_by_default": False,
    "knowledge_mutation_performed": False,
    "graph_mutation_performed": False,
}

PERFORMANCE_PROMPTS = [
    "How does photosynthesis relate to respiration?",
    "How does gravity relate to orbital motion?",
    "Compare inflation and interest rates.",
    "What connects planning, feedback loops, and software architecture?",
    "How does DELTA memory relate to human memory?",
]


class RuntimeRetrievalCache:
    """Small disposable query cache for performance measurement."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, query: str, loader: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        key = " ".join(query.lower().split())
        if key in self._cache:
            self.hits += 1
            return dict(self._cache[key])
        self.misses += 1
        value = loader()
        self._cache[key] = dict(value)
        return value

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 4) if total else 0.0


def build_concept_indexes(concepts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    concepts = concepts if concepts is not None else load_approved_concepts()
    by_id = {}
    by_name = {}
    by_domain: dict[str, list[dict[str, Any]]] = {}
    keyword_index: dict[str, list[str]] = {}
    related_index: dict[str, list[str]] = {}
    for concept in concepts:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            continue
        name = str(concept.get("concept_name") or "")
        domain = str(concept.get("domain") or "unknown")
        by_id[concept_id] = concept
        by_name[_normalize(name)] = concept
        by_domain.setdefault(domain, []).append(concept)
        terms = set(_tokens(name))
        terms.update(_tokens(concept.get("short_definition")))
        for item in concept.get("keywords", []) or []:
            terms.update(_tokens(item))
        for term in terms:
            keyword_index.setdefault(term, []).append(concept_id)
        for related in concept.get("related_concepts", []) or []:
            related_index.setdefault(_normalize(related), []).append(concept_id)
    return {
        "concept_count": len(concepts),
        "by_id": by_id,
        "by_normalized_name": by_name,
        "by_domain": by_domain,
        "keyword_index": keyword_index,
        "related_concept_index": related_index,
    }


def build_graph_indexes(edges: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if edges is None:
        graph_index = build_runtime_graph_index()
        return {
            "edge_count": len(graph_index["edges"]),
            "outgoing": graph_index["outgoing"],
            "incoming": graph_index["incoming"],
            "concept_to_edges": graph_index["concept_edges"],
            "relation_index": graph_index["relation_index"],
        }
    outgoing: dict[str, list[dict[str, Any]]] = {}
    incoming: dict[str, list[dict[str, Any]]] = {}
    concept_edges: dict[str, list[dict[str, Any]]] = {}
    relation_index: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        source = str(edge.get("source_concept_id") or "")
        target = str(edge.get("target_concept_id") or "")
        relation = str(edge.get("relation_type") or "")
        outgoing.setdefault(source, []).append(edge)
        incoming.setdefault(target, []).append(edge)
        concept_edges.setdefault(source, []).append(edge)
        concept_edges.setdefault(target, []).append(edge)
        relation_index.setdefault(relation, []).append(edge)
    return {
        "edge_count": len(edges),
        "outgoing": outgoing,
        "incoming": incoming,
        "concept_to_edges": concept_edges,
        "relation_index": relation_index,
    }


def benchmark_runtime_performance() -> dict[str, Any]:
    concept_load = _measure(load_approved_concepts)
    graph_load = _measure(load_approved_graph_edges)
    concept_index = _measure(build_runtime_concept_index)
    graph_index = _measure(build_graph_indexes)
    cache = RuntimeRetrievalCache()
    retrieval_timings = []
    cached_timings = []
    traversal_timings = []
    scan_lookup_timings = []
    indexed_lookup_timings = []
    for prompt in PERFORMANCE_PROMPTS:
        retrieval_timings.append(_measure(lambda p=prompt: retrieve_multi_concept_set(p))["elapsed_ms"])
        cached_timings.append(_measure(lambda p=prompt: cache.get(p, lambda: retrieve_multi_concept_set(p)))["elapsed_ms"])
        cached_timings.append(_measure(lambda p=prompt: cache.get(p, lambda: retrieve_multi_concept_set(p)))["elapsed_ms"])
        retrieval = graph_assisted_retrieval(prompt)
        concept_ids = {str(item.get("concept_id")) for item in retrieval.get("concept_retrieval", {}).get("matches", [])}
        scan_lookup_timings.append(_measure(lambda ids=concept_ids: _legacy_edge_scan(ids))["elapsed_ms"])
        indexed_lookup_timings.append(_measure(lambda ids=concept_ids: _indexed_edge_lookup(ids))["elapsed_ms"])
        if retrieval.get("approved_graph_edges"):
            start = retrieval["approved_graph_edges"][0]["source_concept_id"]
            traversal_timings.append(_measure(lambda s=start: bounded_graph_traversal(s, max_depth=2))["elapsed_ms"])
    retrieval_avg = _avg(retrieval_timings)
    cached_avg = _avg(cached_timings)
    scan_avg = _avg(scan_lookup_timings)
    indexed_avg = _avg(indexed_lookup_timings)
    traversal_avg = _avg(traversal_timings)
    return {
        "concept_load_time_ms": concept_load["elapsed_ms"],
        "graph_load_time_ms": graph_load["elapsed_ms"],
        "concept_index_build_time_ms": concept_index["elapsed_ms"],
        "graph_index_build_time_ms": graph_index["elapsed_ms"],
        "retrieval_latency_ms": retrieval_avg,
        "cached_retrieval_latency_ms": cached_avg,
        "retrieval_latency_improvement": _improvement(retrieval_avg, cached_avg),
        "legacy_edge_scan_latency_ms": scan_avg,
        "indexed_edge_lookup_latency_ms": indexed_avg,
        "graph_lookup_improvement": _improvement(scan_avg, indexed_avg),
        "graph_traversal_latency_ms": traversal_avg,
        "cache_hit_rate": cache.hit_rate,
        "cache_hits": cache.hits,
        "cache_misses": cache.misses,
        "memory_footprint_estimate": estimate_memory_footprint(),
    }


def graph_analytics() -> dict[str, Any]:
    concepts = load_approved_concepts()
    edges = load_approved_graph_edges()
    concepts_by_id = {concept["concept_id"]: concept for concept in concepts if concept.get("concept_id")}
    degree = Counter()
    relation_distribution = Counter()
    adjacency: dict[str, set[str]] = {}
    cross_domain_degree = Counter()
    for edge in edges:
        source = str(edge.get("source_concept_id") or "")
        target = str(edge.get("target_concept_id") or "")
        relation_distribution[str(edge.get("relation_type") or "")] += 1
        degree[source] += 1
        degree[target] += 1
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)
        source_domain = str((concepts_by_id.get(source) or {}).get("domain") or "")
        target_domain = str((concepts_by_id.get(target) or {}).get("domain") or "")
        if source_domain and target_domain and source_domain != target_domain:
            cross_domain_degree[source] += 1
            cross_domain_degree[target] += 1
    components = _connected_components(adjacency, set(concepts_by_id))
    hubs = [
        _concept_degree_row(concepts_by_id, concept_id, count)
        for concept_id, count in degree.most_common(25)
    ]
    bridges = [
        _concept_degree_row(concepts_by_id, concept_id, count)
        for concept_id, count in cross_domain_degree.most_common(25)
    ]
    return {
        "concept_count": len(concepts),
        "edge_count": len(edges),
        "degree_distribution": _degree_distribution(degree),
        "hub_concepts": hubs,
        "bridge_concepts": bridges,
        "isolated_concepts": max(0, len(concepts_by_id) - len(degree)),
        "connected_components": {
            "count": len(components),
            "largest": max((len(item) for item in components), default=0),
            "top_sizes": sorted((len(item) for item in components), reverse=True)[:10],
        },
        "average_path_length_estimate": _average_path_length_estimate(adjacency),
        "relation_distribution": dict(relation_distribution.most_common()),
        "domain_density": _domain_density(concepts, edges, concepts_by_id),
        "graph_density": _graph_density(len(concepts_by_id), len(edges)),
    }


def estimate_memory_footprint() -> dict[str, Any]:
    concept_size = KNOWLEDGE_MEMORY_LOG.stat().st_size if KNOWLEDGE_MEMORY_LOG.exists() else 0
    edge_size = GRAPH_EDGE_STORE.stat().st_size if GRAPH_EDGE_STORE.exists() else 0
    concepts = load_approved_concepts()
    edges = load_approved_graph_edges()
    return {
        "concept_jsonl_bytes": concept_size,
        "graph_jsonl_bytes": edge_size,
        "total_jsonl_bytes": concept_size + edge_size,
        "estimated_concept_index_bytes": len(concepts) * 700,
        "estimated_graph_index_bytes": len(edges) * 520,
        "estimate_method": "jsonl file size plus coarse per-record Python index estimate",
    }


def future_scale_readiness(performance: dict[str, Any], analytics: dict[str, Any]) -> dict[str, Any]:
    current_concepts = max(1, analytics["concept_count"])
    current_edges = max(1, analytics["edge_count"])
    retrieval = float(performance["retrieval_latency_ms"])
    traversal = float(performance["graph_traversal_latency_ms"])
    graph_lookup = float(performance["indexed_edge_lookup_latency_ms"])
    estimates = {}
    for target in (25_000, 50_000, 100_000, 250_000):
        concept_factor = target / current_concepts
        edge_factor = max(1.0, (target / current_concepts) * (current_edges / current_concepts))
        estimates[str(target)] = {
            "retrieval_latency_ms_if_scan_based": round(retrieval * concept_factor, 4),
            "retrieval_latency_ms_with_indexes_estimate": round(max(retrieval * 0.25, retrieval * (concept_factor ** 0.35)), 4),
            "graph_lookup_ms_with_adjacency_estimate": round(graph_lookup * min(edge_factor ** 0.20, 3.0), 4),
            "traversal_latency_ms_depth2_estimate": round(traversal * min(edge_factor ** 0.35, 5.0), 4),
            "readiness": _scale_readiness_label(target, performance),
        }
    return estimates


def build_dcm_scalability_readiness_report() -> dict[str, Any]:
    performance = benchmark_runtime_performance()
    analytics = graph_analytics()
    diagnostics = graph_diagnostics()
    reasoning = run_cross_domain_reasoning_evaluation()
    scale = future_scale_readiness(performance, analytics)
    return {
        "phase": "RC2.18-RC2.22 DCM Scalability Readiness",
        "executive_summary": "DELTA now has behavior-preserving concept caches, graph adjacency indexes, disposable retrieval cache instrumentation, graph analytics, and scale-readiness estimates over the expanded RC2 substrate.",
        "current_concept_count": analytics["concept_count"],
        "current_edge_count": analytics["edge_count"],
        "indexes_added": [
            "concept_id map",
            "normalized concept name map",
            "domain concept index",
            "keyword inverted index",
            "related concept index",
            "outgoing graph adjacency",
            "incoming graph adjacency",
            "concept-to-edge map",
            "relation index",
        ],
        "caches_added": [
            "approved concept JSONL signature cache",
            "approved graph edge JSONL signature cache",
            "runtime graph index signature cache",
            "disposable retrieval query cache",
        ],
        "performance": performance,
        "graph_analytics": analytics,
        "graph_diagnostics": diagnostics,
        "reasoning_quality": {
            "average_reasoning_quality": reasoning["average_reasoning_quality"],
            "average_graph_usefulness": reasoning["average_graph_usefulness"],
            "average_hallucination_risk": reasoning["average_hallucination_risk"],
            "average_overreach_risk": reasoning["average_overreach_risk"],
            "operator_review_readiness": reasoning["operator_review_readiness"],
        },
        "scalability_estimates": scale,
        "remaining_bottlenecks": _remaining_bottlenecks(performance, analytics),
        "safety_invariants": dict(SAFETY),
        "recommendation": _recommendation(performance, analytics),
        "commit_status": "not_committed_per_prompt",
        "push_status": "not_pushed_per_prompt",
    }


def write_dcm_scalability_readiness_report() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = build_dcm_scalability_readiness_report()
    (REPORTS / "RC2_DCM_SCALABILITY_READINESS.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / "RC2_DCM_SCALABILITY_READINESS.md").write_text(_report_md(report), encoding="utf-8")
    return report


def _legacy_edge_scan(concept_ids: set[str]) -> list[dict[str, Any]]:
    matches = []
    for edge in load_approved_graph_edges():
        if edge["source_concept_id"] in concept_ids or edge["target_concept_id"] in concept_ids:
            matches.append(edge)
    return sorted(matches, key=lambda edge: (-float(edge.get("confidence") or 0.0), edge["edge_id"]))[:5]


def _indexed_edge_lookup(concept_ids: set[str]) -> list[dict[str, Any]]:
    index = build_runtime_graph_index()
    matches = []
    seen = set()
    for concept_id in concept_ids:
        for edge in index["concept_edges"].get(concept_id, []):
            edge_id = str(edge["edge_id"])
            if edge_id in seen:
                continue
            seen.add(edge_id)
            matches.append(edge)
    return sorted(matches, key=lambda edge: (-float(edge.get("confidence") or 0.0), edge["edge_id"]))[:5]


def _measure(fn: Callable[[], Any]) -> dict[str, Any]:
    start = time.perf_counter()
    value = fn()
    elapsed = round((time.perf_counter() - start) * 1000, 4)
    return {"elapsed_ms": elapsed, "value": value}


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _improvement(before: float, after: float) -> float:
    if before <= 0:
        return 0.0
    return round(max(0.0, (before - after) / before), 4)


def _connected_components(adjacency: dict[str, set[str]], nodes: set[str]) -> list[set[str]]:
    remaining = set(nodes)
    components = []
    while remaining:
        start = remaining.pop()
        component = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for nxt in adjacency.get(node, set()):
                if nxt in remaining:
                    remaining.remove(nxt)
                    component.add(nxt)
                    queue.append(nxt)
        components.append(component)
    return components


def _average_path_length_estimate(adjacency: dict[str, set[str]]) -> float:
    starts = list(adjacency)[:30]
    distances = []
    for start in starts:
        seen = {start}
        queue = deque([(start, 0)])
        while queue:
            node, distance = queue.popleft()
            if 0 < distance <= 4:
                distances.append(distance)
            if distance >= 4:
                continue
            for nxt in adjacency.get(node, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, distance + 1))
    return _avg(distances)


def _degree_distribution(degree: Counter[str]) -> dict[str, int]:
    buckets = {"0": 0, "1": 0, "2-3": 0, "4-7": 0, "8-15": 0, "16+": 0}
    for value in degree.values():
        if value == 0:
            buckets["0"] += 1
        elif value == 1:
            buckets["1"] += 1
        elif value <= 3:
            buckets["2-3"] += 1
        elif value <= 7:
            buckets["4-7"] += 1
        elif value <= 15:
            buckets["8-15"] += 1
        else:
            buckets["16+"] += 1
    return buckets


def _concept_degree_row(concepts_by_id: dict[str, dict[str, Any]], concept_id: str, degree: int) -> dict[str, Any]:
    concept = concepts_by_id.get(concept_id, {})
    return {
        "concept_id": concept_id,
        "concept_name": concept.get("concept_name", concept_id),
        "domain": concept.get("domain", "unknown"),
        "degree": degree,
    }


def _domain_density(concepts: list[dict[str, Any]], edges: list[dict[str, Any]], concepts_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    domain_counts = Counter(str(concept.get("domain") or "unknown") for concept in concepts)
    domain_edges = Counter()
    for edge in edges:
        source_domain = str((concepts_by_id.get(edge.get("source_concept_id")) or {}).get("domain") or "unknown")
        target_domain = str((concepts_by_id.get(edge.get("target_concept_id")) or {}).get("domain") or "unknown")
        if source_domain == target_domain:
            domain_edges[source_domain] += 1
        else:
            domain_edges["cross_domain"] += 1
    return {
        domain: {
            "concepts": count,
            "internal_edges": domain_edges.get(domain, 0),
            "edge_per_concept": round(domain_edges.get(domain, 0) / max(1, count), 4),
        }
        for domain, count in domain_counts.most_common()
    } | {"cross_domain_edges": domain_edges.get("cross_domain", 0)}


def _graph_density(node_count: int, edge_count: int) -> float:
    possible = node_count * (node_count - 1)
    return round(edge_count / possible, 8) if possible > 0 else 0.0


def _scale_readiness_label(target: int, performance: dict[str, Any]) -> str:
    if target <= 50_000 and performance["retrieval_latency_ms"] < 500:
        return "ready_with_current_indexes"
    if target <= 100_000:
        return "needs_persistent_indexes_or_sqlite"
    return "needs_dedicated_vector_or_graph_store"


def _remaining_bottlenecks(performance: dict[str, Any], analytics: dict[str, Any]) -> list[str]:
    blockers = []
    if performance["retrieval_latency_ms"] > 500:
        blockers.append("retrieval_latency_above_500ms")
    if performance["graph_traversal_latency_ms"] > 500:
        blockers.append("graph_traversal_latency_above_500ms")
    if analytics["isolated_concepts"] > analytics["concept_count"] * 0.15:
        blockers.append("too_many_isolated_concepts")
    blockers.append("jsonl_storage_will_need_persistent_indexes_before_100k_plus")
    blockers.append("concept_retrieval_still_scores_candidates_in_python")
    return blockers


def _recommendation(performance: dict[str, Any], analytics: dict[str, Any]) -> str:
    if performance["retrieval_latency_ms"] > 1000 or performance["graph_traversal_latency_ms"] > 1000:
        return "CONTINUE_PERFORMANCE_ENGINEERING"
    if analytics["isolated_concepts"] > analytics["concept_count"] * 0.25:
        return "CONTINUE_GRAPH_CONNECTIVITY_ENGINEERING"
    return "READY_FOR_RC2_ARCHITECTURE_FREEZE_WITH_SCALE_GUARDS"


def _tokens(value: Any) -> set[str]:
    return {token for token in _normalize(value).split() if len(token) > 2}


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def _report_md(report: dict[str, Any]) -> str:
    perf = report["performance"]
    analytics = report["graph_analytics"]
    lines = [
        "# RC2 DCM Scalability Readiness",
        "",
        "## Executive Summary",
        "",
        report["executive_summary"],
        "",
        "## Current Scale",
        "",
        f"- Concepts: {report['current_concept_count']}",
        f"- Graph edges: {report['current_edge_count']}",
        "",
        "## Performance",
        "",
        f"- Concept load time ms: {perf['concept_load_time_ms']}",
        f"- Graph load time ms: {perf['graph_load_time_ms']}",
        f"- Retrieval latency ms: {perf['retrieval_latency_ms']}",
        f"- Cached retrieval latency ms: {perf['cached_retrieval_latency_ms']}",
        f"- Retrieval latency improvement: {perf['retrieval_latency_improvement']}",
        f"- Legacy edge scan latency ms: {perf['legacy_edge_scan_latency_ms']}",
        f"- Indexed edge lookup latency ms: {perf['indexed_edge_lookup_latency_ms']}",
        f"- Graph lookup improvement: {perf['graph_lookup_improvement']}",
        f"- Graph traversal latency ms: {perf['graph_traversal_latency_ms']}",
        f"- Cache hit rate: {perf['cache_hit_rate']}",
        "",
        "## Graph Analytics",
        "",
        f"- Isolated concepts: {analytics['isolated_concepts']}",
        f"- Connected components: {analytics['connected_components']['count']}",
        f"- Average path length estimate: {analytics['average_path_length_estimate']}",
        f"- Graph density: {analytics['graph_density']}",
        "",
        "## Hub Concepts",
        "",
        *[f"- {item['concept_name']} ({item['domain']}): degree {item['degree']}" for item in analytics["hub_concepts"][:10]],
        "",
        "## Remaining Bottlenecks",
        "",
        *[f"- {item}" for item in report["remaining_bottlenecks"]],
        "",
        "## Recommendation",
        "",
        report["recommendation"],
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(json.dumps(write_dcm_scalability_readiness_report(), indent=2, sort_keys=True))
