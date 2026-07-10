"""RC2 cognitive state reconciliation and substrate integrity report.

This module defines the vocabulary for DELTA's substrate counters. It is
read-only: it does not repair, expand, replay, train, call providers, or write
canonical memory.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime import rc2_sqlite_substrate as sqlite_backend
from orchestration.runtime.rc2_developmental_concept_memory import (
    build_developmental_memory_state,
    load_approved_concepts,
)
from orchestration.runtime.rc2_governed_semantic_graph import load_approved_graph_edges


REPORT_JSON = ROOT / "reports" / "RC2_SUBSTRATE_RECONCILIATION.json"
REPORT_MD = ROOT / "reports" / "RC2_SUBSTRATE_RECONCILIATION.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
    "delta_75_push_performed": False,
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _sqlite_event_breakdown() -> dict[str, Any]:
    if not sqlite_backend.DB_PATH.exists():
        return {
            "migration_audit_events": 0,
            "migration_audit_by_type": {},
            "replay_status_by_type": {},
            "replay_event_type_counts": {},
        }
    conn = sqlite_backend.connect()
    sqlite_backend.ensure_schema(conn)
    migration_by_type = {
        str(row["event_type"]): int(row["count"])
        for row in conn.execute("SELECT event_type, COUNT(*) AS count FROM migration_audit GROUP BY event_type")
    }
    replay_status = {
        str(row["status"]): int(row["count"])
        for row in conn.execute("SELECT status, COUNT(*) AS count FROM substrate_replay_events GROUP BY status")
    }
    replay_event_types = {
        str(row["event_type"]): int(row["count"])
        for row in conn.execute("SELECT event_type, COUNT(*) AS count FROM substrate_replay_events GROUP BY event_type")
    }
    conn.close()
    return {
        "migration_audit_events": sum(migration_by_type.values()),
        "migration_audit_by_type": migration_by_type,
        "replay_status_by_type": replay_status,
        "replay_event_type_counts": replay_event_types,
    }


def build_substrate_reconciliation(write_reports: bool = False) -> dict[str, Any]:
    health = sqlite_backend.backend_health()
    sqlite_counts = health.get("counts", {}) if health.get("sqlite_available") else {}
    replay = health.get("replay_coverage", {}) if health.get("sqlite_available") else {}
    jsonl_counts = health.get("jsonl_counts", {}) if health.get("sqlite_available") else {
        "concepts": len(load_approved_concepts()),
        "graph_edges": len(load_approved_graph_edges()),
    }
    developmental = build_developmental_memory_state()
    events = _sqlite_event_breakdown()

    active_runtime_concepts = int(sqlite_counts.get("concepts", jsonl_counts.get("concepts", 0)) or 0)
    active_graph_edges = int(sqlite_counts.get("graph_edges", jsonl_counts.get("graph_edges", 0)) or 0)
    replay_events = int(replay.get("total_replay_events", 0) or 0)
    concept_replay_events = int(replay.get("concept_replay_events", 0) or 0)
    edge_replay_events = int(replay.get("edge_replay_events", 0) or 0)
    legacy_jsonl_concepts = int(jsonl_counts.get("concepts", 0) or 0)
    legacy_jsonl_edges = int(jsonl_counts.get("graph_edges", 0) or 0)

    counters = [
        {
            "counter": "active_runtime_concepts",
            "value": active_runtime_concepts,
            "source": "SQLite concepts table" if health.get("sqlite_available") else "JSONL fallback",
            "meaning": "Authoritative active concept rows available to runtime retrieval/WRS.",
            "includes": ["approved_noncanonical runtime concepts"],
            "excludes": ["canonical memory", "provider knowledge", "training artifacts"],
            "authoritative_for_runtime": True,
        },
        {
            "counter": "active_graph_edges",
            "value": active_graph_edges,
            "source": "SQLite graph_edges table" if health.get("sqlite_available") else "JSONL fallback",
            "meaning": "Approved noncanonical graph edges available to graph-assisted retrieval.",
            "includes": ["approved_noncanonical graph edges"],
            "excludes": ["candidate edges", "rolled-back edges", "canonical graph writes"],
            "authoritative_for_runtime": True,
        },
        {
            "counter": "substrate_replay_events",
            "value": replay_events,
            "source": "SQLite substrate_replay_events table",
            "meaning": "Replay-review/audit events derived from indexed concepts and graph edges; not a concept total.",
            "includes": ["concept replay review events", "graph edge replay review events"],
            "excludes": ["raw concept rows as separate concepts"],
            "authoritative_for_runtime": False,
        },
        {
            "counter": "concept_replay_events",
            "value": concept_replay_events,
            "source": "SQLite substrate_replay_events where target_type='concept'",
            "meaning": "Replay-review events corresponding to active concept rows.",
            "includes": ["one replay-review event per indexed active concept when coverage is complete"],
            "excludes": ["graph-edge replay events"],
            "authoritative_for_runtime": False,
        },
        {
            "counter": "graph_edge_replay_events",
            "value": edge_replay_events,
            "source": "SQLite substrate_replay_events where target_type='graph_edge'",
            "meaning": "Replay-review events corresponding to active graph edge rows.",
            "includes": ["one replay-review event per indexed active graph edge when coverage is complete"],
            "excludes": ["concept replay events"],
            "authoritative_for_runtime": False,
        },
        {
            "counter": "legacy_jsonl_concepts",
            "value": legacy_jsonl_concepts,
            "source": "legacy JSONL approved concept stores",
            "meaning": "Historical/audit source records, not the primary runtime count when SQLite is available.",
            "includes": ["approved noncanonical JSONL concepts"],
            "excludes": ["SQLite-only repaired/cleaned runtime rows"],
            "authoritative_for_runtime": not bool(health.get("sqlite_available")),
        },
        {
            "counter": "legacy_jsonl_graph_edges",
            "value": legacy_jsonl_edges,
            "source": "legacy JSONL graph edge store",
            "meaning": "Historical/audit source graph edges, not the primary runtime edge count when SQLite is available.",
            "includes": ["approved noncanonical JSONL graph edges"],
            "excludes": ["SQLite-only repaired/cleaned runtime rows"],
            "authoritative_for_runtime": not bool(health.get("sqlite_available")),
        },
        {
            "counter": "developmental_memory_records",
            "value": int(developmental.get("knowledge_memory_records", 0) or 0),
            "source": "developmental memory state",
            "meaning": "Legacy local developmental memory count. This is diagnostic, not the canonical runtime substrate count.",
            "includes": ["local approved developmental-memory records"],
            "excludes": ["SQLite-only substrate rows"],
            "authoritative_for_runtime": False,
        },
        {
            "counter": "migration_audit_events",
            "value": int(events["migration_audit_events"]),
            "source": "SQLite migration_audit table",
            "meaning": "Backend migration/repair/cleanup events. This is operational history, not a concept count.",
            "includes": ["rebuild", "repair", "duplicate cleanup", "replay sync events"],
            "excludes": ["runtime concept rows"],
            "authoritative_for_runtime": False,
        },
    ]

    ui_display = {
        "knowledge_available": active_runtime_concepts > 0,
        "active_runtime_concepts": active_runtime_concepts,
        "active_graph_edges": active_graph_edges,
        "substrate_replay_events": replay_events,
        "concept_replay_events": concept_replay_events,
        "graph_edge_replay_events": edge_replay_events,
        "migration_audit_events": int(events["migration_audit_events"]),
        "legacy_jsonl_concepts": legacy_jsonl_concepts,
        "legacy_jsonl_graph_edges": legacy_jsonl_edges,
        "backend": health.get("backend", "jsonl_fallback"),
        "sqlite_available": bool(health.get("sqlite_available")),
        "sqlite_fresh": bool(health.get("fresh")),
    }

    consistency = {
        "active_concepts_match_concept_replay_events": active_runtime_concepts == concept_replay_events if replay_events else None,
        "active_edges_match_edge_replay_events": active_graph_edges == edge_replay_events if replay_events else None,
        "runtime_uses_single_authoritative_concept_count": True,
        "ui_header_should_display": "active_runtime_concepts",
        "database_should_display": "active_runtime_concepts",
        "wrs_should_retrieve_from": "storage_adapter_active_runtime_substrate",
    }

    report = {
        "report": "RC2_SUBSTRATE_RECONCILIATION",
        "created_at": _now(),
        "authoritative_runtime_concept_counter": "active_runtime_concepts",
        "authoritative_runtime_edge_counter": "active_graph_edges",
        "backend_health": health,
        "ui_display": ui_display,
        "counters": counters,
        "sqlite_event_breakdown": events,
        "consistency": consistency,
        "recommendation": "USE_ACTIVE_RUNTIME_CONCEPTS_FOR_UI_AND_WRS_DEFER_INSTILLATION_UNTIL_COUNTERS_STAY_RECONCILED",
        "safety": dict(SAFETY),
    }
    if write_reports:
        write_reconciliation_reports(report)
    return report


def write_reconciliation_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Substrate Reconciliation",
        "",
        f"Created: {report['created_at']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Authoritative Runtime Counters",
        "",
        f"- Active runtime concepts: {report['ui_display']['active_runtime_concepts']}",
        f"- Active graph edges: {report['ui_display']['active_graph_edges']}",
        f"- Substrate replay events: {report['ui_display']['substrate_replay_events']}",
        f"- Legacy JSONL concepts: {report['ui_display']['legacy_jsonl_concepts']}",
        f"- Legacy JSONL graph edges: {report['ui_display']['legacy_jsonl_graph_edges']}",
        "",
        "## Counter Reconciliation",
        "",
        "| Counter | Value | Source | Meaning | Runtime authoritative |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for row in report["counters"]:
        lines.append(
            f"| {row['counter']} | {row['value']} | {row['source']} | {row['meaning']} | {row['authoritative_for_runtime']} |"
        )
    lines.extend([
        "",
        "## Consistency",
        "",
    ])
    for key, value in report["consistency"].items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        "",
    ])
    for key, value in report["safety"].items():
        lines.append(f"- {key}: {value}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print(json.dumps(build_substrate_reconciliation(write_reports=True), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
