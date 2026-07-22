"""Read-only audit and campaign compiler for the authoritative RC2 concept store."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import re
from copy import deepcopy
from collections import Counter
from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.rc2_sqlite_substrate import DB_PATH


SEEDS = (
    "scalar", "vector", "vector addition", "scalar multiplication", "vector space",
    "linear combination", "span", "linear independence", "basis", "linear map", "matrix",
    "eigenvalue", "eigenvector", "inner product", "orthogonality", "orthonormal basis",
    "finite dimensionality", "self-adjoint operator", "diagonalization", "spectral theorem",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _connect_read_only(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def build_concept_memory_formalization_audit(db_path: Path = DB_PATH) -> dict[str, Any]:
    """Inspect the SQLite substrate without schema creation or database writes."""
    conn = _connect_read_only(db_path)
    tables = [str(row["name"]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    required = {"concepts", "concept_keywords", "concept_related", "concept_propositions", "graph_edges", "graph_adjacency", "substrate_replay_events", "migration_audit"}
    if not required.issubset(tables):
        raise ValueError("concept_memory_audit_missing_required_rc2_tables")
    counts = {name: int(conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]) for name in required}
    concept_columns = tuple(str(row["name"]) for row in conn.execute("PRAGMA table_info(concepts)"))
    statuses = tuple(dict(row) for row in conn.execute("SELECT approval_status, noncanonical, COUNT(*) AS count FROM concepts GROUP BY approval_status, noncanonical"))
    domains = tuple(dict(row) for row in conn.execute("SELECT domain, COUNT(*) AS count FROM concepts GROUP BY domain ORDER BY count DESC, domain"))
    duplicate_rows = tuple(dict(row) for row in conn.execute("SELECT normalized_name, COUNT(*) AS count, GROUP_CONCAT(concept_id) AS concept_ids FROM concepts GROUP BY normalized_name HAVING COUNT(*) > 1 ORDER BY count DESC, normalized_name"))
    seed_matches = []
    for seed in SEEDS:
        rows = [dict(row) for row in conn.execute("SELECT concept_id, concept_name, normalized_name, domain, concept_type, short_definition, confidence, quality_score, approval_status, rollback_handle, source_type FROM concepts WHERE lower(concept_name)=? OR lower(normalized_name)=? ORDER BY quality_score DESC, concept_id", (seed, seed.replace(" ", "")))]
        seed_matches.append({"seed": seed, "matches": tuple(rows), "classification": "missing" if not rows else "present_but_informal"})
    math_examples = tuple(dict(row) for row in conn.execute("SELECT concept_id, concept_name, concept_type, short_definition, confidence, quality_score FROM concepts WHERE domain='mathematics' ORDER BY concept_name LIMIT 50"))
    concepts = tuple(dict(row) for row in conn.execute("SELECT concept_id, concept_name, normalized_name, domain, concept_type, confidence, quality_score, approval_status, rollback_handle, created_at, source_type FROM concepts ORDER BY concept_id"))
    replays = tuple(dict(row) for row in conn.execute("SELECT replay_event_id, target_type, target_id, event_type, status, created_at FROM substrate_replay_events ORDER BY replay_event_id"))
    raw_key_counter: Counter[str] = Counter()
    raw_variant_counter: Counter[tuple[str, ...]] = Counter()
    for row in conn.execute("SELECT raw_json FROM concepts"):
        try:
            raw = json.loads(str(row["raw_json"]))
        except json.JSONDecodeError:
            raw = {}
        if isinstance(raw, dict):
            keys = tuple(sorted(str(key) for key in raw))
            raw_variant_counter[keys] += 1
            raw_key_counter.update(keys)
    metadata = {str(row["key"]): json.loads(str(row["value"])) for row in conn.execute("SELECT key, value FROM store_metadata")}
    conn.close()
    audit = {
        "audit_id": stable_id("concept-memory-formalization-audit", str(db_path), counts["concepts"], counts["substrate_replay_events"]),
        "audit_version": "concept_memory_formalization_audit_v1",
        "created_at": utc_now(),
        "read_only": True,
        "authoritative_store": {"owner": "rc2_sqlite_substrate", "location": str(db_path), "table": "concepts", "active_concept_count": counts["concepts"], "stable_id_field": "concept_id", "ui_count_reconciled": counts["concepts"] == 8979, "restart_persistence": "SQLite file-backed substrate"},
        "linked_subsystems": {"propositions": {"table": "concept_propositions", "count": counts["concept_propositions"], "join_key": "concept_id"}, "evidence": {"representation": "embedded raw_json/source fields plus proposition records", "separate_table": False}, "contradictions": {"representation": "not a dedicated SQLite table; runtime/validation subsystem", "count_in_store": None}, "replay_audit": {"table": "substrate_replay_events", "count": counts["substrate_replay_events"], "join_key": "target_id"}, "migration_audit": {"table": "migration_audit", "count": counts["migration_audit"], "join_key": "audit_id"}, "graph": {"tables": ("graph_edges", "graph_adjacency", "concept_related"), "edge_count": counts["graph_edges"]}},
        "schema": {"concept_columns": concept_columns, "raw_json_key_frequencies": dict(raw_key_counter), "raw_schema_variants": tuple({"fields": fields, "count": count} for fields, count in raw_variant_counter.most_common(20)), "approval_statuses": statuses, "domain_distribution": domains, "store_metadata": metadata},
        "catalog_assessment": "partially_structured_knowledge_graph_with_generated_associative_facets; not a formal mathematical knowledge graph",
        "quality_observations": {"normalized_name_duplicates": duplicate_rows, "duplicate_cleanup_candidates": (), "improper_or_low_formal_readiness_candidates": {"reason": "mathematics records are primarily generated domain facets and lack exact primitive matches", "sample": math_examples}, "conflicts": "no dedicated conflict field/table in the authoritative substrate"},
        "frontier": {"benchmark": "spectral_theorem", "seed_results": tuple(seed_matches), "selected_concept_ids": (), "status": "formal_primitives_missing_from_authoritative_concept_store", "notes": "No exact linear-algebra primitive records matched the seed labels; the future campaign must first formalize only records that actually exist or escalate for trusted acquisition."},
        "shareable_identifier_index": {"concepts": concepts, "replay_events": replays},
    }
    # The snapshot timestamp is report metadata, not semantic audit input.
    # Excluding it keeps campaign identity restart-safe for an unchanged store.
    audit["audit_digest"] = _digest({**audit, "created_at": ""})
    return audit


def compile_formalization_campaign(audit: dict[str, Any]) -> dict[str, Any]:
    """Compile one future campaign; it creates no overlays and changes no concepts."""
    campaign = {
        "campaign_id": stable_id("concept-memory-formalization-campaign", audit["audit_id"], audit["audit_digest"]),
        "mission": "formalize the retained linear-algebra prerequisite frontier for the spectral-theorem benchmark using existing memory and approved local deterministic checks only",
        "audit_id": audit["audit_id"], "audit_digest": audit["audit_digest"], "status": "pending_operator_campaign_authority",
        "overlay_schema": {"source_concept_id": "stable existing concept_id", "status": ("informal_only", "formalization_candidate", "partially_formalized", "formally_grounded", "behaviorally_validated", "conflicted", "deprecated"), "fields": ("aliases", "typed_entities", "symbols", "plain_language_definition", "formal_definition", "prerequisites", "dependents", "examples", "counterexamples", "evidence_refs", "unresolved_obligations", "validation_state", "mission_id", "overlay_version")},
        "budgets": {"maximum_active_concepts": 50, "maximum_downward_prerequisite_expansion": 30, "maximum_overlay_revisions_per_concept": 3, "maximum_local_executions": 250, "maximum_runtime_minutes": 180, "maximum_unresolved_conflicts": 15, "checkpoint_every_operations": 20, "maximum_working_artifacts": 500, "maximum_graph_depth": 8},
        "permitted_actions": ("read_authoritative_concept_store", "create_workspace_overlays", "resolve_aliases", "detect_duplicates", "record_conflicts", "infer_conservative_edges", "create_finite_examples", "run_local_deterministic_checks", "checkpoint_and_resume"),
        "escalation_boundaries": ("external_retrieval", "provider_or_api_use", "new_dependency_installation", "new_execution_capability", "tracked_source_mutation", "frontier_scope_expansion", "trusted_memory_admission", "capability_promotion", "material_ambiguity", "budget_exhaustion"),
        "authority_request": {"request_id": stable_id("concept-memory-formalization-campaign-authority", audit["audit_id"]), "request_kind": "concept_memory_formalization_campaign_authority", "status": "pending", "permitted_responses": ("approve_concept_memory_formalization_campaign", "reject_concept_memory_formalization_campaign", "defer_concept_memory_formalization_campaign", "ask_for_clarification"), "authority_scope": "one bounded linear-algebra formalization campaign using only authoritative existing RC2 concept memory and approved local deterministic checks", "authority_granted": False},
    }
    campaign["campaign_digest"] = _digest(campaign)
    return campaign


def consume_formalization_campaign_authority(campaign: dict[str, Any], response: str) -> dict[str, Any]:
    """Return a resolved campaign copy without rewriting its compiled request."""
    resolved = deepcopy(campaign)
    request = resolved["authority_request"]
    if request["status"] != "pending":
        raise ValueError("concept_memory_formalization_campaign_authority_not_pending")
    if response not in request["permitted_responses"]:
        raise ValueError("concept_memory_formalization_campaign_authority_response_invalid")
    request["status"] = "consumed"
    request["response"] = response
    request["authority_granted"] = response == "approve_concept_memory_formalization_campaign"
    request["consumed_at"] = utc_now()
    resolved["status"] = "campaign_authority_granted" if request["authority_granted"] else "campaign_authority_not_granted"
    resolved["compiled_campaign_digest"] = campaign["campaign_digest"]
    resolved["effective_campaign_digest"] = _digest({**resolved, "authority_request": {**request, "consumed_at": ""}})
    return resolved


def write_shareable_audit(audit: dict[str, Any], campaign: dict[str, Any], output_root: Path) -> tuple[Path, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "CONCEPT_MEMORY_FORMALIZATION_AUDIT.json"
    md_path = output_root / "CONCEPT_MEMORY_FORMALIZATION_AUDIT.md"
    json_path.write_text(json.dumps({"audit": audit, "campaign": campaign}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Concept Memory Formalization Audit", "", f"- Audit ID: `{audit['audit_id']}`", f"- Audit digest: `{audit['audit_digest']}`", f"- Store: `{audit['authoritative_store']['location']}`", f"- Active concepts: `{audit['authoritative_store']['active_concept_count']}`", f"- Campaign ID: `{campaign['campaign_id']}`", f"- Pending request: `{campaign['authority_request']['request_id']}`", "", "## Finding", "The SQLite substrate is authoritative, stable-ID keyed, and graph-linked, but its linear-algebra seed records are absent. The mathematics slice is primarily generated associative facets, not formally usable primitives.", "", "## Shareable Index", "The JSON companion contains compact identifiers for every active concept and replay event."]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def execute_formalization_campaign(*, audit: dict[str, Any], campaign: dict[str, Any], workspace: Path, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Create reversible workspace overlays; never write the RC2 substrate."""
    conn = _connect_read_only(db_path)
    rows = tuple(dict(row) for row in conn.execute("SELECT concept_id, concept_name, normalized_name, domain, concept_type, short_definition, confidence, quality_score, source_type, rollback_handle FROM concepts WHERE domain='mathematics' ORDER BY concept_id"))
    selected = []
    seen_subjects: set[str] = set()
    seed_terms = tuple(seed.split()[0] for seed in SEEDS)
    for row in rows:
        name = str(row["concept_name"] or "").lower()
        matched = next((term for term in seed_terms if re.search(rf"\b{re.escape(term)}", name)), "")
        if not matched or matched in seen_subjects:
            continue
        seen_subjects.add(matched)
        text = str(row.get("short_definition") or "").lower()
        generic = any(marker in text for marker in ("operator-reviewable uncertainty", "connecting", "describes how", "identifies how"))
        selected.append({"source_concept_id": row["concept_id"], "canonical_label": row["concept_name"], "seed_term": matched, "status": "informal_only" if generic else "formalization_candidate", "formal_definition": None, "typed_entities": (), "symbols": (), "prerequisite_links": (), "dependent_links": (), "examples": (), "counterexamples": (), "evidence_refs": (), "unresolved_obligations": ("derive a formal definition from independently grounded material",), "validation_state": "not_self_certified", "source_record_unchanged": True})
        if len(selected) >= int(campaign["budgets"]["maximum_active_concepts"]):
            break
    ids = tuple(item["source_concept_id"] for item in selected)
    placeholders = ",".join("?" for _ in ids)
    edges = tuple(dict(row) for row in conn.execute(f"SELECT edge_id, source_concept_id, target_concept_id, relation_type, confidence, uncertainty FROM graph_edges WHERE source_concept_id IN ({placeholders}) AND target_concept_id IN ({placeholders})", ids * 2)) if ids else ()
    conn.close()
    missing = tuple(seed["seed"] for seed in audit["frontier"]["seed_results"] if not seed["matches"])
    result = {"execution_id": stable_id("concept-memory-formalization-execution", campaign["campaign_id"], audit["audit_digest"]), "campaign_id": campaign["campaign_id"], "audit_id": audit["audit_id"], "workspace": str(workspace), "source_store_read_only": True, "overlays": tuple(selected), "existing_graph_edges": edges, "missing_primitives": missing, "outcome": "blocked_on_formal_concept_primitives" if missing else "frontier_ready_for_formalization", "trusted_memory_admission": False, "capability_promotion": False, "provider_calls": 0, "external_retrievals": 0, "created_at": utc_now()}
    result["execution_digest"] = _digest(result)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "FORMALIZATION_CAMPAIGN_WORKING_RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
