"""Storage adapter for the RC2 substrate.

Runtime callers use this module instead of deciding whether to read SQLite or
JSONL directly. SQLite is preferred when available; JSONL remains the safe
fallback and audit/export source.
"""

from __future__ import annotations

from typing import Any

from orchestration.runtime import rc2_sqlite_substrate as sqlite_backend
from orchestration.runtime.rc2_substrate_reconciliation import build_substrate_reconciliation
from orchestration.runtime.rc2_developmental_concept_memory import (
    load_approved_concepts,
    rank_approved_concepts,
)
from orchestration.runtime.rc2_governed_semantic_graph import (
    bounded_graph_traversal,
    build_runtime_graph_index,
    load_approved_graph_edges,
)


def backend_health() -> dict[str, Any]:
    return sqlite_backend.backend_health()


def substrate_counts() -> dict[str, Any]:
    reconciliation = build_substrate_reconciliation(write_reports=False)
    display = reconciliation["ui_display"]
    health = reconciliation["backend_health"]
    if display.get("sqlite_available"):
        return {
            "backend": display.get("backend"),
            "concepts": int(display.get("active_runtime_concepts", 0)),
            "active_runtime_concepts": int(display.get("active_runtime_concepts", 0)),
            "graph_edges": int(display.get("active_graph_edges", 0)),
            "active_graph_edges": int(display.get("active_graph_edges", 0)),
            "import_audited_events": int(display.get("substrate_replay_events", 0)),
            "substrate_replay_events": int(display.get("substrate_replay_events", 0)),
            "import_audited_concepts": int(display.get("concept_replay_events", 0)),
            "concept_replay_events": int(display.get("concept_replay_events", 0)),
            "import_audited_graph_edges": int(display.get("graph_edge_replay_events", 0)),
            "graph_edge_replay_events": int(display.get("graph_edge_replay_events", 0)),
            "migration_audit_events": int(display.get("migration_audit_events", 0)),
            "replay_events": int(display.get("substrate_replay_events", 0)),
            "concept_replay_coverage": float(health.get("replay_coverage", {}).get("concept_replay_coverage", 0.0)),
            "edge_replay_coverage": float(health.get("replay_coverage", {}).get("edge_replay_coverage", 0.0)),
            "jsonl_backup": health.get("jsonl_counts", {}),
            "legacy_jsonl_concepts": int(display.get("legacy_jsonl_concepts", 0)),
            "legacy_jsonl_graph_edges": int(display.get("legacy_jsonl_graph_edges", 0)),
            "fresh": bool(display.get("sqlite_fresh")),
            "reconciliation": reconciliation,
        }
    return {
        "backend": "jsonl_fallback",
        "concepts": len(load_approved_concepts()),
        "graph_edges": len(load_approved_graph_edges()),
        "import_audited_events": 0,
        "import_audited_concepts": 0,
        "import_audited_graph_edges": 0,
        "replay_events": 0,
        "concept_replay_coverage": 0.0,
        "edge_replay_coverage": 0.0,
        "jsonl_backup": {},
        "fresh": False,
    }


def load_concepts(limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.load_concepts_sqlite(limit=limit)
    concepts = load_approved_concepts()
    return concepts[:limit] if limit else concepts


def load_diverse_concepts(limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.load_diverse_concepts_sqlite(limit=limit)
    concepts = load_approved_concepts()
    buckets: dict[str, list[dict[str, Any]]] = {}
    for concept in concepts:
        buckets.setdefault(str(concept.get("domain") or ""), []).append(concept)
    selected: list[dict[str, Any]] = []
    keys = sorted(buckets)
    requested = int(limit or len(concepts))
    while keys and len(selected) < requested:
        next_keys = []
        for key in keys:
            bucket = buckets[key]
            if bucket:
                selected.append(bucket.pop(0))
            if bucket:
                next_keys.append(key)
            if len(selected) >= requested:
                break
        keys = next_keys
    return selected


def get_concept(concept_id: str) -> dict[str, Any] | None:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_concept_sqlite(concept_id)
    for concept in load_approved_concepts():
        if str(concept.get("concept_id")) == str(concept_id):
            return concept
    return None


def search_concepts(
    query: str,
    *,
    domain: str | None = None,
    limit: int = 5,
    exclude_concept_names: list[str] | None = None,
) -> dict[str, Any]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.search_concepts_sqlite(
            query,
            domain=domain,
            limit=limit,
            exclude_concept_names=exclude_concept_names,
        )
    result = rank_approved_concepts(
        query,
        domain=domain,
        limit=limit,
        exclude_concept_names=exclude_concept_names,
    )
    return {**result, "backend": "jsonl_fallback"}


def get_edges_for_concept(concept_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_edges_for_concept_sqlite(concept_id, limit=limit)
    index = build_runtime_graph_index()
    edges = index["concept_edges"].get(str(concept_id), [])
    return edges[:limit] if limit else edges


def get_outgoing_edges(concept_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_outgoing_edges_sqlite(concept_id, limit=limit)
    index = build_runtime_graph_index()
    edges = index["outgoing"].get(str(concept_id), [])
    return edges[:limit] if limit else edges


def get_incoming_edges(concept_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_incoming_edges_sqlite(concept_id, limit=limit)
    index = build_runtime_graph_index()
    edges = index["incoming"].get(str(concept_id), [])
    return edges[:limit] if limit else edges


def traverse_graph(concept_id: str, *, depth: int = 1) -> dict[str, Any]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.traverse_graph_sqlite(concept_id, depth=depth)
    return {**bounded_graph_traversal(concept_id, max_depth=depth), "backend": "jsonl_fallback"}


def get_graph_neighborhood(concept_id: str, *, depth: int = 1) -> dict[str, Any]:
    concept = get_concept(concept_id)
    edges = get_edges_for_concept(concept_id, limit=25)
    traversal = traverse_graph(concept_id, depth=depth)
    neighbor_ids = {
        str(edge.get("source_concept_id") if edge.get("target_concept_id") == concept_id else edge.get("target_concept_id"))
        for edge in edges
    }
    neighbors = [item for item in (get_concept(item) for item in sorted(neighbor_ids)) if item]
    return {
        "backend": substrate_counts()["backend"],
        "concept": concept,
        "edges": edges,
        "neighbors": neighbors,
        "traversal": traversal,
        "read_only": True,
    }
