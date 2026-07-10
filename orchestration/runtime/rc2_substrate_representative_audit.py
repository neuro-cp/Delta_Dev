"""Representative audit for the RC2 100k SQLite substrate.

This module measures whether visible duplicate-looking concepts are a UI
ordering artifact, localized template pollution, or broader substrate
contamination. It is read-only: no quarantine, deletion, rollback, provider
call, training, or canonical mutation is performed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime import rc2_sqlite_substrate as sqlite_backend


REPORT_JSON = ROOT / "reports" / "RC2_100K_SUBSTRATE_REPRESENTATIVE_AUDIT.json"
REPORT_MD = ROOT / "reports" / "RC2_100K_SUBSTRATE_REPRESENTATIVE_AUDIT.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "canonical_memory_mutated": False,
    "stores_deleted_or_reset": False,
    "substrate_expansion_continued": False,
    "quarantine_performed": False,
    "delta_75_push_performed": False,
}

TEMPLATE_PHRASES = (
    "reusable",
    "helps explain causes, constraints, tradeoffs",
    "with explicit attention to evidence, constraints, and operator review",
    "connects observable situations to underlying",
    "comparing evidence, identifying constraints, and choosing next questions",
    "supports cross-domain retrieval only as noncanonical substrate knowledge",
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def semantic_stem(name: str) -> str:
    stem = normalize_text(re.sub(r"\([^)]*\)", " ", str(name or "")))
    stem = re.sub(r"\bpattern\s+\d+\b", "pattern", stem)
    stem = re.sub(r"\bcycle\s+\d+\b", "cycle", stem)
    stem = re.sub(r"\bvariant\s+\d+\b", "variant", stem)
    stem = re.sub(r"\bpass\s+\d+\b", "pass", stem)
    stem = re.sub(r"\b\d+\b", " ", stem)
    return " ".join(stem.split())


def definition_template(text: str, concept_name: str, domain: str) -> str:
    normalized = normalize_text(text)
    for removable in (concept_name, domain, semantic_stem(concept_name), domain.replace("_", " ")):
        token = normalize_text(removable)
        if token:
            normalized = normalized.replace(token, "<slot>")
    normalized = re.sub(r"\bpattern\s+\d+\b", "pattern", normalized)
    normalized = re.sub(r"\b\d+\b", "<num>", normalized)
    normalized = re.sub(r"\b[a-f0-9]{8,}\b", "<id>", normalized)
    return " ".join(normalized.split())


def _list_text(values: Any) -> str:
    if isinstance(values, list):
        return " ".join(str(item) for item in values)
    return str(values or "")


def concept_quality_flags(concept: dict[str, Any]) -> set[str]:
    flags: set[str] = set()
    name = str(concept.get("concept_name") or "")
    domain = str(concept.get("domain") or "")
    definition = str(concept.get("short_definition") or "")
    propositions = _list_text(concept.get("propositions"))
    related = concept.get("related_concepts") or []
    source_type = str(concept.get("source_type") or "")
    combined = normalize_text(f"{name} {definition} {propositions}")

    if re.search(r"\bpattern\s+\d+\b", name.lower()):
        flags.add("pattern_number_name")
    if source_type == "rc2_sqlite_curated_expansion":
        flags.add("sqlite_expansion_source")
    if "describes how" in combined and "with explicit attention to evidence constraints and operator review" in combined:
        flags.add("generated_pattern_definition")
    if sum(1 for phrase in TEMPLATE_PHRASES if phrase in combined) >= 2:
        flags.add("template_language")
    if "reusable" in normalize_text(definition) and "domain" in normalize_text(definition):
        flags.add("generic_definition")
    if isinstance(related, list) and related:
        normalized_related = {normalize_text(item) for item in related}
        generic_related = {
            normalize_text(f"{domain} reasoning"),
            normalize_text(f"{domain} evidence"),
            normalize_text(f"{domain} tradeoffs"),
            normalize_text(f"{domain} applications"),
            normalize_text(f"{domain} uncertainty"),
        }
        if len(normalized_related & generic_related) >= 4:
            flags.add("generic_related_concepts")
    if len(set(normalize_text(propositions).split())) < 18:
        flags.add("weak_semantic_density")
    if "pattern_number_name" in flags and "sqlite_expansion_source" in flags:
        flags.add("scaffold_not_real_concept")
    if len(flags & {"pattern_number_name", "template_language", "generic_definition", "generic_related_concepts", "generated_pattern_definition"}) >= 2:
        flags.add("scaffold_not_real_concept")
    return flags


def _deterministic_sample(rows: list[dict[str, Any]], limit: int, salt: str) -> list[dict[str, Any]]:
    keyed = []
    for row in rows:
        key = hashlib.sha256(f"{salt}:{row.get('concept_id')}:{row.get('concept_name')}".encode()).hexdigest()
        keyed.append((key, row))
    return [row for _key, row in sorted(keyed)[:limit]]


def _quality_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "sample_size": 0,
            "weak_or_template": 0,
            "weak_or_template_ratio": 0.0,
            "distinct_domains": 0,
            "example_names": [],
        }
    weak = 0
    domains: set[str] = set()
    examples = []
    for row in rows:
        concept = _loads(row.get("raw_json")) or dict(row)
        flags = concept_quality_flags(concept)
        if flags & {"scaffold_not_real_concept", "template_language", "generic_definition", "generic_related_concepts"}:
            weak += 1
        domains.add(str(row.get("domain") or concept.get("domain") or ""))
        if len(examples) < 8:
            examples.append(str(row.get("concept_name") or concept.get("concept_name") or ""))
    return {
        "sample_size": len(rows),
        "weak_or_template": weak,
        "weak_or_template_ratio": round(weak / len(rows), 4),
        "distinct_domains": len({domain for domain in domains if domain}),
        "example_names": examples,
    }


def _load_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(
        """
        SELECT concept_id, concept_name, normalized_name, domain, concept_type,
               short_definition, quality_score, source_type, source_question, raw_json
        FROM concepts
        """
    )]


def _audit_duplicate_groups(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact = Counter(normalize_text(row["concept_name"]) for row in rows)
    exact_duplicate_groups = {name: count for name, count in exact.items() if count > 1}

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("domain") or ""), semantic_stem(str(row.get("concept_name") or "")))].append(row)

    near_groups = []
    clone_count = 0
    for (domain, stem), members in groups.items():
        if len(members) < 2:
            continue
        templates = Counter()
        flag_counts = Counter()
        for member in members:
            concept = _loads(member.get("raw_json")) or member
            templates[definition_template(str(member.get("short_definition") or ""), str(member.get("concept_name") or ""), domain)] += 1
            flag_counts.update(concept_quality_flags(concept))
        dominant_template_count = templates.most_common(1)[0][1] if templates else 0
        pattern_members = sum(1 for member in members if re.search(r"\bpattern\s+\d+\b", str(member.get("concept_name") or "").lower()))
        group_is_clone_like = (
            pattern_members >= 2
            or dominant_template_count / len(members) >= 0.75
            or flag_counts.get("scaffold_not_real_concept", 0) / len(members) >= 0.5
        )
        if group_is_clone_like:
            clone_count += max(0, len(members) - 1)
            near_groups.append({
                "domain": domain,
                "semantic_stem": stem,
                "size": len(members),
                "pattern_members": pattern_members,
                "dominant_template_ratio": round(dominant_template_count / len(members), 4),
                "sample_names": [str(member.get("concept_name") or "") for member in members[:8]],
            })
    near_groups.sort(key=lambda item: (-int(item["size"]), str(item["domain"]), str(item["semantic_stem"])))
    return {
        "exact_duplicate_name_groups": len(exact_duplicate_groups),
        "exact_duplicate_concepts": sum(count - 1 for count in exact_duplicate_groups.values()),
        "near_duplicate_groups": len(near_groups),
        "near_duplicate_clone_concepts": clone_count,
        "largest_near_duplicate_groups": near_groups[:20],
    }


def _audit_samples(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> dict[str, Any]:
    default_first = [dict(row) for row in conn.execute(
        "SELECT concept_id, concept_name, domain, raw_json FROM concepts ORDER BY concept_name LIMIT 100"
    )]
    default_late = [dict(row) for row in conn.execute(
        "SELECT concept_id, concept_name, domain, raw_json FROM concepts ORDER BY concept_name LIMIT 100 OFFSET 900"
    )]
    random_sample = _deterministic_sample(rows, 250, "representative")
    keyword_terms = ["science", "law", "energy", "photosynthesis", "software architecture", "planning"]
    keyword_samples = {}
    for term in keyword_terms:
        result = sqlite_backend.search_concepts_sqlite(term, limit=25)
        keyword_samples[term] = _quality_summary([
            {
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "raw_json": json.dumps(item, sort_keys=True),
            }
            for item in result.get("matches", [])
        ])
    per_domain_rows = []
    for row in conn.execute("SELECT DISTINCT domain FROM concepts ORDER BY domain"):
        domain = row["domain"]
        domain_rows = [dict(item) for item in conn.execute(
            """
            SELECT concept_id, concept_name, domain, raw_json
            FROM concepts
            WHERE domain = ?
            ORDER BY quality_score DESC, concept_name
            LIMIT 5
            """,
            (domain,),
        )]
        per_domain_rows.extend(domain_rows)
    high_degree_rows = [dict(row) for row in conn.execute(
        """
        SELECT c.concept_id, c.concept_name, c.domain, c.raw_json, COUNT(ga.edge_id) AS degree
        FROM concepts c
        JOIN graph_adjacency ga ON ga.concept_id = c.concept_id
        GROUP BY c.concept_id
        ORDER BY degree DESC, c.quality_score DESC, c.concept_name
        LIMIT 100
        """
    )]
    return {
        "default_alphabetical_first_page": _quality_summary(default_first),
        "default_alphabetical_late_page": _quality_summary(default_late),
        "random_sample": _quality_summary(random_sample),
        "keyword_search_samples": keyword_samples,
        "per_domain_top_quality_sample": _quality_summary(per_domain_rows),
        "high_degree_sample": _quality_summary(high_degree_rows),
    }


def _audit_graph(conn: sqlite3.Connection, weak_ids: set[str]) -> dict[str, Any]:
    total_edges = int(conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0])
    duplicate_edge_groups = int(conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT source_concept_id, target_concept_id, relation_type, COUNT(*) c
            FROM graph_edges
            GROUP BY source_concept_id, target_concept_id, relation_type
            HAVING c > 1
        )
        """
    ).fetchone()[0])
    weak_edge_count = 0
    if weak_ids:
        placeholders = ",".join("?" for _ in weak_ids)
        weak_edge_count = int(conn.execute(
            f"""
            SELECT COUNT(*) FROM graph_edges
            WHERE source_concept_id IN ({placeholders})
               OR target_concept_id IN ({placeholders})
            """,
            tuple(weak_ids) + tuple(weak_ids),
        ).fetchone()[0])
    return {
        "total_graph_edges": total_edges,
        "duplicate_edge_groups": duplicate_edge_groups,
        "edges_connected_to_weak_or_template_concepts": weak_edge_count,
        "edge_contamination_ratio": round(weak_edge_count / total_edges, 4) if total_edges else 0.0,
        "usable_edge_estimate": max(0, total_edges - weak_edge_count),
    }


def build_audit(write_reports: bool = True) -> dict[str, Any]:
    conn = sqlite_backend.connect()
    sqlite_backend.ensure_schema(conn)
    rows = _load_rows(conn)
    total = len(rows)

    source_counts = Counter(str(row.get("source_type") or "") for row in rows)
    domain_counts = Counter(str(row.get("domain") or "") for row in rows)
    weak_flags = Counter()
    weak_ids: set[str] = set()
    rich_estimate = 0
    for row in rows:
        concept = _loads(row.get("raw_json")) or row
        flags = concept_quality_flags(concept)
        weak_flags.update(flags)
        weak = bool(flags & {"scaffold_not_real_concept", "template_language", "generic_definition", "generic_related_concepts"})
        if weak:
            weak_ids.add(str(row["concept_id"]))
        else:
            rich_estimate += 1

    duplicate_audit = _audit_duplicate_groups(rows)
    samples = _audit_samples(conn, rows)
    graph = _audit_graph(conn, weak_ids)
    conn.close()

    weak_count = len(weak_ids)
    unique_semantic_estimate = max(0, total - int(duplicate_audit["near_duplicate_clone_concepts"]))
    usable_estimate = max(0, total - max(weak_count, int(duplicate_audit["near_duplicate_clone_concepts"])))
    weak_ratio = weak_count / total if total else 0.0
    clone_ratio = int(duplicate_audit["near_duplicate_clone_concepts"]) / total if total else 0.0
    if weak_ratio >= 0.35 or clone_ratio >= 0.25:
        classification = "mixed_substrate_with_widespread_template_pollution"
        recommendation = "REBUILD_EXPANSION_GENERATOR"
    elif weak_ratio >= 0.15 or clone_ratio >= 0.10:
        classification = "mixed_substrate_with_rich_and_weak_regions"
        recommendation = "QUARANTINE_TEMPLATE_EXPANSION"
    elif samples["default_alphabetical_late_page"]["weak_or_template_ratio"] > samples["random_sample"]["weak_or_template_ratio"] * 2:
        classification = "ui_default_ordering_problem_with_localized_template_clusters"
        recommendation = "FIX_DATABASE_DEFAULT_VIEW"
    else:
        classification = "mostly_usable_substrate_with_localized_cleanup_needed"
        recommendation = "KEEP_100K_SUBSTRATE"

    report = {
        "report": "RC2_100K_SUBSTRATE_REPRESENTATIVE_AUDIT",
        "created_at": _now(),
        "audit_mode": "read_only_representative_audit",
        "classification": classification,
        "recommendation": recommendation,
        "total_concepts": total,
        "source_counts": dict(source_counts.most_common()),
        "top_domain_counts": dict(domain_counts.most_common(20)),
        "unique_semantic_concept_estimate": unique_semantic_estimate,
        "rich_concept_estimate": rich_estimate,
        "weak_or_template_concept_estimate": weak_count,
        "weak_or_template_ratio": round(weak_ratio, 4),
        "usable_concept_estimate": usable_estimate,
        "duplicate_ratio": round(clone_ratio, 4),
        "quality_flag_counts": dict(weak_flags.most_common()),
        "duplicate_audit": duplicate_audit,
        "sample_quality": samples,
        "graph_audit": graph,
        "database_default_view": {
            "previous_behavior": "ORDER BY concept_name, which clusters domain/topic/template neighbors",
            "recommended_behavior": "diversified representative concepts across domains and sources",
        },
        "safety": SAFETY,
    }
    if write_reports:
        write_audit_reports(report)
    return report


def write_audit_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    largest = report["duplicate_audit"]["largest_near_duplicate_groups"][:8]
    lines = [
        "# RC2 100K Substrate Representative Audit",
        "",
        f"Created: {report['created_at']}",
        f"Mode: {report['audit_mode']}",
        f"Classification: {report['classification']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Counts",
        "",
        f"- Total concepts: {report['total_concepts']}",
        f"- Unique semantic estimate: {report['unique_semantic_concept_estimate']}",
        f"- Usable concept estimate: {report['usable_concept_estimate']}",
        f"- Rich concept estimate: {report['rich_concept_estimate']}",
        f"- Weak/template concept estimate: {report['weak_or_template_concept_estimate']}",
        f"- Duplicate ratio estimate: {report['duplicate_ratio']}",
        "",
        "## Duplicate Audit",
        "",
        f"- Exact duplicate name groups: {report['duplicate_audit']['exact_duplicate_name_groups']}",
        f"- Exact duplicate concepts: {report['duplicate_audit']['exact_duplicate_concepts']}",
        f"- Near-duplicate groups: {report['duplicate_audit']['near_duplicate_groups']}",
        f"- Near-duplicate clone concepts: {report['duplicate_audit']['near_duplicate_clone_concepts']}",
        "",
        "## Largest Near-Duplicate Groups",
        "",
    ]
    for group in largest:
        lines.extend([
            f"### {group['semantic_stem']} ({group['domain']})",
            f"- Size: {group['size']}",
            f"- Pattern members: {group['pattern_members']}",
            f"- Dominant template ratio: {group['dominant_template_ratio']}",
            "- Samples:",
            *[f"  - {name}" for name in group["sample_names"][:5]],
            "",
        ])
    lines.extend([
        "## Sample Quality",
        "",
        "```json",
        json.dumps(report["sample_quality"], indent=2, sort_keys=True),
        "```",
        "",
        "## Graph Audit",
        "",
        "```json",
        json.dumps(report["graph_audit"], indent=2, sort_keys=True),
        "```",
        "",
        "## Safety",
        "",
        "No deletion, quarantine, rollback, training, provider call, canonical mutation, or expansion was performed.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_audit(write_reports=True)
    print(json.dumps({
        "classification": report["classification"],
        "recommendation": report["recommendation"],
        "total_concepts": report["total_concepts"],
        "usable_concept_estimate": report["usable_concept_estimate"],
        "weak_or_template_concept_estimate": report["weak_or_template_concept_estimate"],
        "duplicate_ratio": report["duplicate_ratio"],
        "edge_contamination_ratio": report["graph_audit"]["edge_contamination_ratio"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
