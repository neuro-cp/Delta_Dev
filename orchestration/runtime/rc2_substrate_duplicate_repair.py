"""Remove RC2 SQLite template clone concepts while preserving an audit backup.

This is an explicit cleanup pass for the 100k SQLite expansion. It removes
semantically duplicated Pattern clone rows from the runtime SQLite index,
keeps one representative per semantic group, removes graph edges connected to
removed concepts, and writes an audit report. It does not touch canonical
memory, model weights, providers, DELTA-75, or JSONL source stores.
"""

from __future__ import annotations

import json
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
from orchestration.runtime.rc2_substrate_representative_audit import (
    concept_quality_flags,
    definition_template,
    semantic_stem,
)


REPORT_JSON = ROOT / "reports" / "RC2_100K_SUBSTRATE_DUPLICATE_REPAIR.json"
REPORT_MD = ROOT / "reports" / "RC2_100K_SUBSTRATE_DUPLICATE_REPAIR.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "canonical_memory_mutated": False,
    "jsonl_source_store_mutated": False,
    "delta_75_push_performed": False,
    "substrate_expansion_continued": False,
}


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


def _chunked(values: list[str], size: int = 700) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def _load_concept_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(
        """
        SELECT concept_id, concept_name, domain, short_definition, quality_score,
               source_type, created_at, raw_json
        FROM concepts
        """
    )]


def _clone_group(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 2:
        return False
    templates = Counter()
    pattern_members = 0
    scaffold_members = 0
    for row in rows:
        concept = _loads(row.get("raw_json")) or row
        name = str(row.get("concept_name") or "")
        domain = str(row.get("domain") or "")
        if " pattern " in f" {name.lower()} ":
            pattern_members += 1
        if "scaffold_not_real_concept" in concept_quality_flags(concept):
            scaffold_members += 1
        templates[definition_template(str(row.get("short_definition") or ""), name, domain)] += 1
    dominant_template = templates.most_common(1)[0][1] if templates else 0
    return (
        pattern_members >= 2
        or dominant_template / len(rows) >= 0.75
        or scaffold_members / len(rows) >= 0.5
    )


def _representative_key(row: dict[str, Any]) -> tuple[int, int, float, int, str]:
    name = str(row.get("concept_name") or "")
    source = str(row.get("source_type") or "")
    has_pattern = 1 if " pattern " in f" {name.lower()} " else 0
    sqlite_source = 1 if source == "rc2_sqlite_curated_expansion" else 0
    quality = float(row.get("quality_score") or 0.0)
    return (has_pattern, sqlite_source, -quality, len(name), name)


def plan_duplicate_removal(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = _load_concept_rows(conn)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("domain") or ""), semantic_stem(str(row.get("concept_name") or "")))].append(row)

    remove_ids: set[str] = set()
    representatives: dict[str, str] = {}
    affected_groups = []
    for (domain, stem), members in groups.items():
        if not _clone_group(members):
            continue
        representative = sorted(members, key=_representative_key)[0]
        representative_id = str(representative["concept_id"])
        group_remove = [str(member["concept_id"]) for member in members if str(member["concept_id"]) != representative_id]
        if not group_remove:
            continue
        remove_ids.update(group_remove)
        group_id = f"{domain}:{stem}"
        representatives[group_id] = representative_id
        affected_groups.append({
            "group_id": group_id,
            "domain": domain,
            "semantic_stem": stem,
            "size_before": len(members),
            "representative_concept_id": representative_id,
            "representative_name": representative.get("concept_name"),
            "removed_count": len(group_remove),
            "sample_removed_names": [member.get("concept_name") for member in members if str(member["concept_id"]) != representative_id][:6],
        })
    affected_groups.sort(key=lambda item: (-int(item["removed_count"]), str(item["group_id"])))
    residual_scaffold_ids = []
    for row in rows:
        concept = _loads(row.get("raw_json")) or row
        flags = concept_quality_flags(concept)
        if flags & {"scaffold_not_real_concept", "template_language", "generic_definition", "generic_related_concepts"}:
            residual_scaffold_ids.append(str(row["concept_id"]))
    return {
        "remove_ids": sorted(remove_ids),
        "residual_scaffold_ids": sorted(set(residual_scaffold_ids) - remove_ids),
        "affected_groups": affected_groups,
        "representatives": representatives,
        "concept_count_before": len(rows),
    }


def _delete_by_ids(conn: sqlite3.Connection, table: str, column: str, ids: list[str]) -> int:
    deleted = 0
    for chunk in _chunked(ids):
        placeholders = ",".join("?" for _ in chunk)
        cursor = conn.execute(f"DELETE FROM {table} WHERE {column} IN ({placeholders})", tuple(chunk))
        deleted += cursor.rowcount if cursor.rowcount is not None else 0
    return deleted


def _edge_ids_for_removed_concepts(conn: sqlite3.Connection, remove_ids: list[str]) -> list[str]:
    edge_ids: set[str] = set()
    for chunk in _chunked(remove_ids):
        placeholders = ",".join("?" for _ in chunk)
        for row in conn.execute(
            f"""
            SELECT edge_id FROM graph_edges
            WHERE source_concept_id IN ({placeholders})
               OR target_concept_id IN ({placeholders})
            """,
            tuple(chunk) + tuple(chunk),
        ):
            edge_ids.add(str(row["edge_id"]))
    return sorted(edge_ids)


def repair_duplicate_substrate(db_path: Path = sqlite_backend.DB_PATH, *, write_reports: bool = True) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite substrate not found: {db_path}")
    backup_path = db_path.with_name(f"{db_path.stem}.pre_duplicate_repair_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}{db_path.suffix}")
    source = sqlite3.connect(db_path)
    backup = sqlite3.connect(backup_path)
    try:
        source.backup(backup)
    finally:
        backup.close()
        source.close()

    conn = sqlite_backend.connect(db_path)
    sqlite_backend.ensure_schema(conn)
    before = sqlite_backend.sqlite_counts(conn)
    plan = plan_duplicate_removal(conn)
    remove_ids = sorted(set(plan["remove_ids"]) | set(plan["residual_scaffold_ids"]))
    edge_ids = _edge_ids_for_removed_concepts(conn, remove_ids)

    deleted = {}
    with conn:
        deleted["concept_keywords"] = _delete_by_ids(conn, "concept_keywords", "concept_id", remove_ids)
        deleted["concept_related"] = _delete_by_ids(conn, "concept_related", "concept_id", remove_ids)
        deleted["concept_propositions"] = _delete_by_ids(conn, "concept_propositions", "concept_id", remove_ids)
        deleted["graph_adjacency_removed_concepts"] = _delete_by_ids(conn, "graph_adjacency", "concept_id", remove_ids)
        deleted["graph_adjacency_removed_edges"] = _delete_by_ids(conn, "graph_adjacency", "edge_id", edge_ids)
        deleted["graph_edges"] = _delete_by_ids(conn, "graph_edges", "edge_id", edge_ids)
        deleted["concept_replay_events"] = _delete_by_ids(conn, "substrate_replay_events", "target_id", remove_ids)
        deleted["edge_replay_events"] = _delete_by_ids(conn, "substrate_replay_events", "target_id", edge_ids)
        deleted["concepts"] = _delete_by_ids(conn, "concepts", "concept_id", remove_ids)
        sqlite_backend._audit(conn, "sqlite_template_duplicate_removal", before["concepts"] - len(remove_ids), before["graph_edges"] - len(edge_ids), {
            "backup_path": str(backup_path),
            "removed_concepts": len(remove_ids),
            "removed_graph_edges": len(edge_ids),
            "affected_duplicate_groups": len(plan["affected_groups"]),
            "representatives_kept": len(plan["representatives"]),
            "no_jsonl_mutation": True,
            "no_canonical_mutation": True,
        })
    after = sqlite_backend.sqlite_counts(conn)
    replay = sqlite_backend.replay_coverage(conn)
    conn.close()

    report = {
        "report": "RC2_100K_SUBSTRATE_DUPLICATE_REPAIR",
        "created_at": _now(),
        "status": "completed",
        "backup_path": str(backup_path),
        "before": before,
        "after": after,
        "removed_concepts": len(remove_ids),
        "removed_clone_concepts": len(plan["remove_ids"]),
        "removed_residual_scaffold_concepts": len(plan["residual_scaffold_ids"]),
        "removed_graph_edges": len(edge_ids),
        "duplicate_groups_repaired": len(plan["affected_groups"]),
        "representatives_kept": len(plan["representatives"]),
        "deleted_rows_by_table": deleted,
        "largest_repaired_groups": plan["affected_groups"][:20],
        "replay_coverage_after": replay,
        "effective_working_substrate": {
            "concepts": after["concepts"],
            "graph_edges": after["graph_edges"],
            "runtime_duplicates_removed": True,
            "source_backup_preserved": True,
        },
        "safety": SAFETY,
        "recommendation": "READY_FOR_GENERATOR_REBUILD_VALIDATION",
    }
    if write_reports:
        write_reports_file(report)
    return report


def write_reports_file(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 100K Substrate Duplicate Repair",
        "",
        f"Created: {report['created_at']}",
        f"Status: {report['status']}",
        f"Backup: `{report['backup_path']}`",
        "",
        "## Summary",
        "",
        f"- Concepts before: {report['before']['concepts']}",
        f"- Concepts after: {report['after']['concepts']}",
        f"- Removed duplicate concepts: {report['removed_concepts']}",
        f"- Removed clone concepts: {report['removed_clone_concepts']}",
        f"- Removed residual scaffold representatives: {report['removed_residual_scaffold_concepts']}",
        f"- Graph edges before: {report['before']['graph_edges']}",
        f"- Graph edges after: {report['after']['graph_edges']}",
        f"- Removed graph edges: {report['removed_graph_edges']}",
        f"- Duplicate groups repaired: {report['duplicate_groups_repaired']}",
        f"- Representatives kept: {report['representatives_kept']}",
        "",
        "## Largest Repaired Groups",
        "",
    ]
    for group in report["largest_repaired_groups"][:10]:
        lines.extend([
            f"### {group['semantic_stem']} ({group['domain']})",
            f"- Size before: {group['size_before']}",
            f"- Removed: {group['removed_count']}",
            f"- Kept: {group['representative_name']} (`{group['representative_concept_id']}`)",
            "",
        ])
    lines.extend([
        "## Safety",
        "",
        "No training, provider call, canonical write, JSONL source mutation, DELTA-75 push, or substrate expansion was performed.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = repair_duplicate_substrate(write_reports=True)
    print(json.dumps({
        "status": report["status"],
        "before": report["before"],
        "after": report["after"],
        "removed_concepts": report["removed_concepts"],
        "removed_graph_edges": report["removed_graph_edges"],
        "duplicate_groups_repaired": report["duplicate_groups_repaired"],
        "backup_path": report["backup_path"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
