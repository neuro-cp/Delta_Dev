"""Workspace-only, cross-domain formal-primitives campaign.

The RC2 substrate remains an input.  This module never creates tables or writes
to it; every formal node is a reversible candidate artifact under a mission root.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.rc2_sqlite_substrate import DB_PATH


DOMAIN_CLUSTERS: dict[str, dict[str, Any]] = {
    "formal_mathematics": {"sources": ("mathematics", "logic"), "seeds": ("number", "function", "vector", "matrix", "eigen", "inner product", "basis", "proof")},
    "everyday_causal_science": {"sources": ("basic_physics", "chemistry", "materials_science", "nutrition", "vehicles_mechanics"), "seeds": ("heat", "phase", "force", "motion", "friction", "energy", "conduction", "flow")},
    "computing_software": {"sources": ("programming", "software_architecture"), "seeds": ("function", "type", "state", "exception", "module", "dependency", "process", "test", "api")},
    "cognition_language_learning": {"sources": ("delta_architecture_itself", "knowledge", "planning_productivity", "social_communication", "logic"), "seeds": ("concept", "evidence", "memory", "context", "learning", "capability", "evaluation", "confidence")},
    "psychology_behavior": {"sources": ("psychology",), "seeds": ("perception", "attention", "memory", "motivation", "bias", "stress", "emotion", "behavior")},
    "finance_economics": {"sources": ("finance", "business"), "seeds": ("asset", "liability", "income", "interest", "inflation", "risk", "return", "supply", "demand")},
    "biology_health": {"sources": ("biology", "medicine_health_general"), "seeds": ("cell", "metabolism", "homeostasis", "hormone", "response", "risk", "symptom", "evidence")},
    "art_interpretation": {"sources": ("philosophy", "history", "social_communication"), "seeds": ("form", "color", "composition", "style", "interpretation", "audience", "ambiguity", "perspective")},
    "engineering_systems": {"sources": ("engineering", "energy", "home_repair", "vehicles_mechanics"), "seeds": ("component", "subsystem", "load", "tolerance", "failure", "control", "sensor", "reliability")},
}

SHARED_PRIMITIVES = (
    "typed_entity", "property", "relation", "state_transition", "causal_link",
    "quantitative_value", "qualitative_value", "assumption", "claim",
    "evidence_reference", "confidence", "uncertainty", "conflict", "prerequisite",
    "dependent", "example", "counterexample", "validation_result", "constraint",
)

NOISE_MARKERS = (
    "operator-reviewable uncertainty", "connecting ", "governed memory", "governance",
    "operational use", "optimization", "coordination role", "curriculum role",
    "historical development", "longitudinal tracking", "evidence standard", "design pattern",
    "policy interface", "competency test", "resilience role", "system interaction",
)
NOISE_LABEL_WORDS = (
    "governance", "operational use", "optimization", "coordination role", "curriculum role",
    "historical development", "longitudinal tracking", "evidence standard", "design pattern",
    "policy interface", "competency test", "resilience role", "system interaction",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _connect_read_only(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _base_label(value: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()


def _is_associative_facet(row: dict[str, Any]) -> bool:
    label = _base_label(str(row["concept_name"])).lower()
    definition = str(row.get("short_definition") or "").lower()
    return not definition or any(marker in definition for marker in NOISE_MARKERS) or any(marker in label for marker in NOISE_LABEL_WORDS)


def _node_type(domain: str, label: str, definition: str) -> str:
    text = f"{label} {definition}".lower()
    if domain in {"formal_mathematics", "finance_economics"} and any(token in text for token in ("matrix", "vector", "number", "rate", "interest", "inflation", "balance")):
        return "quantitative_relation"
    if domain in {"everyday_causal_science", "biology_health"}:
        return "causal_mechanism"
    if domain == "computing_software":
        return "state_transition"
    if domain == "art_interpretation":
        return "interpretive_claim"
    if domain == "psychology_behavior":
        return "probabilistic_behavioral_construct"
    return "structured_claim"


def _tags(domain: str, node_type: str) -> tuple[str, ...]:
    tags = {"typed_entity", "property", "relation", "evidence_reference", "uncertainty", "example", "counterexample", "validation_result"}
    if node_type in {"causal_mechanism", "state_transition"}:
        tags |= {"state_transition", "causal_link", "assumption", "constraint"}
    if node_type == "quantitative_relation":
        tags |= {"quantitative_value", "assumption", "prerequisite"}
    if node_type == "interpretive_claim":
        tags |= {"claim", "qualitative_value", "confidence"}
    if node_type == "probabilistic_behavioral_construct":
        tags |= {"claim", "confidence", "conflict"}
    if domain in {"cognition_language_learning", "computing_software", "engineering_systems"}:
        tags |= {"state_transition", "constraint", "prerequisite"}
    return tuple(sorted(tags))


def _validate_node(node: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if not node["source_concept_ids"]:
        errors.append("missing_source_concept_id")
    if not node["plain_language_definition"]:
        errors.append("missing_retained_definition")
    if set(node["shared_primitive_ids"]) - set(SHARED_PRIMITIVES):
        errors.append("undeclared_shared_primitive")
    if any(marker in node["plain_language_definition"].lower() for marker in NOISE_MARKERS):
        errors.append("associative_facet_not_formalizable")
    if node["node_type"] == "interpretive_claim" and node["validation_status"] == "formally_grounded":
        errors.append("interpretation_cannot_claim_binary_grounding")
    return tuple(errors)


def _checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _select_domain_nodes(conn: sqlite3.Connection, domain: str, config: dict[str, Any], used_ids: set[str], maximum: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    placeholders = ",".join("?" for _ in config["sources"])
    rows = [dict(row) for row in conn.execute(
        f"SELECT concept_id, concept_name, normalized_name, domain, concept_type, short_definition, confidence, quality_score, source_type, rollback_handle FROM concepts WHERE domain IN ({placeholders}) ORDER BY quality_score DESC, concept_id",
        tuple(config["sources"]),
    )]
    rejected: list[dict[str, Any]] = []
    eligible: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        if row["concept_id"] in used_ids:
            continue
        if _is_associative_facet(row):
            rejected.append({"concept_id": row["concept_id"], "label": row["concept_name"], "reason": "generated_associative_facet_or_missing_definition"})
            continue
        label = _base_label(str(row["concept_name"])).lower()
        seed_score = sum(1 for seed in config["seeds"] if seed in label)
        eligible.append((seed_score, row))
    eligible.sort(key=lambda item: (-item[0], -float(item[1].get("quality_score") or 0), str(item[1]["concept_id"])))
    # A sparse domain is an honest missing-frontier result.  Do not fill it with
    # unrelated definitions merely to satisfy a campaign-size target.
    selected = [row for score, row in eligible if score > 0][:maximum]
    labels = {_base_label(str(row["concept_name"])).lower() for row in selected}
    missing = [seed for seed in config["seeds"] if not any(seed in label for label in labels)]
    return selected, rejected, missing


def compile_cross_domain_campaign(*, audit_id: str, audit_digest: str) -> dict[str, Any]:
    """Compile the one operator-approved envelope; routine actions are internal."""
    campaign_id = stable_id("cross-domain-formal-primitive-marathon-v2", audit_id, audit_digest)
    return {
        "campaign_id": campaign_id,
        "mission": "build a workspace-only, cross-domain formal primitive candidate layer from retained RC2 concept memory",
        "status": "campaign_authority_granted",
        "audit_id": audit_id,
        "audit_digest": audit_digest,
        "authority": {"request_id": stable_id("cross-domain-formal-primitive-authority", campaign_id), "status": "consumed", "authority_granted": True, "response": "approve_concept_memory_formalization_campaign", "routine_internal_actions_auto_consumed": True},
        "budgets": {"maximum_active_formal_nodes": 300, "maximum_nodes_per_domain": 50, "maximum_shared_primitives": 75, "maximum_downward_prerequisite_expansions": 150, "maximum_graph_depth": 12, "maximum_overlay_revisions_per_node": 4, "maximum_local_checks": 2500, "maximum_local_executions": 750, "maximum_working_artifacts": 5000},
        "external_boundaries": ("external_retrieval", "provider_or_api", "package_installation", "tracked_source_mutation", "trusted_memory_admission", "capability_promotion", "git", "deployment"),
    }


def run_cross_domain_formal_primitive_marathon(*, campaign: dict[str, Any], workspace: Path, db_path: Path = DB_PATH, maximum_nodes_per_domain: int = 50) -> dict[str, Any]:
    """Run deterministically from read-only RC2 input and checkpoint after each domain."""
    if campaign["authority"]["status"] != "consumed" or not campaign["authority"]["authority_granted"]:
        raise ValueError("cross_domain_formal_primitive_campaign_authority_not_granted")
    workspace.mkdir(parents=True, exist_ok=True)
    final_path = workspace / "CROSS_DOMAIN_FORMAL_PRIMITIVE_PACKAGE.json"
    input_digest = _digest({"campaign_id": campaign["campaign_id"], "source_digest": _file_digest(db_path), "maximum_nodes_per_domain": maximum_nodes_per_domain, "domains": DOMAIN_CLUSTERS})
    if final_path.exists():
        existing = json.loads(final_path.read_text(encoding="utf-8"))
        if existing.get("input_digest") == input_digest:
            return existing
        raise ValueError("cross_domain_formal_primitive_workspace_input_mismatch")

    before_digest = _file_digest(db_path)
    conn = _connect_read_only(db_path)
    source_count = int(conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0])
    used_ids: set[str] = set()
    nodes: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    missing_by_domain: dict[str, list[str]] = {}
    domain_reports: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    checkpoints: list[str] = []
    checkpoint_path = workspace / "campaign_checkpoint.json"
    for position, (domain, config) in enumerate(DOMAIN_CLUSTERS.items(), start=1):
        source_rows, domain_rejected, missing = _select_domain_nodes(conn, domain, config, used_ids, min(maximum_nodes_per_domain, int(campaign["budgets"]["maximum_nodes_per_domain"])))
        rejected.extend({"domain": domain, **item} for item in domain_rejected)
        domain_nodes: list[dict[str, Any]] = []
        for row in source_rows:
            used_ids.add(str(row["concept_id"]))
            label = _base_label(str(row["concept_name"]))
            definition = str(row.get("short_definition") or "").strip()
            kind = _node_type(domain, label, definition)
            node = {
                "primitive_id": stable_id("formal-node", campaign["campaign_id"], row["concept_id"]),
                "source_concept_ids": (row["concept_id"],), "canonical_label": label,
                "aliases": (str(row["normalized_name"]),), "domain": domain, "source_domain": row["domain"],
                "node_type": kind, "typed_entities": ({"entity_id": "subject", "label": label, "type": kind},), "symbols": (),
                "plain_language_definition": definition,
                "structured_definition": {"kind": "source_bounded_definition", "subject": label, "statement": definition, "derived_claims_allowed": False},
                "properties": (), "relations": (), "prerequisites": (), "dependents": (), "mechanisms": (), "assumptions": ("definition is retained context, not an independently proven theorem",),
                "examples": ({"kind": "schema_witness", "statement": f"{label} is represented only by its retained source definition.", "non_evidentiary": True},),
                "counterexamples": ({"kind": "rejection_rule", "statement": "A keyword-only or generated associative facet is not a formal primitive.", "non_evidentiary": True},),
                "evidence_references": ({"source_concept_id": row["concept_id"], "source_type": row["source_type"], "rollback_handle": row["rollback_handle"]},),
                "confidence": min(float(row.get("confidence") or 0), float(row.get("quality_score") or 0)), "uncertainty": ("source definition has not undergone independent truth validation",), "conflicts": (),
                "unresolved_obligations": ("independent evidence and behavioral use validation required before trusted admission",),
                "shared_primitive_ids": _tags(domain, kind), "validation_status": "partially_formalized", "mission_id": campaign["campaign_id"], "overlay_version": 1,
                "creation_history": ({"event": "source_bounded_workspace_overlay", "at": utc_now()},), "source_record_unchanged": True,
            }
            errors = _validate_node(node)
            node["validation_errors"] = errors
            if errors:
                node["validation_status"] = "conflicted"
            domain_nodes.append(node); nodes.append(node)
            for tag in node["shared_primitive_ids"]:
                edges.append({"edge_id": stable_id("formal-uses-shared", node["primitive_id"], tag), "source": node["primitive_id"], "target": tag, "relation": "uses_shared_primitive", "domain": domain})
            checks.append({"check_id": stable_id("formal-node-check", node["primitive_id"]), "node_id": node["primitive_id"], "passed": not errors, "errors": errors})
        missing_by_domain[domain] = missing
        domain_reports[domain] = {"source_domains": config["sources"], "nodes_created": len(domain_nodes), "source_concept_ids": tuple(node["source_concept_ids"][0] for node in domain_nodes), "missing_seed_labels": tuple(missing), "rejected_associative_facets": len(domain_rejected), "formal_readiness": "partial" if domain_nodes else "missing_retained_primitives"}
        checkpoint = {"campaign_id": campaign["campaign_id"], "input_digest": input_digest, "completed_domains": tuple(domain_reports), "node_count": len(nodes), "edge_count": len(edges), "checkpoint_index": position}
        _checkpoint(checkpoint_path, checkpoint); checkpoints.append(str(checkpoint_path))
    conn.close()

    shared = [{"primitive_id": tag, "node_type": "shared_schema_primitive", "validation_status": "schema_validated_not_trusted", "definition": f"Domain-neutral candidate schema primitive: {tag.replace('_', ' ')}.", "trusted_memory_admission": False} for tag in SHARED_PRIMITIVES]
    usage: dict[str, set[str]] = defaultdict(set)
    for node in nodes:
        for tag in node["shared_primitive_ids"]:
            usage[tag].add(node["domain"])
    transfers = [{"primitive_id": tag, "domains": tuple(sorted(domains)), "passed": len(domains) >= 2, "result": "cross_domain_schema_transfer" if len(domains) >= 2 else "insufficient_domain_coverage"} for tag, domains in sorted(usage.items())]
    after_digest = _file_digest(db_path)
    package = {
        "execution_id": stable_id("cross-domain-formal-primitive-execution", campaign["campaign_id"], input_digest), "campaign_id": campaign["campaign_id"], "created_at": utc_now(), "input_digest": input_digest,
        "workspace": str(workspace), "source_store": {"path": str(db_path), "concepts_inspected": source_count, "digest_before": before_digest, "digest_after": after_digest, "immutable": before_digest == after_digest},
        "domains_processed": tuple(DOMAIN_CLUSTERS), "shared_primitives": shared, "nodes": nodes, "edges": edges, "domain_reports": domain_reports, "rejected_associative_facets": rejected,
        "missing_primitives_by_domain": missing_by_domain, "checks": checks, "transfer_tests": transfers, "check_summary": {"total": len(checks), "passed": sum(1 for item in checks if item["passed"]), "failed": sum(1 for item in checks if not item["passed"])},
        "admission_package": {"admission_ready": (), "partially_formalized": tuple(node["primitive_id"] for node in nodes if node["validation_status"] == "partially_formalized"), "informal_context_only": tuple(item["concept_id"] for item in rejected), "conflicted": tuple(node["primitive_id"] for node in nodes if node["validation_status"] == "conflicted"), "missing": missing_by_domain, "automatic_admission": False},
        "external_escalation_items": ("independent source validation", "trusted memory admission", "capability promotion"), "provider_calls": 0, "external_retrievals": 0, "trusted_memory_admissions": 0, "capability_promotions": 0,
        "restart_proof": {"checkpoint_path": str(checkpoint_path), "final_package_path": str(final_path), "duplicate_safe_on_same_input_digest": True}, "status": "completed_workspace_candidate_package",
    }
    package["package_digest"] = _digest({**package, "created_at": ""})
    _checkpoint(final_path, package)
    return package


def write_cross_domain_summary(package: dict[str, Any], path: Path) -> Path:
    lines = ["# Cross-Domain Formal Primitive Marathon", "", f"- Execution: `{package['execution_id']}`", f"- Status: `{package['status']}`", f"- Concepts inspected: `{package['source_store']['concepts_inspected']}`", f"- Formal nodes: `{len(package['nodes'])}`", f"- Shared primitives: `{len(package['shared_primitives'])}`", f"- Source store immutable: `{package['source_store']['immutable']}`", "", "## Domain Results"]
    lines.extend(f"- `{name}`: {report['nodes_created']} nodes; readiness `{report['formal_readiness']}`" for name, report in package["domain_reports"].items())
    lines.extend(["", "## Admission Boundary", "All nodes remain workspace-only candidates. No trusted RC2 memory admission or capability promotion occurred."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
