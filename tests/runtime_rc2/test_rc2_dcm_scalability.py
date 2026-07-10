from __future__ import annotations

from orchestration.runtime import rc2_dcm_scalability as scale


def _concept(concept_id: str, name: str, domain: str, keywords: list[str] | None = None) -> dict:
    return {
        "concept_id": concept_id,
        "concept_name": name,
        "domain": domain,
        "short_definition": f"{name} is a test concept for {domain}.",
        "keywords": keywords or [],
        "related_concepts": [f"{domain} evidence"],
    }


def _edge(edge_id: str, source: str, target: str, relation: str = "supports") -> dict:
    return {
        "edge_id": edge_id,
        "source_concept_id": source,
        "target_concept_id": target,
        "relation_type": relation,
        "confidence": 0.9,
    }


def test_concept_indexes_cover_ids_names_domains_keywords_and_related():
    concepts = [
        _concept("c1", "Photosynthesis", "biology", ["light", "glucose"]),
        _concept("c2", "Cellular Respiration", "biology", ["ATP"]),
        _concept("c3", "Interest Rates", "finance", ["borrowing"]),
    ]

    index = scale.build_concept_indexes(concepts)

    assert index["by_id"]["c1"]["concept_name"] == "Photosynthesis"
    assert index["by_normalized_name"]["cellular respiration"]["concept_id"] == "c2"
    assert len(index["by_domain"]["biology"]) == 2
    assert "c1" in index["keyword_index"]["glucose"]
    assert "c3" in index["related_concept_index"]["finance evidence"]


def test_graph_indexes_cover_adjacency_relation_and_concept_edges():
    edges = [
        _edge("e1", "c1", "c2", "supports"),
        _edge("e2", "c2", "c3", "analogy_to"),
    ]

    index = scale.build_graph_indexes(edges)

    assert index["outgoing"]["c1"][0]["edge_id"] == "e1"
    assert index["incoming"]["c2"][0]["edge_id"] == "e1"
    assert {edge["edge_id"] for edge in index["concept_to_edges"]["c2"]} == {"e1", "e2"}
    assert index["relation_index"]["analogy_to"][0]["edge_id"] == "e2"


def test_runtime_retrieval_cache_tracks_hits_and_misses():
    cache = scale.RuntimeRetrievalCache()
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"answer": "cached"}

    assert cache.get("Hello World", loader)["answer"] == "cached"
    assert cache.get("hello   world", loader)["answer"] == "cached"
    assert calls["count"] == 1
    assert cache.hits == 1
    assert cache.misses == 1
    assert cache.hit_rate == 0.5


def test_scalability_report_preserves_safety(monkeypatch):
    monkeypatch.setattr(scale, "benchmark_runtime_performance", lambda: {
        "concept_load_time_ms": 1,
        "graph_load_time_ms": 1,
        "concept_index_build_time_ms": 1,
        "graph_index_build_time_ms": 1,
        "retrieval_latency_ms": 10,
        "cached_retrieval_latency_ms": 4,
        "retrieval_latency_improvement": 0.6,
        "legacy_edge_scan_latency_ms": 5,
        "indexed_edge_lookup_latency_ms": 1,
        "graph_lookup_improvement": 0.8,
        "graph_traversal_latency_ms": 8,
        "cache_hit_rate": 0.5,
        "cache_hits": 5,
        "cache_misses": 5,
        "memory_footprint_estimate": {},
    })
    monkeypatch.setattr(scale, "graph_analytics", lambda: {
        "concept_count": 10,
        "edge_count": 12,
        "degree_distribution": {},
        "hub_concepts": [],
        "bridge_concepts": [],
        "isolated_concepts": 0,
        "connected_components": {"count": 1, "largest": 10, "top_sizes": [10]},
        "average_path_length_estimate": 1.4,
        "relation_distribution": {},
        "domain_density": {},
        "graph_density": 0.1,
    })
    monkeypatch.setattr(scale, "graph_diagnostics", lambda: {"graph_consistency": 1.0})
    monkeypatch.setattr(scale, "run_cross_domain_reasoning_evaluation", lambda: {
        "average_reasoning_quality": 1.0,
        "average_graph_usefulness": 1.0,
        "average_hallucination_risk": 0.1,
        "average_overreach_risk": 0.1,
        "operator_review_readiness": 1.0,
    })

    report = scale.build_dcm_scalability_readiness_report()

    assert report["current_concept_count"] == 10
    assert "concept_id map" in report["indexes_added"]
    assert "runtime graph index signature cache" in report["caches_added"]
    assert report["safety_invariants"]["training_performed"] is False
    assert report["safety_invariants"]["canonical_write_performed"] is False
