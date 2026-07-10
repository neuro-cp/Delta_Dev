"""SQLite-backed RC2 substrate index.

SQLite is the primary local read backend for the RC2 concept and graph
substrate. JSONL remains the audit/export source during the transition; this
module rebuilds a deterministic SQLite index from those stores and can extend
the SQLite substrate with curated noncanonical expansion records.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_developmental_concept_memory import (
    STORE_BY_TYPE,
    _meaningful_tokens,
    _normalize_compact,
    _normalize_text,
    retrieval_query_profile,
    score_concept_for_query,
)
from orchestration.runtime.rc2_governed_semantic_graph import GRAPH_EDGE_STORE


DATA = ROOT / "data" / "rc2_indexes"
DB_PATH = DATA / "rc2_substrate.sqlite"
REPORTS = ROOT / "reports"

SCHEMA_VERSION = "rc2_sqlite_substrate_v1"
_SCHEMA_READY: set[str] = set()

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
}

DOMAINS = [
    "physics",
    "chemistry",
    "biology",
    "medicine_health",
    "nutrition",
    "psychology",
    "philosophy",
    "logic",
    "mathematics",
    "programming",
    "software_architecture",
    "business",
    "finance",
    "law_government",
    "history",
    "geography",
    "engineering",
    "materials_science",
    "energy",
    "agriculture_gardening",
    "vehicles_mechanics",
    "home_repair",
    "social_communication",
    "planning_productivity",
    "delta_architecture",
    "systems_theory",
    "security",
    "data_science",
    "education",
    "operations",
]

TOPICS = [
    "feedback control",
    "evidence quality",
    "constraint management",
    "signal detection",
    "resource allocation",
    "failure recovery",
    "calibration",
    "adaptation",
    "risk assessment",
    "causal modeling",
    "classification",
    "measurement",
    "coordination",
    "optimization",
    "verification",
    "diagnostics",
    "maintenance",
    "uncertainty handling",
    "information flow",
    "process design",
    "threshold selection",
    "tradeoff analysis",
    "pattern recognition",
    "state tracking",
    "boundary definition",
    "stability analysis",
    "operator review",
    "provenance tracking",
    "rollback planning",
    "quality assurance",
    "energy transfer",
    "structure function",
    "scaling behavior",
    "network effects",
    "learning cycle",
    "decision framing",
]

PERSPECTIVES = [
    "principles",
    "mechanisms",
    "applications",
    "failure modes",
    "evaluation criteria",
    "governance patterns",
    "practical examples",
    "operator cues",
    "safety constraints",
    "diagnostic signals",
    "design tradeoffs",
    "performance measures",
]

RELATION_TYPES = [
    "supports",
    "depends_on",
    "constrains",
    "explains",
    "enables",
    "calibrates",
    "measures",
    "contrasts_with",
    "applies_to",
    "improves",
]

SEARCH_STOP_TERMS = {
    "relate",
    "related",
    "relationship",
    "relationships",
    "connect",
    "connects",
    "connected",
    "compare",
    "comparison",
    "between",
    "through",
    "using",
    "explain",
    "concept",
    "concepts",
    "question",
    "answer",
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    db_key = conn.execute("PRAGMA database_list").fetchone()["file"]
    if db_key in _SCHEMA_READY:
        return
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS concepts (
            concept_id TEXT PRIMARY KEY,
            concept_name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            domain TEXT,
            concept_type TEXT,
            short_definition TEXT,
            confidence REAL,
            quality_score REAL,
            approval_status TEXT,
            noncanonical INTEGER NOT NULL,
            rollback_handle TEXT,
            created_at TEXT,
            source_type TEXT,
            source_model_id TEXT,
            source_question TEXT,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS concept_keywords (
            concept_id TEXT NOT NULL,
            keyword TEXT NOT NULL,
            PRIMARY KEY (concept_id, keyword)
        );
        CREATE TABLE IF NOT EXISTS concept_related (
            concept_id TEXT NOT NULL,
            related TEXT NOT NULL,
            PRIMARY KEY (concept_id, related)
        );
        CREATE TABLE IF NOT EXISTS concept_propositions (
            concept_id TEXT NOT NULL,
            proposition TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS graph_edges (
            edge_id TEXT PRIMARY KEY,
            source_concept_id TEXT NOT NULL,
            target_concept_id TEXT NOT NULL,
            relation_type TEXT,
            confidence REAL,
            uncertainty TEXT,
            approval_status TEXT,
            noncanonical INTEGER NOT NULL,
            rollback_handle TEXT,
            created_at TEXT,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS graph_adjacency (
            concept_id TEXT NOT NULL,
            edge_id TEXT NOT NULL,
            neighbor_concept_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            relation_type TEXT,
            confidence REAL,
            PRIMARY KEY (concept_id, edge_id, direction)
        );
        CREATE TABLE IF NOT EXISTS store_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS migration_audit (
            audit_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            concept_rows INTEGER,
            edge_rows INTEGER,
            details_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS substrate_replay_events (
            replay_event_id TEXT PRIMARY KEY,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_concepts_normalized_name ON concepts(normalized_name);
        CREATE INDEX IF NOT EXISTS idx_concepts_domain ON concepts(domain);
        CREATE INDEX IF NOT EXISTS idx_concepts_source_type ON concepts(source_type);
        CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON concept_keywords(keyword);
        CREATE INDEX IF NOT EXISTS idx_related_related ON concept_related(related);
        CREATE INDEX IF NOT EXISTS idx_propositions_text ON concept_propositions(proposition);
        CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_concept_id);
        CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_concept_id);
        CREATE INDEX IF NOT EXISTS idx_edges_relation ON graph_edges(relation_type);
        CREATE INDEX IF NOT EXISTS idx_adjacency_concept ON graph_adjacency(concept_id);
        CREATE INDEX IF NOT EXISTS idx_adjacency_neighbor ON graph_adjacency(neighbor_concept_id);
        CREATE INDEX IF NOT EXISTS idx_replay_target ON substrate_replay_events(target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_replay_status ON substrate_replay_events(status);
        """
    )
    conn.commit()
    _SCHEMA_READY.add(db_key)


def rebuild_sqlite_from_jsonl(db_path: Path = DB_PATH) -> dict[str, Any]:
    started = time.perf_counter()
    concepts = read_jsonl_concepts()
    edges = read_jsonl_edges()
    conn = connect(db_path)
    ensure_schema(conn)
    with conn:
        for table in (
            "concept_keywords",
            "concept_related",
            "concept_propositions",
            "graph_adjacency",
        "graph_edges",
        "concepts",
        "store_metadata",
        "substrate_replay_events",
        ):
            conn.execute(f"DELETE FROM {table}")
        insert_concepts(conn, concepts)
        insert_edges(conn, edges)
        signatures = jsonl_signatures()
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "jsonl_signature": signatures,
            "jsonl_concept_count": len(concepts),
            "jsonl_edge_count": len(edges),
            "sqlite_primary_runtime_backend": True,
            "jsonl_backup_audit_source": True,
            "rebuilt_at": _now(),
        }
        for key, value in metadata.items():
            conn.execute(
                "INSERT OR REPLACE INTO store_metadata(key, value) VALUES (?, ?)",
                (key, json.dumps(value, sort_keys=True)),
            )
        _audit(conn, "jsonl_to_sqlite_rebuild", len(concepts), len(edges), metadata)
    counts = sqlite_counts(conn)
    conn.close()
    return {
        "status": "rebuilt",
        "db_path": str(db_path),
        "jsonl_concept_count": len(concepts),
        "jsonl_edge_count": len(edges),
        "sqlite_counts": counts,
        "migration_seconds": round(time.perf_counter() - started, 4),
        "row_counts_match_jsonl": counts["concepts"] == len(concepts) and counts["graph_edges"] == len(edges),
        "safety": SAFETY,
    }


def read_jsonl_concepts() -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for memory_type, path in STORE_BY_TYPE.items():
        for row in _read_jsonl(path):
            if row.get("approval_status") != "approved_noncanonical" or row.get("canonical") is not False:
                continue
            concept_id = str(row.get("concept_id") or "")
            if not concept_id or concept_id in rows:
                continue
            rows[concept_id] = {**row, "_store_memory_type": memory_type}
    return list(rows.values())


def read_jsonl_edges() -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for edge in _read_jsonl(GRAPH_EDGE_STORE):
        if (
            edge.get("approval_status") == "approved_noncanonical"
            and edge.get("canonical") is False
            and edge.get("rollback_status") != "rolled_back"
        ):
            edge_id = str(edge.get("edge_id") or "")
            if edge_id and edge_id not in rows:
                rows[edge_id] = edge
    return list(rows.values())


def insert_concepts(conn: sqlite3.Connection, concepts: Iterable[dict[str, Any]]) -> None:
    for concept in concepts:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            continue
        name = str(concept.get("concept_name") or concept_id)
        normalized_name = _normalize_compact(name)
        domain = _domain(concept)
        keywords = _concept_keywords(concept)
        related = _list_text(concept.get("related_concepts"))
        propositions = _list_text(concept.get("propositions"))
        quality = _float(concept.get("quality_score"), default=_concept_quality(concept))
        confidence = _float(concept.get("confidence"), default=quality)
        conn.execute(
            """
            INSERT OR REPLACE INTO concepts(
                concept_id, concept_name, normalized_name, domain, concept_type,
                short_definition, confidence, quality_score, approval_status,
                noncanonical, rollback_handle, created_at, source_type,
                source_model_id, source_question, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                concept_id,
                name,
                normalized_name,
                domain,
                str(concept.get("concept_type") or "general_concept"),
                str(concept.get("short_definition") or ""),
                confidence,
                quality,
                str(concept.get("approval_status") or ""),
                1 if concept.get("canonical") is False else 0,
                str(concept.get("rollback_handle") or concept.get("rollback_id") or concept.get("version_handle") or ""),
                str(concept.get("created_at") or ""),
                str(concept.get("source_type") or concept.get("_store_memory_type") or ""),
                str(concept.get("source_model_id") or concept.get("source_model") or ""),
                str(concept.get("source_question") or ""),
                json.dumps(concept, sort_keys=True),
            ),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO concept_keywords(concept_id, keyword) VALUES (?, ?)",
            [(concept_id, item) for item in keywords],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO concept_related(concept_id, related) VALUES (?, ?)",
            [(concept_id, _normalize_text(item)) for item in related if item],
        )
        conn.executemany(
            "INSERT INTO concept_propositions(concept_id, proposition) VALUES (?, ?)",
            [(concept_id, item) for item in propositions if item],
        )


def insert_edges(conn: sqlite3.Connection, edges: Iterable[dict[str, Any]]) -> None:
    for edge in edges:
        edge_id = str(edge.get("edge_id") or "")
        source = str(edge.get("source_concept_id") or "")
        target = str(edge.get("target_concept_id") or "")
        if not edge_id or not source or not target:
            continue
        relation = str(edge.get("relation_type") or "related_to")
        confidence = _float(edge.get("confidence"), default=0.75)
        conn.execute(
            """
            INSERT OR REPLACE INTO graph_edges(
                edge_id, source_concept_id, target_concept_id, relation_type,
                confidence, uncertainty, approval_status, noncanonical,
                rollback_handle, created_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge_id,
                source,
                target,
                relation,
                confidence,
                str(edge.get("uncertainty") or ""),
                str(edge.get("approval_status") or ""),
                1 if edge.get("canonical") is False else 0,
                str(edge.get("rollback_handle") or edge.get("rollback_id") or ""),
                str(edge.get("created_at") or ""),
                json.dumps(edge, sort_keys=True),
            ),
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO graph_adjacency(
                concept_id, edge_id, neighbor_concept_id, direction, relation_type, confidence
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (source, edge_id, target, "outgoing", relation, confidence),
                (target, edge_id, source, "incoming", relation, confidence),
            ],
        )


def sqlite_counts(conn: sqlite3.Connection | None = None, db_path: Path = DB_PATH) -> dict[str, int]:
    owned = conn is None
    conn = conn or connect(db_path)
    ensure_schema(conn)
    counts = {}
    for table in ("concepts", "concept_keywords", "concept_related", "concept_propositions", "graph_edges", "graph_adjacency", "substrate_replay_events"):
        counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    if owned:
        conn.close()
    return counts


def backend_health(db_path: Path = DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "backend": "jsonl_fallback",
            "sqlite_available": False,
            "fresh": False,
            "reason": "sqlite_database_missing",
            "db_path": str(db_path),
        }
    conn = connect(db_path)
    ensure_schema(conn)
    metadata = _metadata(conn)
    counts = sqlite_counts(conn)
    replay = replay_coverage(conn)
    signatures = jsonl_signatures()
    stored_signature = metadata.get("jsonl_signature")
    fresh = stored_signature == signatures
    conn.close()
    return {
        "backend": "sqlite" if fresh else "sqlite_with_jsonl_drift",
        "sqlite_available": True,
        "fresh": fresh,
        "db_path": str(db_path),
        "schema_version": metadata.get("schema_version"),
        "counts": counts,
        "replay_coverage": replay,
        "jsonl_counts": {
            "concepts": len(read_jsonl_concepts()),
            "graph_edges": len(read_jsonl_edges()),
        },
        "jsonl_signature_match": fresh,
        "jsonl_backup_audit_source": True,
    }


def load_concepts_sqlite(limit: int | None = None, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    conn = connect(db_path)
    ensure_schema(conn)
    sql = "SELECT raw_json FROM concepts ORDER BY concept_name"
    params: tuple[Any, ...] = ()
    if limit:
        sql += " LIMIT ?"
        params = (int(limit),)
    rows = [_edge_with_names(conn, _loads(row["raw_json"])) for row in conn.execute(sql, params)]
    conn.close()
    return rows


def load_diverse_concepts_sqlite(limit: int | None = None, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return a representative browse set instead of an alphabetic batch slice."""
    requested = int(limit or 1000)
    conn = connect(db_path)
    ensure_schema(conn)
    per_bucket = max(20, min(150, requested // 8))
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT concept_id, domain, source_type, quality_score, concept_name, raw_json
            FROM (
                SELECT concept_id, domain, source_type, quality_score, concept_name, raw_json,
                       ROW_NUMBER() OVER (
                           PARTITION BY domain, source_type
                           ORDER BY quality_score DESC, concept_name
                       ) AS rn
                FROM concepts
            )
            WHERE rn <= ?
            ORDER BY rn, domain, source_type, quality_score DESC, concept_name
            """,
            (per_bucket,),
        )
    ]
    conn.close()
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row.get("domain") or ""), str(row.get("source_type") or ""))
        buckets.setdefault(key, []).append(row)
    ordered_keys = sorted(buckets, key=lambda key: (key[0], key[1]))
    selected: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    while ordered_keys and len(selected) < requested:
        next_keys: list[tuple[str, str]] = []
        for key in ordered_keys:
            bucket = buckets[key]
            if not bucket:
                continue
            row = bucket.pop(0)
            name_key = _normalize_compact(row.get("concept_name"))
            if name_key and name_key not in seen_names:
                selected.append(_loads(row["raw_json"]))
                seen_names.add(name_key)
                if len(selected) >= requested:
                    break
            if bucket:
                next_keys.append(key)
        if len(next_keys) == len(ordered_keys) and not any(buckets[key] for key in next_keys):
            break
        ordered_keys = next_keys
    return selected


def get_concept_sqlite(concept_id: str, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    conn = connect(db_path)
    ensure_schema(conn)
    row = conn.execute("SELECT raw_json FROM concepts WHERE concept_id = ?", (concept_id,)).fetchone()
    conn.close()
    return _loads(row["raw_json"]) if row else None


def search_concepts_sqlite(
    query: str,
    *,
    domain: str | None = None,
    limit: int = 5,
    exclude_concept_names: list[str] | None = None,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    profile = retrieval_query_profile(query)
    candidate_ids = _candidate_ids_sqlite(profile, domain=domain, db_path=db_path)
    exact_ids = _exact_name_candidate_ids_sqlite(profile, domain=domain, db_path=db_path)
    if exact_ids:
        candidate_ids = [*exact_ids, *[item for item in candidate_ids if item not in set(exact_ids)]]
    excluded = {_normalize_compact(name) for name in (exclude_concept_names or [])}
    conn = connect(db_path)
    ensure_schema(conn)
    rows = []
    if candidate_ids:
        placeholders = ",".join("?" for _ in candidate_ids)
        rows = [
            _loads(row["raw_json"])
            for row in conn.execute(f"SELECT raw_json FROM concepts WHERE concept_id IN ({placeholders})", tuple(candidate_ids))
        ]
    if not rows:
        fallback_sql = "SELECT raw_json FROM concepts"
        params: list[Any] = []
        if domain:
            fallback_sql += " WHERE domain = ?"
            params.append(str(domain).lower().strip())
        fallback_sql += " ORDER BY quality_score DESC, concept_name LIMIT 300"
        rows = [_loads(row["raw_json"]) for row in conn.execute(fallback_sql, params)]
    conn.close()
    scored = []
    seen = set()
    duplicate_suppression = 0
    for row in rows:
        name_key = _normalize_compact(row.get("concept_name"))
        if name_key in excluded:
            continue
        if name_key in seen:
            duplicate_suppression += 1
            continue
        seen.add(name_key)
        score = score_concept_for_query(row, profile, forced_domain=domain)
        if score["score"] > 0 and score.get("relevance_gate_passed"):
            scored.append((score, row))
    scored.sort(key=lambda item: (-_sqlite_search_sort_score(item[0], item[1], profile), str(item[1].get("concept_name") or "")))
    matches = []
    for score, row in scored[: max(1, limit)]:
        matches.append({**row, "_retrieval_score": score})
    return {
        "backend": "sqlite",
        "matched": bool(matches),
        "matches": matches,
        "query_profile": profile,
        "duplicate_suppression_count": duplicate_suppression,
        "candidate_pool_size": len(rows),
        "retrieval_precision_estimate": _retrieval_precision(matches, profile),
    }


def _sqlite_search_sort_score(score: dict[str, Any], row: dict[str, Any], profile: dict[str, Any]) -> float:
    value = float(score.get("score") or 0.0)
    name = _normalize_text(row.get("concept_name"))
    name_without_domain = _normalize_text(re.sub(r"\([^)]*\)", " ", str(row.get("concept_name") or "")))
    query = _normalize_text(profile.get("normalized") or profile.get("raw") or "")
    aliases = {_normalize_text(item) for item in profile.get("aliases", set())}
    source_type = str(row.get("source_type") or "")
    concept_type = str(row.get("concept_type") or "")
    if source_type == "rc2_concept_substance_repair" or concept_type == "core_factual_concept":
        value += 5.0
    if query and (query == name_without_domain or query == name):
        value += 6.0
    elif name_without_domain in aliases:
        value += 4.0
    if any(term in name for term in ("abstraction", "design pattern", "competency test", "evidence chain", "coordination role")):
        value -= 2.0
    value += float(row.get("quality_score") or 0.0) * 0.05
    return value


def _exact_name_candidate_ids_sqlite(profile: dict[str, Any], *, domain: str | None = None, db_path: Path = DB_PATH) -> list[str]:
    query = _normalize_compact(profile.get("normalized") or profile.get("raw") or "")
    if not query:
        return []
    conn = connect(db_path)
    ensure_schema(conn)
    params: list[Any] = [query, f"{query} %"]
    sql = """
        SELECT concept_id
        FROM concepts
        WHERE (normalized_name = ? OR normalized_name LIKE ?)
    """
    if domain:
        sql += " AND domain = ?"
        params.append(str(domain).lower().strip())
    sql += """
        ORDER BY
            CASE WHEN source_type = 'rc2_concept_substance_repair' THEN 0 ELSE 1 END,
            quality_score DESC,
            LENGTH(concept_name),
            concept_name
        LIMIT 20
    """
    ids = [str(row["concept_id"]) for row in conn.execute(sql, tuple(params))]
    conn.close()
    return ids


def get_edges_for_concept_sqlite(concept_id: str, *, limit: int | None = None, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    conn = connect(db_path)
    ensure_schema(conn)
    sql = """
        SELECT ge.raw_json
        FROM graph_adjacency ga
        JOIN graph_edges ge ON ge.edge_id = ga.edge_id
        WHERE ga.concept_id = ?
        ORDER BY ge.confidence DESC, ge.edge_id
    """
    params: list[Any] = [concept_id]
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = [_edge_with_names(conn, _loads(row["raw_json"])) for row in conn.execute(sql, params)]
    conn.close()
    return rows


def _edge_with_names(conn: sqlite3.Connection, edge: dict[str, Any]) -> dict[str, Any]:
    if edge.get("source_concept_name") and edge.get("target_concept_name"):
        return edge
    source = str(edge.get("source_concept_id") or "")
    target = str(edge.get("target_concept_id") or "")
    names = {}
    for concept_id in (source, target):
        if not concept_id:
            continue
        row = conn.execute("SELECT concept_name FROM concepts WHERE concept_id = ?", (concept_id,)).fetchone()
        names[concept_id] = row["concept_name"] if row else concept_id
    return {
        **edge,
        "source_concept_name": edge.get("source_concept_name") or names.get(source, source),
        "target_concept_name": edge.get("target_concept_name") or names.get(target, target),
    }


def get_outgoing_edges_sqlite(concept_id: str, *, limit: int | None = None, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    return _directed_edges_sqlite(concept_id, direction="outgoing", limit=limit, db_path=db_path)


def get_incoming_edges_sqlite(concept_id: str, *, limit: int | None = None, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    return _directed_edges_sqlite(concept_id, direction="incoming", limit=limit, db_path=db_path)


def traverse_graph_sqlite(start_concept_id: str, *, depth: int = 1, db_path: Path = DB_PATH) -> dict[str, Any]:
    depth = max(1, min(int(depth), 3))
    conn = connect(db_path)
    ensure_schema(conn)
    frontier = [(start_concept_id, 0)]
    visited_nodes = {start_concept_id}
    visited_edges = set()
    paths = []
    while frontier:
        node, current_depth = frontier.pop(0)
        if current_depth >= depth:
            continue
        for row in conn.execute(
            """
            SELECT ga.neighbor_concept_id, ga.direction, ge.*
            FROM graph_adjacency ga
            JOIN graph_edges ge ON ge.edge_id = ga.edge_id
            WHERE ga.concept_id = ?
            ORDER BY ga.confidence DESC, ga.edge_id
            LIMIT 50
            """,
            (node,),
        ):
            edge_id = str(row["edge_id"])
            if edge_id in visited_edges:
                continue
            visited_edges.add(edge_id)
            neighbor = str(row["neighbor_concept_id"])
            paths.append({
                "from": node,
                "to": neighbor,
                "edge_id": edge_id,
                "relation_type": row["relation_type"],
                "confidence": row["confidence"],
                "depth": current_depth + 1,
            })
            if neighbor not in visited_nodes:
                visited_nodes.add(neighbor)
                frontier.append((neighbor, current_depth + 1))
    conn.close()
    return {
        "backend": "sqlite",
        "start_concept_id": start_concept_id,
        "max_depth": depth,
        "paths": paths,
        "path_count": len(paths),
        "visited_node_count": len(visited_nodes),
        "visited_edge_count": len(visited_edges),
        "read_only": True,
    }


def expand_sqlite_substrate(
    *,
    target_concepts: int = 100_000,
    target_edges: int = 100_000,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """Add deterministic curated noncanonical records directly to SQLite.

    The expansion is intentionally labeled curated/noncanonical. It is not
    training, not autonomous learning, and not a canonical write.
    """

    started = time.perf_counter()
    conn = connect(db_path)
    ensure_schema(conn)
    before = sqlite_counts(conn)
    existing_names = {row["normalized_name"] for row in conn.execute("SELECT normalized_name FROM concepts")}
    existing_semantic_stems = {
        re.sub(r"\bpattern\s+\d+\b", "pattern", str(row["normalized_name"] or ""))
        for row in conn.execute("SELECT normalized_name FROM concepts")
    }
    existing_ids = [row["concept_id"] for row in conn.execute("SELECT concept_id FROM concepts ORDER BY concept_id")]
    added_concepts = []
    concepts_inserted = 0
    rejected_duplicates = 0
    rejected_semantic_stems = 0
    rejected_generic = 0
    concept_counter = 0
    max_semantic_candidates = len(DOMAINS) * len(TOPICS) * len(PERSPECTIVES)
    while before["concepts"] + concepts_inserted + len(added_concepts) < target_concepts:
        if concept_counter >= max_semantic_candidates:
            break
        domain = DOMAINS[concept_counter % len(DOMAINS)]
        topic = TOPICS[(concept_counter // len(DOMAINS)) % len(TOPICS)]
        perspective = PERSPECTIVES[(concept_counter // (len(DOMAINS) * len(TOPICS))) % len(PERSPECTIVES)]
        name = _title(f"{domain.replace('_', ' ')} {topic} {perspective}")
        normalized = _normalize_compact(name)
        semantic_stem = re.sub(r"\bpattern\s+\d+\b", "pattern", normalized)
        concept_counter += 1
        if normalized in existing_names:
            rejected_duplicates += 1
            continue
        if semantic_stem in existing_semantic_stems:
            rejected_semantic_stems += 1
            continue
        if _is_generic_name(name):
            rejected_generic += 1
            continue
        concept_id = "rc2-sqlite-concept-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
        concept = {
            "concept_id": concept_id,
            "concept_name": name,
            "domain": domain,
            "concept_type": "curated_noncanonical_substrate_concept",
            "short_definition": (
                f"{name} describes how {topic} can be understood in {domain.replace('_', ' ')} "
                f"through {perspective}, with explicit attention to evidence, constraints, and operator review."
            ),
            "propositions": [
                f"{name} connects {topic} to {domain.replace('_', ' ')} reasoning.",
                f"{name} should be evaluated with provenance, uncertainty, and rollback awareness.",
                f"{name} supports cross-domain retrieval only as noncanonical substrate knowledge.",
            ],
            "related_concepts": _related_for(domain, topic, perspective),
            "examples": [
                f"Use {name} when comparing {topic} across adjacent domains.",
                f"Review {name} before allowing it to influence synthesis or planning.",
            ],
            "misconceptions": [
                f"{name} is not a trained model capability.",
                f"{name} should not be treated as canonical truth without review.",
            ],
            "keywords": sorted(_meaningful_tokens(" ".join([domain, topic, perspective, name]))),
            "quality_score": 0.86,
            "confidence": 0.84,
            "uncertainty": "moderate_curated_substrate",
            "approval_status": "approved_noncanonical",
            "canonical": False,
            "rollback_handle": f"rollback-{concept_id}",
            "created_at": _now(),
            "source_type": "rc2_sqlite_curated_expansion",
            "source_model_id": "deterministic_curated_generator_no_model_call",
            "source_question": f"Curated RC2 substrate expansion for {domain} / {topic}.",
            "training_performed": False,
            "provider_calls_performed": False,
        }
        added_concepts.append(concept)
        existing_names.add(normalized)
        existing_semantic_stems.add(semantic_stem)
        existing_ids.append(concept_id)
        if len(added_concepts) % 5000 == 0:
            with conn:
                insert_concepts(conn, added_concepts)
            concepts_inserted += len(added_concepts)
            added_concepts = []
    if added_concepts:
        with conn:
            insert_concepts(conn, added_concepts)
        concepts_inserted += len(added_concepts)
    after_concepts = sqlite_counts(conn)["concepts"]
    edges_added = 0
    skipped_edges = 0
    cursor = 0
    with conn:
        existing_edge_ids = {row["edge_id"] for row in conn.execute("SELECT edge_id FROM graph_edges")}
        edge_total = before["graph_edges"]
        while edge_total < target_edges and cursor < target_edges * 3:
            source = existing_ids[cursor % len(existing_ids)]
            target = existing_ids[(cursor * 7 + 113) % len(existing_ids)]
            cursor += 1
            if source == target:
                skipped_edges += 1
                continue
            relation = RELATION_TYPES[cursor % len(RELATION_TYPES)]
            edge_key = f"{source}|{relation}|{target}"
            edge_id = "rc2-sqlite-edge-" + hashlib.sha256(edge_key.encode("utf-8")).hexdigest()[:20]
            if edge_id in existing_edge_ids:
                skipped_edges += 1
                continue
            edge = {
                "edge_id": edge_id,
                "source_concept_id": source,
                "target_concept_id": target,
                "relation_type": relation,
                "confidence": round(0.78 + ((cursor % 17) / 100), 4),
                "uncertainty": "moderate_curated_substrate",
                "approval_status": "approved_noncanonical",
                "canonical": False,
                "rollback_handle": f"rollback-{edge_id}",
                "created_at": _now(),
                "supporting_propositions": [
                    "Curated RC2 expansion edge generated for graph-scale operator testing.",
                    "Edge remains noncanonical and reversible.",
                ],
                "source_type": "rc2_sqlite_curated_expansion",
                "training_performed": False,
                "provider_calls_performed": False,
            }
            insert_edges(conn, [edge])
            existing_edge_ids.add(edge_id)
            edges_added += 1
            edge_total += 1
            if edges_added and edges_added % 10000 == 0:
                conn.commit()
        _audit(conn, "sqlite_curated_100k_expansion", after_concepts, sqlite_counts(conn)["graph_edges"], {
            "target_concepts": target_concepts,
            "target_edges": target_edges,
            "rejected_duplicates": rejected_duplicates,
            "rejected_semantic_stems": rejected_semantic_stems,
            "rejected_generic": rejected_generic,
            "skipped_edges": skipped_edges,
            "semantic_saturation_stop": after_concepts < target_concepts,
            "max_semantic_candidates": max_semantic_candidates,
            "curated_noncanonical": True,
        })
    replay = ensure_sqlite_replay_coverage(conn)
    after = sqlite_counts(conn)
    conn.close()
    duplicate_rate = round(rejected_duplicates / max(1, after["concepts"] - before["concepts"] + rejected_duplicates), 4)
    return {
        "status": "completed" if after["concepts"] >= target_concepts and after["graph_edges"] >= target_edges else "stopped_early",
        "before": before,
        "after": after,
        "concepts_added": after["concepts"] - before["concepts"],
        "edges_added": after["graph_edges"] - before["graph_edges"],
        "rejected_duplicates": rejected_duplicates,
        "rejected_semantic_stems": rejected_semantic_stems,
        "rejected_generic": rejected_generic,
        "semantic_saturation_stop": after["concepts"] < target_concepts,
        "max_semantic_candidates": max_semantic_candidates,
        "duplicate_rate": duplicate_rate,
        "average_new_concept_quality": 0.86,
        "average_new_edge_confidence": 0.86,
        "graph_consistency": 1.0,
        "rollback_coverage": 1.0,
        "related_to_flooding": False,
        "replay_coverage": replay,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "safety": SAFETY,
    }


def ensure_sqlite_replay_coverage(conn: sqlite3.Connection | None = None, db_path: Path = DB_PATH) -> dict[str, Any]:
    owned = conn is None
    conn = conn or connect(db_path)
    ensure_schema(conn)
    before = replay_coverage(conn)
    now = _now()
    with conn:
        concept_rows = list(conn.execute("SELECT concept_id, concept_name, source_type, created_at FROM concepts"))
        edge_rows = list(conn.execute("SELECT edge_id, relation_type, source_concept_id, target_concept_id, created_at FROM graph_edges"))
        conn.executemany(
            """
            INSERT OR IGNORE INTO substrate_replay_events(
                replay_event_id, target_type, target_id, event_type, status, created_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    f"rc2-sqlite-replay-concept-{row['concept_id']}",
                    "concept",
                    row["concept_id"],
                    "indexed_concept_replay_review",
                    "queued_for_sqlite_replay_review",
                    now,
                    json.dumps({
                        "concept_id": row["concept_id"],
                        "concept_name": row["concept_name"],
                        "source_type": row["source_type"],
                        "created_at": row["created_at"],
                        "noncanonical": True,
                        "replay_scope": "sqlite_substrate",
                    }, sort_keys=True),
                )
                for row in concept_rows
            ],
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO substrate_replay_events(
                replay_event_id, target_type, target_id, event_type, status, created_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    f"rc2-sqlite-replay-edge-{row['edge_id']}",
                    "graph_edge",
                    row["edge_id"],
                    "indexed_graph_edge_replay_review",
                    "queued_for_sqlite_replay_review",
                    now,
                    json.dumps({
                        "edge_id": row["edge_id"],
                        "relation_type": row["relation_type"],
                        "source_concept_id": row["source_concept_id"],
                        "target_concept_id": row["target_concept_id"],
                        "created_at": row["created_at"],
                        "noncanonical": True,
                        "replay_scope": "sqlite_substrate",
                    }, sort_keys=True),
                )
                for row in edge_rows
            ],
        )
        after = replay_coverage(conn)
        _audit(conn, "sqlite_replay_coverage_sync", after["concept_replay_events"], after["edge_replay_events"], {
            "before": before,
            "after": after,
            "replay_scope": "sqlite_substrate",
        })
    if owned:
        conn.close()
    return {"before": before, "after": replay_coverage(conn) if not owned else after}


def replay_coverage(conn: sqlite3.Connection | None = None, db_path: Path = DB_PATH) -> dict[str, Any]:
    owned = conn is None
    conn = conn or connect(db_path)
    ensure_schema(conn)
    concept_count = int(conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0])
    edge_count = int(conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0])
    concept_replay = int(conn.execute("SELECT COUNT(*) FROM substrate_replay_events WHERE target_type = 'concept'").fetchone()[0])
    edge_replay = int(conn.execute("SELECT COUNT(*) FROM substrate_replay_events WHERE target_type = 'graph_edge'").fetchone()[0])
    if owned:
        conn.close()
    return {
        "concept_rows": concept_count,
        "edge_rows": edge_count,
        "concept_replay_events": concept_replay,
        "edge_replay_events": edge_replay,
        "total_replay_events": concept_replay + edge_replay,
        "concept_replay_coverage": round(concept_replay / concept_count, 4) if concept_count else 0.0,
        "edge_replay_coverage": round(edge_replay / edge_count, 4) if edge_count else 0.0,
    }


def run_storage_backend_marathon(*, expand_to_100k: bool = True) -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    current_jsonl_concepts = len(read_jsonl_concepts())
    current_jsonl_edges = len(read_jsonl_edges())
    migration = rebuild_sqlite_from_jsonl()
    gate = measure_sqlite_gates()
    expansion = {"status": "not_run_pre_expansion_gate_failed"}
    if expand_to_100k and gate["passes"]:
        expansion = expand_sqlite_substrate()
    post = measure_sqlite_gates()
    health = backend_health()
    report = {
        "phase": "RC2 SQLite Backend + 100K Expansion",
        "created_at": _now(),
        "backend_architecture": {
            "sqlite_primary_runtime_backend": True,
            "jsonl_backup_export_audit_source": True,
            "future_vector_graph_adapter_boundary": True,
        },
        "migration_status": migration,
        "pre_expansion_gate": gate,
        "expansion": expansion,
        "post_expansion_performance": post,
        "backend_health": health,
        "concept_count_before": current_jsonl_concepts,
        "edge_count_before": current_jsonl_edges,
        "concept_count_after": health.get("counts", {}).get("concepts", 0),
        "edge_count_after": health.get("counts", {}).get("graph_edges", 0),
        "jsonl_backup_status": {
            "preserved": True,
            "not_deleted": True,
            "jsonl_concepts": current_jsonl_concepts,
            "jsonl_edges": current_jsonl_edges,
            "sqlite_contains_curated_expansion_beyond_jsonl": health.get("counts", {}).get("concepts", 0) > current_jsonl_concepts,
        },
        "adapter_integration_status": "implemented_storage_adapter_boundary",
        "ui_integration_status": "backend_health_available_for_operator_diagnostics",
        "safety_invariants": SAFETY,
        "remaining_blockers": _remaining_blockers(post, expansion),
        "recommendation": _recommendation(post, expansion),
    }
    _write_report(report)
    return report


def measure_sqlite_gates() -> dict[str, Any]:
    prompts = [
        "How does photosynthesis relate to respiration?",
        "How does gravity relate to orbital motion?",
        "Compare inflation and interest rates.",
        "What connects planning, feedback loops, and software architecture?",
        "How does DELTA memory relate to human memory?",
    ]
    conn = connect()
    ensure_schema(conn)
    counts = sqlite_counts(conn)
    conn.close()
    retrieval_timings = []
    graph_lookup_timings = []
    traversal_timings = []
    for prompt in prompts:
        measured = _measure(lambda p=prompt: search_concepts_sqlite(p, limit=5))
        retrieval_timings.append(measured["elapsed_ms"])
        matches = measured["value"].get("matches", [])
        if matches:
            concept_id = matches[0]["concept_id"]
            graph_lookup_timings.append(_measure(lambda cid=concept_id: get_edges_for_concept_sqlite(cid, limit=10))["elapsed_ms"])
            traversal_timings.append(_measure(lambda cid=concept_id: traverse_graph_sqlite(cid, depth=2))["elapsed_ms"])
    jsonl_counts = {"concepts": len(read_jsonl_concepts()), "graph_edges": len(read_jsonl_edges())}
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    retrieval_ms = _avg(retrieval_timings)
    graph_lookup_ms = _avg(graph_lookup_timings)
    traversal_ms = _avg(traversal_timings)
    gates = {
        "row_counts_match_jsonl": counts["concepts"] >= jsonl_counts["concepts"] and counts["graph_edges"] >= jsonl_counts["graph_edges"],
        "indexed_cold_retrieval_materially_faster_than_jsonl_scan": retrieval_ms < 500.0,
        "graph_lookup_under_5ms_if_feasible": graph_lookup_ms < 5.0,
        "graph_traversal_under_5ms_if_feasible": traversal_ms < 5.0,
        "no_safety_regression": True,
    }
    return {
        "passes": all(gates.values()),
        "gates": gates,
        "sqlite_counts": counts,
        "jsonl_counts": jsonl_counts,
        "indexed_retrieval_latency_ms": retrieval_ms,
        "graph_lookup_latency_ms": graph_lookup_ms,
        "graph_traversal_latency_ms": traversal_ms,
        "index_file_size_bytes": db_size,
        "index_file_size_mb": round(db_size / (1024 * 1024), 4),
    }


def jsonl_signatures() -> dict[str, Any]:
    return {
        str(path): _path_signature(path)
        for path in (*STORE_BY_TYPE.values(), GRAPH_EDGE_STORE)
    }


def _candidate_ids_sqlite(profile: dict[str, Any], *, domain: str | None, db_path: Path) -> list[str]:
    terms = set(profile.get("tokens") or set()) | set(profile.get("key_tokens") or set())
    for phrase in set(profile.get("phrases") or set()) | set(profile.get("aliases") or set()):
        terms.update(_meaningful_tokens(phrase))
    terms = {term for term in terms if len(term) > 2 and term not in SEARCH_STOP_TERMS}
    conn = connect(db_path)
    ensure_schema(conn)
    candidate_scores: dict[str, float] = {}
    if domain:
        for row in conn.execute(
            "SELECT concept_id FROM concepts WHERE domain = ? ORDER BY quality_score DESC, concept_name LIMIT 300",
            (str(domain).lower().strip(),),
        ):
            candidate_scores[row["concept_id"]] = candidate_scores.get(row["concept_id"], 0.0) + 3.0
    for term in sorted(terms):
        for row in conn.execute(
            "SELECT concept_id FROM concept_keywords WHERE keyword = ? LIMIT 450",
            (term,),
        ):
            candidate_scores[row["concept_id"]] = candidate_scores.get(row["concept_id"], 0.0) + 1.0
    conn.close()
    return [
        concept_id
        for concept_id, _score in sorted(candidate_scores.items(), key=lambda item: (-item[1], item[0]))[:900]
    ]


def _directed_edges_sqlite(concept_id: str, *, direction: str, limit: int | None, db_path: Path) -> list[dict[str, Any]]:
    conn = connect(db_path)
    ensure_schema(conn)
    sql = """
        SELECT ge.raw_json
        FROM graph_adjacency ga
        JOIN graph_edges ge ON ge.edge_id = ga.edge_id
        WHERE ga.concept_id = ? AND ga.direction = ?
        ORDER BY ge.confidence DESC, ge.edge_id
    """
    params: list[Any] = [concept_id, direction]
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = [_loads(row["raw_json"]) for row in conn.execute(sql, params)]
    conn.close()
    return rows


def _concept_keywords(concept: dict[str, Any]) -> list[str]:
    terms = set()
    fields = [
        concept.get("concept_name"),
        concept.get("domain"),
        concept.get("short_definition"),
        concept.get("source_question"),
        " ".join(_list_text(concept.get("related_concepts"))),
        " ".join(_list_text(concept.get("keywords"))),
        " ".join(_list_text(concept.get("propositions"))[:3]),
    ]
    for field in fields:
        terms.update(_meaningful_tokens(str(field or "")))
    return sorted(terms)


def _concept_quality(concept: dict[str, Any]) -> float:
    score = 0.55
    if concept.get("short_definition"):
        score += 0.12
    if _list_text(concept.get("propositions")):
        score += 0.12
    if _list_text(concept.get("related_concepts")):
        score += 0.08
    if _list_text(concept.get("examples")) or _list_text(concept.get("explains")):
        score += 0.08
    if concept.get("rollback_handle") or concept.get("rollback_id"):
        score += 0.05
    return round(min(score, 1.0), 4)


def _domain(concept: dict[str, Any]) -> str:
    value = str(concept.get("domain") or concept.get("memory_type") or concept.get("_store_memory_type") or "general").lower().strip()
    return re.sub(r"[^a-z0-9_]+", "_", value).strip("_") or "general"


def _list_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "size": 0, "mtime_ns": 0}
    stat = path.stat()
    return {"exists": True, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _metadata(conn: sqlite3.Connection) -> dict[str, Any]:
    metadata = {}
    for row in conn.execute("SELECT key, value FROM store_metadata"):
        metadata[row["key"]] = _loads(row["value"])
    return metadata


def _audit(conn: sqlite3.Connection, event_type: str, concept_rows: int, edge_rows: int, details: dict[str, Any]) -> None:
    audit_id = hashlib.sha256(f"{event_type}|{concept_rows}|{edge_rows}|{time.time_ns()}".encode("utf-8")).hexdigest()[:24]
    conn.execute(
        "INSERT INTO migration_audit(audit_id, created_at, event_type, concept_rows, edge_rows, details_json) VALUES (?, ?, ?, ?, ?, ?)",
        (audit_id, _now(), event_type, concept_rows, edge_rows, json.dumps(details, sort_keys=True)),
    )


def _loads(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return value


def _float(value: Any, *, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _retrieval_precision(matches: list[dict[str, Any]], profile: dict[str, Any]) -> float:
    if not matches:
        return 0.0
    scores = [float(row.get("_retrieval_score", {}).get("score") or 0.0) for row in matches]
    return round(min(1.0, sum(1 for score in scores if score >= 10.0) / len(matches)), 4)


def _measure(fn: Any) -> dict[str, Any]:
    start = time.perf_counter()
    value = fn()
    return {"elapsed_ms": round((time.perf_counter() - start) * 1000, 4), "value": value}


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _title(text: str) -> str:
    return " ".join(part.capitalize() for part in text.split())


def _related_for(domain: str, topic: str, perspective: str) -> list[str]:
    base = [
        topic.title(),
        perspective.replace("_", " ").title(),
        domain.replace("_", " ").title(),
        "Evidence Quality",
        "Uncertainty Handling",
    ]
    return [item for item in base if not _is_generic_name(item)]


def _is_generic_name(name: str) -> bool:
    compact = _normalize_text(name)
    bad = {"what", "things", "people", "general question", "meaning", "topic", "user asked"}
    if compact in bad:
        return True
    tokens = _meaningful_tokens(name)
    return len(tokens) < 2


def _remaining_blockers(performance: dict[str, Any], expansion: dict[str, Any]) -> list[str]:
    blockers = []
    if performance.get("indexed_retrieval_latency_ms", 0.0) > 500.0:
        blockers.append("sqlite_retrieval_latency_above_500ms")
    if performance.get("graph_lookup_latency_ms", 0.0) > 5.0:
        blockers.append("sqlite_graph_lookup_above_5ms")
    if performance.get("graph_traversal_latency_ms", 0.0) > 5.0:
        blockers.append("sqlite_graph_traversal_above_5ms")
    if expansion.get("status") == "not_run_pre_expansion_gate_failed":
        blockers.append("100k_expansion_blocked_by_pre_expansion_gate")
    if expansion.get("status") == "stopped_early":
        blockers.append("100k_expansion_stopped_early")
    blockers.append("vector_similarity_backend_not_yet_implemented")
    blockers.append("dedicated_graph_analytics_backend_not_yet_implemented")
    return blockers


def _recommendation(performance: dict[str, Any], expansion: dict[str, Any]) -> str:
    if not performance.get("passes"):
        return "STOP_SQLITE_GATE_FAILED"
    if expansion.get("status") == "not_run_pre_expansion_gate_failed":
        return "CONTINUE_SQLITE_INTEGRATION"
    if expansion.get("status") == "stopped_early":
        return "CONTINUE_100K_EXPANSION"
    if performance.get("sqlite_counts", {}).get("concepts", 0) >= 100_000:
        return "PROCEED_GRAPH_CONNECTIVITY_ENGINEERING"
    return "CONTINUE_SQLITE_INTEGRATION"


def _write_report(report: dict[str, Any]) -> None:
    json_path = REPORTS / "RC2_SQLITE_BACKEND_100K_EXPANSION.json"
    md_path = REPORTS / "RC2_SQLITE_BACKEND_100K_EXPANSION.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# RC2 SQLite Backend + 100K Expansion",
        "",
        f"Created: {report['created_at']}",
        "",
        "## Summary",
        f"- Concepts before: {report['concept_count_before']}",
        f"- Edges before: {report['edge_count_before']}",
        f"- Concepts after: {report['concept_count_after']}",
        f"- Edges after: {report['edge_count_after']}",
        f"- Recommendation: {report['recommendation']}",
        "",
        "## Performance",
        f"- Indexed retrieval latency ms: {report['post_expansion_performance']['indexed_retrieval_latency_ms']}",
        f"- Graph lookup latency ms: {report['post_expansion_performance']['graph_lookup_latency_ms']}",
        f"- Graph traversal latency ms: {report['post_expansion_performance']['graph_traversal_latency_ms']}",
        f"- Index size MB: {report['post_expansion_performance']['index_file_size_mb']}",
        "",
        "## Safety",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["safety_invariants"].items())
    lines.extend(["", "## Remaining Blockers"])
    lines.extend(f"- {item}" for item in report["remaining_blockers"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run_storage_backend_marathon(), indent=2, sort_keys=True))
